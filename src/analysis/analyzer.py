import pandas as pd

def _analyze_desk_occupancy(df_assignments, all_desks):
    """
    Analiza la ocupación de escritorios por día, detallando cada asignación.
    """
    print("### 1. Análisis de Ocupación de Escritorios (Detallado) ###")
    
    total_desks = len(all_desks)
    if total_desks == 0:
        print("No hay escritorios definidos en la instancia.")
        return

    # Agrupar por día para el análisis
    assignments_by_day = df_assignments.groupby('Dia')

    print(f"Total de escritorios disponibles: {total_desks}\n")
    # Iterar sobre los días que tienen asignaciones
    for day, group_df in assignments_by_day:
        count = len(group_df)
        percentage = (count / total_desks) * 100
        print(f"--- Día {day}: {count}/{total_desks} escritorios asignados ({percentage:.1f}%) ---")
        
        # Ordenar por escritorio para una visualización más clara
        sorted_assignments = group_df.sort_values(by='Escritorio')
        
        # Imprimir cada asignación del día
        for index, row in sorted_assignments.iterrows():
            print(f"  - {row['Escritorio']}: {row['Empleado']}")

def _analyze_preference_mismatches(df_assignments, s_ek_param):
    """Cuenta cuántas asignaciones ocurrieron en días no preferidos."""
    print("\n### 2. Análisis de Preferencias de Días ###")
    
    mismatch_count = 0
    for index, row in df_assignments.iterrows():
        employee = row['Empleado']
        day = row['Dia']
        # Si el valor en P_ek para esta combinación es 0, es un "mismatch"
        if s_ek_param.get((employee, day), 0) == -1:
            mismatch_count += 1
            
    print(f"Se realizaron {mismatch_count} asignaciones en días NO preferidos por los empleados.")

def _analyze_group_dispersion(df_assignments, raw_data):
    """
    Analiza en cuántas zonas se distribuyen los grupos, detallando el conteo
    de empleados por zona.
    """
    print("\n### 3. Análisis de Dispersión de Grupos por Zona (Detallado) ###")

    desk_to_zone = {desk: zone for zone, desks in raw_data.get('Desks_Z', {}).items() for desk in desks}
    employee_to_group = {emp: group for group, emps in raw_data.get('Employees_G', {}).items() for emp in emps}
    group_sizes = {group: len(emps) for group, emps in raw_data.get('Employees_G', {}).items()}
            
    if not desk_to_zone or not employee_to_group:
        print("No se pudo analizar la dispersión por falta de datos 'Desks_Z' o 'Employees_G'.")
        return

    df_copy = df_assignments.copy()
    df_copy['Zona'] = df_copy['Escritorio'].map(desk_to_zone)
    df_copy['Grupo'] = df_copy['Empleado'].map(employee_to_group)

    print("Distribución de los grupos en las zonas cada día que tienen miembros presentes:")
    # Agrupar por Grupo y Día
    for (group, day), group_day_df in df_copy.groupby(['Grupo', 'Dia']):
        present_count = len(group_day_df)
        total_members = group_sizes.get(group, 0)
        
        # Contar cuántos empleados hay en cada zona para ese grupo y día
        zone_counts = group_day_df['Zona'].value_counts()
        
        # Formatear el texto de la distribución por zona
        distribution_str = ", ".join([f"{zone} ({count})" for zone, count in zone_counts.items()])
        
        print(f"- Grupo {group} - Día {day}: Presentes {present_count}/{total_members}. Distribución: {distribution_str}")

def _analyze_full_group_attendance(df_assignments, df_meetings, raw_data):
    """Verifica si los días de reunión asignados cumplen con la asistencia total."""
    print("\n### 4. Análisis de Asistencia en Días de Reunión ###")

    employee_to_group = {}
    group_sizes = {}
    for group, employees in raw_data.get('Employees_G', {}).items():
        group_sizes[group] = len(employees)
        for employee in employees:
            employee_to_group[employee] = group
            
    if not employee_to_group:
        print("No se pudo analizar la asistencia por falta de datos 'Employees_G'.")
        return

    for index, row in df_meetings.iterrows():
        meeting_group = row['Grupo']
        meeting_day = row['Dia_Reunion']
        
        # Filtrar las asignaciones para ese grupo en su día de reunión
        attendees = df_assignments[
            (df_assignments['Dia'] == meeting_day) & 
            (df_assignments['Empleado'].apply(lambda e: employee_to_group.get(e) == meeting_group))
        ]
        
        num_attendees = len(attendees)
        total_members = group_sizes.get(meeting_group, 0)
        
        if num_attendees == total_members:
            print(f"- Grupo {meeting_group}: CUMPLE. Asisten los {num_attendees}/{total_members} miembros el día de su reunión ({meeting_day}). ✔️")
        else:
            print(f"- Grupo {meeting_group}: NO CUMPLE. Solo asisten {num_attendees}/{total_members} miembros el día de su reunión ({meeting_day}). ❌")

def _analyze_desk_compatibility(df_assignments, raw_data):
    """
    Verifica que cada asignación respete la lista de escritorios
    compatibles del empleado (Desks_E).
    """
    print("\n### 5. Verificación de Compatibilidad de Escritorios (Desks_E) ###")
    
    desk_compatibilities = raw_data.get('Desks_E', {})
    violations = []

    # Iterar sobre cada asignación en la solución
    for index, row in df_assignments.iterrows():
        employee = row['Empleado']
        desk = row['Escritorio']
        
        # Obtener la lista de escritorios permitidos para ese empleado
        allowed_desks = desk_compatibilities.get(employee, [])
        
        # Si el escritorio asignado no está en la lista de permitidos, es una violación
        if desk not in allowed_desks:
            violations.append(f"  - Empleado {employee} fue asignado a {desk}, pero sus escritorios permitidos son: {allowed_desks}")

    if not violations:
        print("VERIFICACIÓN CUMPLIDA: Todas las asignaciones respetan la compatibilidad de escritorios. ✔️")
    else:
        print("¡ALERTA! Se encontraron asignaciones incompatibles con Desks_E: ❌")
        for v in violations:
            print(v)

def analyze_solution(results, model_data, raw_data):
    """
    Función principal que ejecuta una serie de análisis sobre la solución obtenida.
    
    Args:
        results (dict): El diccionario de resultados devuelto por el solver.
        model_data (dict): El diccionario con los datos procesados (sets y params).
        raw_data (dict): El diccionario con los datos crudos del JSON original.
    """
    if not results or 'asignaciones' not in results or results['asignaciones'].empty:
        print("No hay resultados de asignaciones para analizar.")
        return
        
    df_assignments = results['asignaciones']
    df_meetings = results['reuniones']
    
    _analyze_desk_occupancy(df_assignments, model_data['sets']['Desks'])
    _analyze_preference_mismatches(df_assignments, model_data['params']['S_ek'])
    _analyze_group_dispersion(df_assignments, raw_data)
    _analyze_full_group_attendance(df_assignments, df_meetings, raw_data)
    _analyze_desk_compatibility(df_assignments, raw_data)


# --- Ejemplo de cómo usar este script ---
# Este bloque se ejecutaría desde un archivo como main.py o uno nuevo para análisis.
if __name__ == '__main__':
    pass