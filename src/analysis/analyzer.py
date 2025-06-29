import pandas as pd
from tabulate import tabulate
import math

# Constante para asegurar el orden cronológico en todos los análisis.
DAY_ORDER = ['L', 'Ma', 'Mi', 'J', 'V']

def _print_section_header(title):
    """ Imprime un encabezado de sección estandarizado y llamativo. """
    width = 86
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)

def _get_daily_isolation_incidents(daily_solution_df, raw_data):
    """
    Analiza una asignación de UN SOLO DÍA y cuenta el número total de
    incidentes de aislamiento (empleados solos de su grupo en una zona).
    Esta es la lógica CORRECTA y PROBADA.
    """
    if daily_solution_df is None or daily_solution_df.empty:
        return 0

    # No es necesario enriquecer el DataFrame aquí si ya lo hemos hecho antes.
    # Pero para mantener la función autocontenida, se espera un df con 'Grupo' y 'Zona'.
    
    # Contar empleados por cada grupo en cada zona
    group_zone_counts = daily_solution_df.groupby(['Grupo', 'Zona']).size()
    
    # Filtrar para encontrar los casos donde el conteo es exactamente 1
    isolation_cases = group_zone_counts[group_zone_counts == 1]
    
    # El costo es el número de casos de aislamiento encontrados
    return len(isolation_cases)

def _format_multiline_list(items, columns=3):
    """ Formatea una lista de strings en un número fijo de columnas. """
    if not items:
        return ""
    
    rows = math.ceil(len(items) / columns)
    padded_items = items + [''] * (rows * columns - len(items))
    col_data = [padded_items[i::rows] for i in range(rows)]
    
    lines = []
    for row_items in col_data:
        lines.append("  ".join(item.ljust(35) for item in row_items).rstrip())
    return "\n".join(lines)


def analyze_solution(results, model_data, raw_data, final_status_message):
    """
    Función principal y rediseñada que ejecuta un análisis completo y presenta
    los resultados en un formato profesional y estructurado.
    """
    print(final_status_message)

    if not results or 'asignaciones' not in results or results['asignaciones'].empty:
        print("\nNo hay resultados de asignaciones para analizar.")
        return

    # --- 1. PREPARACIÓN DE DATOS ENRIQUECIDOS ---
    df_assignments = results['asignaciones'].copy()
    df_meetings = results.get('reuniones', pd.DataFrame())

    day_categorical_type = pd.CategoricalDtype(categories=DAY_ORDER, ordered=True)
    df_assignments['Dia'] = df_assignments['Dia'].astype(day_categorical_type)

    desk_to_zone = {desk: zone for zone, desks in raw_data.get('Desks_Z', {}).items() for desk in desks}
    employee_to_group = {emp: group for group, emps in raw_data.get('Employees_G', {}).items() for emp in emps}
    
    df_assignments['Zona'] = df_assignments['Escritorio'].map(desk_to_zone)
    df_assignments['Grupo'] = df_assignments['Empleado'].map(employee_to_group)
    
    # --- 2. CÁLCULO DE TODOS LOS KPIs (Usando la lógica correcta) ---

    # --- CÁLCULO DE COHESIÓN (CORREGIDO) ---
    daily_isolation_costs = {}
    for day in DAY_ORDER:
        df_day = df_assignments[df_assignments['Dia'] == day]
        daily_isolation_costs[day] = _get_daily_isolation_incidents(df_day, raw_data)
    
    total_isolation_cost = sum(daily_isolation_costs.values())

    # --- Resto de KPIs ---
    total_assignments = len(df_assignments)
    total_employees_in_instance = len(raw_data.get('Employees', []))
    employees_assigned = df_assignments['Empleado'].nunique()
    total_desks = len(raw_data.get('Desks', []))
    avg_occupancy = (total_assignments / (total_desks * len(DAY_ORDER))) * 100 if total_desks > 0 else 0
    mismatch_preferences = sum(1 for _, row in df_assignments.iterrows() if row['Dia'] not in raw_data.get('Days_E', {}).get(row['Empleado'], []))
    meeting_compliance_count = df_meetings['Grupo'].nunique()
    total_groups = len(raw_data.get('Groups',[]))
    compat_violations = sum(1 for _, row in df_assignments.iterrows() if row['Escritorio'] not in raw_data.get('Desks_E', {}).get(row['Empleado'], []))
    anchor_map = results.get('anclas', {})
    anchor_assignments_count = sum(1 for _, row in df_assignments.iterrows() if anchor_map.get(row['Empleado']) == row['Escritorio'])

    # --- 3. IMPRESIÓN DEL INFORME ESTRUCTURADO ---
    _print_section_header("R E S U M E N   E J E C U T I V O")
    # (El resto de la función de impresión sigue igual, ya que ahora los datos son correctos)
    exec_summary_data = [
        ["> Costo Total de Aislamiento (Objetivo Principal)", f"{total_isolation_cost}"],
        ["MÉTRICAS DE COBERTURA", ""],
        ["  - Asignaciones totales realizadas", f"{total_assignments}"],
        ["  - Empleados con asignación", f"{employees_assigned} / {total_employees_in_instance} ({employees_assigned/total_employees_in_instance:.1%})"],
        ["  - Ocupación promedio de escritorios", f"{avg_occupancy:.1f}%"],
        ["MÉTRICAS DE CALIDAD", ""],
        ["  - Asignaciones en días NO preferidos", f"{mismatch_preferences} ({mismatch_preferences/total_assignments:.1%})"],
        ["  - Cumplimiento asistencia a reuniones", f"{meeting_compliance_count} / {total_groups} ({meeting_compliance_count/total_groups:.1%})"],
    ]
    print(tabulate(exec_summary_data, headers=["INDICADOR CLAVE DE RENDIMIENTO (KPI)", "VALOR"], tablefmt="presto"))

    _print_section_header("D E C I S I O N E S   O P E R A C I O N A L E S")
    # ... (El resto de la impresión no cambia)
    print("\n--- [1. Ocupación Diaria de la Oficina] ---")
    occupancy_data = []
    for day in DAY_ORDER:
        count = len(df_assignments[df_assignments['Dia'] == day])
        percentage = (count / total_desks) * 100 if total_desks > 0 else 0
        occupancy_data.append([day, count, f"{percentage:.1f}"])
    print(tabulate(occupancy_data, headers=["Día", "Empleados Asignados", "Ocupación (%)"], tablefmt="pipe"))

    print("\n--- [2. Días de Reunión Designados por Grupo] ---")
    meeting_items = [f"{row['Grupo']}: {row['Dia_Reunion']}" for _, row in df_meetings.sort_values(by='Grupo').iterrows()]
    print(_format_multiline_list(meeting_items, columns=3))
    
    _print_section_header("A N Á L I S I S   D E   C A L I D A D")
    print("\n--- [A. Costo de Aislamiento por Día] ---")
    cohesion_table_data = [[day, cost] for day, cost in daily_isolation_costs.items()]
    cohesion_table_data.append(["TOTAL", total_isolation_cost])
    print(tabulate(cohesion_table_data, headers=["Día", "Total de Aislamientos (Incidentes)"], tablefmt="pipe"))

    print("\n--- [B. Verificación de Restricciones y Heurísticas] ---")
    print(f"- Cumplimiento de Compatibilidad Escritorio-Empleado: {'CUMPLIDO ✔️' if compat_violations == 0 else f'FALLIDO ({compat_violations} violaciones) ❌'}")
    print(f"- Uso de Escritorios \"Ancla\" de Referencia: {anchor_assignments_count} de {total_assignments} asignaciones ({anchor_assignments_count/total_assignments:.1%})")

    _print_section_header("A N E X O  1:  P L A N   D E   A S I G N A C I Ó N   F I N A L")
    assignment_items = []
    # (El resto de la lógica de Anexo 1 y Anexo 2 que ya teníamos no necesita cambiar)
    group_sizes = {group: len(emps) for group, emps in raw_data.get('Employees_G', {}).items()}
    df_assignments['Tamaño_Grupo'] = df_assignments['Grupo'].map(group_sizes)
    meeting_map = {row['Grupo']: row['Dia_Reunion'] for index, row in df_meetings.iterrows()}
    df_assignments['Es_Reunion'] = df_assignments.apply(
        lambda row: row['Dia'] == meeting_map.get(row['Grupo']), axis=1
    )
    _, dispersion_details_by_day = _calculate_cohesion_kpis_for_annex(df_assignments) # Usamos una función separada para el anexo
    
    for emp, assignments in df_assignments.groupby('Empleado'):
        details = ", ".join(f"{row['Dia']}:{row['Escritorio']}" for _, row in assignments.sort_values(by='Dia').iterrows())
        assignment_items.append(f"{emp}: {details}")
    print(_format_multiline_list(assignment_items, columns=2))

    _print_section_header("A N E X O  2:   D E S G L O S E   D E   C O H E S I Ó N   D I A R I A")
    for day in DAY_ORDER:
        if dispersion_details_by_day.get(day):
            print(f"\n--- [Día {day}] ---")
            dispersion_details_by_day[day].sort()
            for line in dispersion_details_by_day[day]:
                print(line)

# Reemplaza la función existente con esta versión corregida
def _calculate_cohesion_kpis_for_annex(df_assignments_enhanced):
    """ 
    Función auxiliar solo para generar el texto del anexo 2.
    CORREGIDA para manejar correctamente el caso de un solo asistente.
    """
    dispersion_details_by_day = {day: [] for day in DAY_ORDER}
    
    for (day, group), group_day_df in df_assignments_enhanced.groupby(['Dia', 'Grupo'], observed=True):
        
        zone_counts = group_day_df['Zona'].value_counts()
        distribution_str = ", ".join([f"{zone}({count})" for zone, count in zone_counts.items()])
        
        num_presentes = len(group_day_df)
        conclusion = "" # Inicializar la conclusión
        
        # 1. Caso especial: Solo una persona del grupo asiste.
        if num_presentes == 1:
            conclusion = "-> 1 persona presente (Aislado del equipo)."
        
        # 2. Caso: Asisten varios, pero todos en la misma zona. ¡Esto es cohesión perfecta!
        elif len(zone_counts) == 1:
            conclusion = "-> Cohesión perfecta."
            
        # 3. Caso: Asisten varios y están divididos, y al menos uno está solo en una zona.
        elif 1 in zone_counts.values:
            isolated_count = sum(1 for count in zone_counts.values if count == 1)
            conclusion = f"-> {len(zone_counts)} subgrupos ({isolated_count} aislado/s)."
            
        # 4. Caso: Asisten varios y están divididos, pero siempre en grupos de 2 o más.
        else:
            conclusion = f"-> {len(zone_counts)} subgrupos (sin aislados)."
            
        is_meeting_day = group_day_df['Es_Reunion'].any()
        marker = "* " if is_meeting_day else "  "
        line = f"{marker}{group} (Reunión)" if is_meeting_day else f"  {group}:"
        
        dispersion_details_by_day[day].append(
            f"{line:<18} Presentes {num_presentes}/{group_day_df['Tamaño_Grupo'].iloc[0]}. "
            f"Distribución: {distribution_str:<25} {conclusion}"
        )
        
    return None, dispersion_details_by_day