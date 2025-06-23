# main.py

import argparse
import pandas as pd

# Importar funciones de todos los módulos
from data.load_data import load_and_preprocess_data
from optimizer.model.model import solve_schedule_model
from optimizer.heuristics.anchor_assignment import assign_anchor_desks
from optimizer.model.daily_assigner import solve_daily_assignment_model
from analysis.analyzer import analyze_solution

def main():
    """
    Función principal que orquesta la ejecución de la estrategia por etapas.
    """
    parser = argparse.ArgumentParser(description="Script para resolver el reto ASOCIO por etapas.")
    parser.add_argument("--file", type=str, required=True, help='Instancia JSON a resolver.')
    args = parser.parse_args()

    # --- Carga de Datos (Paso 0) ---
    print(f"Iniciando proceso para la instancia: {args.file}")
    print("----------------------------------------------------")
    model_data, raw_data = load_and_preprocess_data(args.file)
    if not model_data: return

    # --- PASO 1: Planificación Maestra de Horarios ---
    print("\n--- PASO 1: Resolviendo Planificación de Horarios ---")
    schedule_results = solve_schedule_model(model_data)
    if not schedule_results: return
    print("   ...Horario semanal y días de reunión definidos.")

    # --- PASO 2: Asignación de Escritorios Ancla ---
    print("\n--- PASO 2: Asignando Escritorios Ancla ---")
    anchor_map = assign_anchor_desks(raw_data)
    print("   ...Escritorios ancla asignados.")

    # --- PASO 3: Asignación Diaria Optimizada ---
    print("\n--- PASO 3: Resolviendo Asignaciones Diarias Optimizadas ---")
    weights = {'aislamiento': 1000, 'consistencia': 1}
    final_assignments = []
    
    # Bucle para resolver la asignación de cada día
    for day, attending_employees in schedule_results['horario_semanal'].items():
        if not attending_employees: continue
        print(f"   - Resolviendo para el día: {day} ({len(attending_employees)} empleados)...")
        daily_assignments = solve_daily_assignment_model(
            day, attending_employees, anchor_map, raw_data, weights
        )
        final_assignments.extend(daily_assignments)
    
    print("   ...Asignaciones diarias finalizadas.")

    # --- PASO 4: Presentación y Análisis de la Solución Final ---
    print("\n----------------------------------------------------")
    print("PROCESO FINALIZADO. Evaluando solución completa:")
    
    # Empaquetar resultados en el formato esperado por el analizador
    df_final_assignments = pd.DataFrame(final_assignments)
    df_meetings = pd.DataFrame(
        list(schedule_results['dias_reunion'].items()), 
        columns=['Grupo', 'Dia_Reunion']
    )
    final_results_dict = {
        'asignaciones': df_final_assignments,
        'reuniones': df_meetings
    }

    # Llamar al analizador para una evaluación completa
    analyze_solution(final_results_dict, model_data, raw_data)

if __name__ == "__main__":
    main()