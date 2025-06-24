import argparse
import pandas as pd

# Importar funciones de todos los módulos. He ajustado las rutas para que coincidan con tu estructura.
# Asumo que la función de la Etapa 1 está en un archivo y la de la Etapa 3 en otro.
from data.load_data import load_and_preprocess_data
from optimizer.model.model import solve_schedule_model # Modelo de Horarios
from optimizer.heuristics.anchor_assignment import assign_anchor_desks # Heurística de Anclas
from optimizer.model.daily_assigner import solve_daily_assignment_model # Modelo de Asignación Diaria
from analysis.analyzer import analyze_solution

def main():
    """
    Función principal que orquesta la ejecución completa de la estrategia por etapas.
    """
    parser = argparse.ArgumentParser(description="Script para resolver el reto ASOCIO por etapas.")
    parser.add_argument("--file", type=str, required=True, help='Instancia JSON a resolver.')
    args = parser.parse_args()

    # --- Carga de Datos (Paso 0) ---
    print(f"Iniciando proceso para la instancia: {args.file}")
    print("----------------------------------------------------")
    model_data, raw_data = load_and_preprocess_data(args.file)
    if not model_data: return

    # --- ETAPA 1: Planificación Maestra de Horarios ---
    print("\n--- ETAPA 1: Resolviendo Planificación de Horarios ---")
    schedule_results = solve_schedule_model(model_data)
    if not schedule_results: 
        print("La Etapa 1 no pudo generar un horario. Finalizando.")
        return
    print("   ...Horario semanal y días de reunión definidos.")

    # --- ETAPA 2: Asignación de Escritorios Ancla ---
    print("\n--- ETAPA 2: Asignando Escritorios Ancla ---")
    anchor_map = assign_anchor_desks(raw_data)
    print("   ...Escritorios ancla asignados.")

    # --- ETAPA 3: Asignación Diaria Optimizada ---
    print("\n--- ETAPA 3: Resolviendo Asignaciones Diarias Optimizadas ---")
    
    # Lista para guardar los DataFrames de resultados de cada día
    daily_results_dfs = []
    
    # Bucle para resolver la asignación de cada día
    for day, attending_employees in schedule_results['horario_semanal'].items():
        if not attending_employees:
            print(f"   - No hay asistentes para el día: {day}")
            continue
            
        print(f"   - Resolviendo para el día: {day} ({len(attending_employees)} empleados)...")

        # --- INICIO DE LA MODIFICACIÓN ---

        # 1. Preparamos un diccionario con los datos específicos para este día
        daily_data = {
            'day': day,
            'sets': {
                'Attending_Employees': attending_employees,
                'Desks': model_data['sets']['Desks'],
                'Groups': model_data['sets']['Groups'],
                'Zones': model_data['sets']['Zones'],
                # Filtramos las asignaciones válidas solo para los empleados de hoy
                'Valid_Daily_Assignments': [
                    (e, d) for (e, d) in model_data['sets']['Valid_Assignments'] if e in attending_employees
                ]
            },
            'params': {
                'M_eg': { (e,g):v for (e,g),v in model_data['params']['M_eg'].items() if e in attending_employees },
                'L_dz': model_data['params']['L_dz'],
                'Anchor_Assignments': {e:d for e,d in anchor_map.items() if e in attending_employees},
                'w_aislamiento': 100,
                'w_consistencia': 1
            }
        }
        
        # 2. Llamamos al solver diario con los datos preparados
        daily_assignments_df = solve_daily_assignment_model(daily_data)
        
        # 3. Guardamos el DataFrame del día si se encontró una solución
        if daily_assignments_df is not None:
            daily_results_dfs.append(daily_assignments_df)
        else:
            print(f"   *** Alerta: No se encontró solución para el día {day}. Este día quedará sin asignaciones. ***")

    # 4. Unimos los resultados de todos los días en un único DataFrame
    if not daily_results_dfs:
        print("No se pudieron generar asignaciones para ningún día.")
        return
        
    df_final_assignments = pd.concat(daily_results_dfs, ignore_index=True)

    # --- FIN DE LA MODIFICACIÓN ---
    
    print("   ...Asignaciones diarias finalizadas.")

    # --- ETAPA 4: Presentación y Análisis de la Solución Final ---
    print("\n----------------------------------------------------")
    print("PROCESO FINALIZADO. Evaluando solución completa:")
    
    df_meetings = pd.DataFrame(
        list(schedule_results['dias_reunion'].items()), 
        columns=['Grupo', 'Dia_Reunion']
    )
    final_results_dict = {
        'asignaciones': df_final_assignments,
        'reuniones': df_meetings
    }

    analyze_solution(final_results_dict, model_data, raw_data)

if __name__ == "__main__":
    main()