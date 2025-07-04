import argparse
import pandas as pd
from multiprocessing import Pool, cpu_count
import logging

logging.getLogger('pyomo.core').setLevel(logging.ERROR)

# Importar todas las funciones de nuestros módulos
from data.load_data import load_and_preprocess_data
from optimizer.heuristics.risk_analysis import calculate_risk_and_top_desks
from optimizer.heuristics.anchor_assignment import assign_anchor_desks
from optimizer.model.model import solve_schedule_model
from optimizer.model.daily_assigner import solve_daily_assignment_model
from optimizer.heuristics.feedback_loop import evaluate_and_generate_cut # El cerebro de la Etapa 4
from analysis.analyzer import analyze_solution

# Función auxiliar para el header
def _print_section_header(title):
    width = 86
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)

def daily_solver_worker(daily_data):
    """
    Esta es la función "trabajadora". Se encarga de resolver la asignación
    para un único día. Está diseñada para ser ejecutada de forma asíncrona.
    """
    day = daily_data['day']
    num_employees = len(daily_data['sets']['Attending_Employees'])
   
    # Llama al solver de la Etapa 3
    daily_assignments_df, final_gap = solve_daily_assignment_model(daily_data)
    
    # Devuelve el día y su resultado para poder rearmar el diccionario después
    return day, daily_assignments_df, final_gap

def main():
    """
    Función principal que orquesta la ejecución completa de la estrategia iterativa.
    """
    parser = argparse.ArgumentParser(description="Script para resolver el reto ASOCIO por etapas.")
    parser.add_argument("--file", type=str, required=True, help='Instancia JSON a resolver.')
    args = parser.parse_args()

    # --- Carga y Análisis Inicial (Pasos 0 y 1) ---
    model_data, raw_data = load_and_preprocess_data(args.file)
    if not model_data: return
    
    #ETAPA 0: Calculando Índice de Riesgo
    print("ETAPA 0: Calculando Índice de Riesgo")
    risk_data = calculate_risk_and_top_desks(raw_data)
    model_data['params']['Risk_Index'] = {e: data['risk_index'] for e, data in risk_data.items()}
    model_data['params']['w_riesgo'] = 2.0
    
    # Parámetros para la Etapa 3 (y la prueba de la Etapa 4)
    model_data['params']['w_aislamiento'] = 100
    model_data['params']['w_consistencia'] = 1
    
    #ETAPA 1: Asignando Escritorios Ancla
    print("ETAPA 1: Asignando escritorios ancla...")
    anchor_map = assign_anchor_desks(raw_data, risk_data)

    # --- INICIO DEL BUCLE ITERATIVO DE MEJORA ---
    
    _print_section_header("M E T O D O L O G Í A")
    print("ETAPA 0: Calculando heurísticas de Riesgo y Anclas...")
    print("ETAPA 1-4: Iniciando bucle de optimización iterativa...")
    
    max_iterations = 10
    list_of_cuts = []
    final_solution_dict = None
    
    # Variables para guardar la mejor solución
    best_solution_so_far = None
    best_isolation_cost = float('inf') # Inicializamos el mejor costo en infinito

    for i in range(1, max_iterations + 1):
        print(f"\n------Iniciando Iteración #{i}------")
        # 1. ETAPA 1: Planificar Horario con los filtros actuales
        print(f"\nResolviendo el modelo de horarios (Iteración #{i})...")
        schedule_results = solve_schedule_model(model_data, list_of_cuts)
        if not schedule_results:
            break
        
        # 2. ETAPA 3: Resolver asignaciones diarias
        # 2.1. Preparamos la lista de "tareas". Cada tarea es un diccionario
        #    con todos los datos necesarios para resolver un día.
        print("Resolviendo modelo de asignaciones diarias...")
        tasks = []
        for day, attending_employees in schedule_results['horario_semanal'].items():
            if not attending_employees: continue
            
            daily_data = {
                'day': day,
                'sets': {
                    'Attending_Employees': attending_employees,
                    'Desks': model_data['sets']['Desks'],
                    'Groups': model_data['sets']['Groups'],
                    'Zones': model_data['sets']['Zones'],
                    'Valid_Daily_Assignments': [(e,d) for (e,d) in model_data['sets']['Valid_Assignments'] if e in attending_employees]
                },
                'params': {
                    'M_eg': { (e,g):v for (e,g),v in model_data['params']['M_eg'].items() if e in attending_employees },
                    'L_dz': model_data['params']['L_dz'],
                    'Anchor_Assignments': {e:d for e,d in anchor_map.items() if e in attending_employees},
                    'w_aislamiento': 100,
                    'w_consistencia': 1
                }
            }
            tasks.append(daily_data)

        # 2.2. Creamos un pool de procesos y distribuimos las tareas
        # Se usarán hasta 5 procesos, o menos si tu CPU tiene menos núcleos.
        with Pool(processes=min(cpu_count(), 5)) as pool:
            # pool.map ejecuta la función 'daily_solver_worker' para cada elemento en 'tasks'
            # y devuelve una lista con los resultados en el mismo orden.
            results_list = pool.map(daily_solver_worker, tasks)
        
        # 2.3. Reconstruimos el diccionario de soluciones diarias a partir de la lista de resultados
        daily_solutions = {day: {'solution': result_df, 'gap': gap} for day, result_df, gap in results_list}
            
        # 3. ETAPA 4: Evaluar la calidad de la solución semanal completa
        # 3.1. Sumar el número de asignaciones de cada día para obtener el total semanal.
        #    Se comprueba que la solución de cada día no sea None para evitar errores.
        total_weekly_assignments = sum(
            len(result_data['solution'])
            for result_data in daily_solutions.values()
            if result_data and result_data['solution'] is not None
        )

        # 3.2. Calcular el 20% del total y redondear hacia abajo (usando int()).
        dynamic_threshold = int(total_weekly_assignments * 0.2)

        is_solution_acceptable, new_cuts, current_isolation_cost = evaluate_and_generate_cut(
            daily_solutions, 
            schedule_results['horario_semanal'], 
            model_data, 
            raw_data, 
            anchor_map, 
            quality_threshold=dynamic_threshold  # Se pasa la nueva variable
        )
        
        # Imprime el resumen conciso de la iteración.
        print(f"   -> Iteración #{i}: Costo Aislamiento={current_isolation_cost}. Umbral Calidad={dynamic_threshold}.")
       
        # Comparamos si la solución de ESTA iteración es la mejor que hemos visto.
        if current_isolation_cost < best_isolation_cost:
            print(f"   -> ✨ ¡Nueva mejor solución encontrada! Costo: {current_isolation_cost} (anterior mejor: {best_isolation_cost})")
            best_isolation_cost = current_isolation_cost
            
            # Guardamos esta solución como la mejor hasta ahora
            valid_dfs = [
                result_data['solution'] 
                for result_data in daily_solutions.values() 
                if result_data and result_data['solution'] is not None
            ]
            full_assignment_df = pd.concat(valid_dfs, ignore_index=True) if valid_dfs else pd.DataFrame()
            best_solution_so_far = {
                'asignaciones': full_assignment_df,
                'reuniones': pd.DataFrame(list(schedule_results['dias_reunion'].items()), columns=['Grupo', 'Dia_Reunion'])
            }
        
        if is_solution_acceptable:
            # Extraemos el DataFrame de la clave 'solution' de cada resultado diario.
            # También comprobamos que el resultado del día no sea None.
            valid_dfs = [
                result_data['solution'] 
                for result_data in daily_solutions.values() 
                if result_data and result_data['solution'] is not None
            ]

            full_assignment_df = pd.concat(valid_dfs, ignore_index=True) if valid_dfs else pd.DataFrame()
            
            final_solution_dict = {
                'asignaciones': full_assignment_df,
                'reuniones': pd.DataFrame(list(schedule_results['dias_reunion'].items()), columns=['Grupo', 'Dia_Reunion'])
            }
            break # Rompemos el bucle
        else:
            list_of_cuts.extend(new_cuts) # Añadimos el nuevo filtro para la siguiente iteración

    # --- PRESENTACIÓN FINAL ---
    _print_section_header("R E S U M E N   D E L   P R O C E S O") # Un nuevo header
    
    # Si el bucle terminó porque encontró una solución aceptable.
    if final_solution_dict:
        final_status = f">>> ESTADO FINAL: Solución de Alta Calidad Encontrada (en {i} iteración/es) <<<"
        analyze_solution(final_solution_dict, model_data, raw_data, final_status)
    # Si el bucle terminó por las 10 iteraciones, usamos la MEJOR que guardamos.
    elif best_solution_so_far:
        final_status = f">>> ESTADO FINAL: Límite de {max_iterations} iteraciones alcanzado. Mostrando la mejor solución encontrada (Costo: {best_isolation_cost}) <<<"
        # Añadir los anclas a los resultados para que el analyzer los pueda usar
        best_solution_so_far['anclas'] = anchor_map 
        analyze_solution(best_solution_so_far, model_data, raw_data, final_status)
    # Si nunca se encontró una solución factible.
    else:
        print(">>> ESTADO FINAL: No se pudo encontrar una solución factible en ninguna de las iteraciones. <<<")

if __name__ == "__main__":
    main()