import argparse
import pandas as pd

# Importamos la función de carga de datos y el NUEVO solver del Paso 1
from data.load_data import load_and_preprocess_data
from optimizer.model.model import solve_schedule_model
from optimizer.heuristics.anchor_assignment import assign_anchor_desks
# La importación de analyze_solution ya no es necesaria en este paso

def main():
    """
    Función principal que orquesta la ejecución del Paso 1: Planificación Maestra de Horarios.
    """
    parser = argparse.ArgumentParser(
        description="Script para ejecutar el Paso 1 del reto de asignación de puestos ASOCIO."
    )
    parser.add_argument(
        "--file",
        type=str,
        required=True,
        help='Nombre del archivo de la instancia JSON. Ejemplo: "instance10.json"'
    )
    args = parser.parse_args()

    # --- ETAPA 1, PASO 1: Cargar datos de la instancia ---
    print(f"Iniciando proceso para la instancia: {args.file}")
    print("----------------------------------------------------")
    print("1. Cargando y preprocesando datos...")
    
    model_data, raw_data = load_and_preprocess_data(args.file)

    if not model_data:
        print("Finalizando ejecución debido a un error en la carga de datos.")
        return

    print("   Datos cargados exitosamente.")

    # --- ETAPA 1, PASO 2: Construir y resolver el modelo de horarios ---
    print("\n2. Construyendo y resolviendo el modelo de Planificación de Horarios (Paso 1)...")
    
    schedule_results = solve_schedule_model(model_data)

    # --- ETAPA 1, PASO 3: Presentar los resultados del horario ---
    print("\n----------------------------------------------------")
    if schedule_results:
        print("3. ¡Planificación Maestra de Horarios Generada Exitosamente!")
        
        # Mostrar valor objetivo
        obj_value = schedule_results['valor_objetivo']
        print(f"\nValor Objetivo (Suma Puntuaciones Preferencia): {obj_value:.2f}")

        # Mostrar días de reunión
        print("\n--- Días de Reunión por Grupo ---")
        df_meetings = pd.DataFrame(
            list(schedule_results['dias_reunion'].items()), 
            columns=['Grupo', 'Dia_Reunion']
        ).sort_values(by='Grupo')
        print(df_meetings.to_string(index=False))
        
        # Mostrar quién asiste cada día
        print("\n--- Asistencia Confirmada por Día ---")
        for day, employees in schedule_results['horario_semanal'].items():
            print(f"- {day}: {len(employees)} empleados -> {', '.join(sorted(employees))}")
            
    else:
        print("3. El modelo no pudo generar un horario.")
    
    print("\n----------------------------------------------------")
    print("Paso 1 (Planificación Maestra de Horarios) finalizado.")
    
    print("\n3. Ejecutando Etapa 2: Asignación de Escritorios Ancla...")
    
    # Llamamos a la función que creamos, pasándole los datos crudos
    anchor_assignments = assign_anchor_desks(raw_data)
    
    if not anchor_assignments:
        print("La heurística no pudo asignar los escritorios ancla. Finalizando.")
        return
        
    print("   ¡Asignación de Escritorios Ancla Generada Exitosamente!")
    
    print("\n--- Muestra de Escritorios Ancla Asignados (Resultado Etapa 2) ---")
    # Imprimimos solo los primeros 5 para no llenar la consola
    for i, (employee, desk) in enumerate(anchor_assignments.items()):
        if i >= 5:
            break
        print(f"- {employee}: {desk}")
    print(f"  ... y {len(anchor_assignments) - 5} más.")


if __name__ == "__main__":
    main()