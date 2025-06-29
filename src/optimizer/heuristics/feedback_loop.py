import pandas as pd
from multiprocessing import Pool, cpu_count
import itertools
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model.daily_assigner import solve_daily_assignment_model

# --- Worker Function (La tarea que se ejecutará en paralelo) ---

def run_single_feasibility_test(args):
    """
    Esta función es el "trabajador". Ejecuta una única prueba de la Etapa 3
    con un subconjunto de empleados y devuelve si tuvo éxito o no.
    Debe estar fuera de cualquier clase para que multiprocessing pueda usarla.
    """
    # Desempaquetamos los argumentos
    employee_to_remove, day, problematic_employees, anchor_map, model_data, raw_data, original_daily_cost = args
    
    # Creamos el conjunto de prueba quitando al empleado de interés
    test_set = [e for e in problematic_employees if e != employee_to_remove]
    
    # Preparamos un diccionario con los datos específicos y FILTRADOS para esta prueba
    daily_data_test = {
        'day': day,
        'sets': {
            'Attending_Employees': test_set,
            'Desks': model_data['sets']['Desks'],
            'Groups': model_data['sets']['Groups'],
            'Zones': model_data['sets']['Zones'],
            'Valid_Daily_Assignments': [(e, d) for (e, d) in model_data['sets']['Valid_Assignments'] if e in test_set]
        },
        'params': {
            # Filtramos M_eg para que SOLO contenga los empleados del test_set
            'M_eg': { (e,g):v for (e,g),v in model_data['params']['M_eg'].items() if e in test_set },
            'L_dz': model_data['params']['L_dz'],
            'Anchor_Assignments': {e:d for e,d in anchor_map.items() if e in test_set},
            'w_aislamiento': model_data['params']['w_aislamiento'],
            'w_consistencia': model_data['params']['w_consistencia']
        }
    }
    
    solution_df = solve_daily_assignment_model(daily_data_test)
    
    if solution_df[0] is None:
        # Si no hay solución, la prueba falla.
        is_successful = False
    else:
        # Si hay solución, calculamos su costo y comparamos.
        new_isolation_cost = _calculate_daily_isolation_cost(solution_df[0], raw_data)
        
        # La prueba es exitosa SOLO SI el costo no aumentó.
        is_successful = new_isolation_cost < original_daily_cost
    
    # Devolvemos el empleado que quitamos y si la prueba tuvo éxito
    return employee_to_remove, is_successful

def _calculate_daily_isolation_cost(solution_df, raw_data):
    """
    Analiza una asignación diaria y cuenta el número de empleados aislados.
    """
    if solution_df is None or solution_df.empty:
        # Si no hay solución o no hay nadie asignado, el costo es 0.
        return 0

    # 1. Crear mapeos para un análisis rápido
    desk_to_zone = {d: z for z, desks in raw_data.get('Desks_Z', {}).items() for d in desks}
    employee_to_group = {e: g for g, emps in raw_data.get('Employees_G', {}).items() for e in emps}

    # 2. Enriquecer el DataFrame con la información de Zona y Grupo
    df_copy = solution_df.copy()
    df_copy['Zona'] = df_copy['Escritorio'].map(desk_to_zone)
    df_copy['Grupo'] = df_copy['Empleado'].map(employee_to_group)
    
    # 3. Contar empleados por cada grupo en cada zona
    group_zone_counts = df_copy.groupby(['Grupo', 'Zona']).size()
    
    # 4. Filtrar para encontrar los casos donde el conteo es exactamente 1
    isolation_cases = group_zone_counts[group_zone_counts == 1]
    
    # El costo es el número de casos de aislamiento encontrados
    return len(isolation_cases)

def _find_core_conflict_parallel(day, problematic_employees, anchor_map, model_data, raw_data, original_daily_cost):
    """
    NUEVA FUNCIÓN de diagnóstico que usa paralelismo para encontrar el núcleo del conflicto.
    """
    tasks = [
        (emp, day, problematic_employees, anchor_map, model_data, raw_data, original_daily_cost)
        for emp in problematic_employees
    ]
    
    if not tasks:
        return []

    # Usamos un pool de procesos para ejecutar todas las pruebas a la vez
    with Pool(processes=min(cpu_count(), len(tasks))) as pool:
        results = pool.map(run_single_feasibility_test, tasks)

    # Un empleado es "inocente" para el conflicto si al quitarlo, la prueba tuvo éxito.
    innocent_employees = [emp for emp, success in results if success]
    
    # Si la lista de 'esenciales' no está vacía, ESE es nuestro núcleo del conflicto.
    if innocent_employees:
        core_conflict =  [emp for emp in problematic_employees if emp not in innocent_employees]
        if len(core_conflict) == 0:
            # Si la lista está vacía, significa que quitar a ningún empleado por sí solo
            # fue suficiente para arreglar el problema. El conflicto es más complejo.
            # En este caso, nuestra mejor opción es usar el grupo problemático completo.
            core_conflict = problematic_employees

    # La función ahora devuelve el núcleo del conflicto correctamente identificado
    return core_conflict

# --- Main Logic Function ---

def evaluate_and_generate_cut(daily_solutions, schedule_candidate, model_data, raw_data, anchor_map, quality_threshold=10, quality_threshold_day=4):
    """
    Función principal de la Etapa 4. Evalúa la calidad y genera un corte inteligente
    usando procesamiento en paralelo para el diagnóstico.
    """
    total_isolation_cost = 0
    daily_costs = {}

    # 1. Calificar cada día, entendiendo la nueva estructura de 'daily_solutions'
    for day, result_data in daily_solutions.items():
        
        # Extraemos el DataFrame de la solución del diccionario anidado
        solution_df = result_data['solution']
        
        if solution_df is None:
            # Caso 1: El día fue infactible
            daily_costs[day] = {'cost': float('inf'), 'attendees': schedule_candidate.get(day, [])}
            total_isolation_cost = float('inf')
        else:
            # Caso 2: El día tuvo solución, calculamos su costo de aislamiento
            isolation_count = _calculate_daily_isolation_cost(solution_df, raw_data)
            daily_costs[day] = {'cost': isolation_count, 'attendees': schedule_candidate.get(day, [])}
            total_isolation_cost += isolation_count
            
    # 2.A. Preparamos y mostramos el reporte detallado de costos por día
    # Usamos sorted() para asegurar que los días se impriman en orden
    daily_cost_report = ", ".join(
        f"{day}({data['cost'] if data['cost'] != float('inf') else 'INF'})" 
        for day, data in sorted(daily_costs.items())
    )
    
    # 2. Tomar la decisión
    if total_isolation_cost <= quality_threshold:
        return True, [], total_isolation_cost
    else:
        print("\n[!] No se encontró una solución aceptable que cumpla con el umbral minimo de calidad. Generando corte inteligente...")
        new_cuts = []
        for day, data in daily_costs.items():
            if data['cost'] > quality_threshold_day:
                problematic_employees = data['attendees']
                
                # Pasamos el costo de ESTE DÍA a la función de diagnóstico.
                original_daily_cost = data['cost']
                
                # Ahora llamamos a nuestra nueva función de diagnóstico.
                core_conflict = _find_core_conflict_parallel(day, problematic_employees, anchor_map, model_data, raw_data, original_daily_cost)
                
                new_cut = {'day': day, 'employees': core_conflict}
                new_cuts.append(new_cut)

        return False, new_cuts, total_isolation_cost