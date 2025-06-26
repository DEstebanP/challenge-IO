import pandas as pd

# Definimos el orden cronológico de los días para usarlo en todo el script.
DAY_ORDER = ['L', 'Ma', 'Mi', 'J', 'V']

def _analyze_desk_occupancy(df_assignments, all_desks):
    """Analiza la ocupación de escritorios por día, detallando cada asignación."""
    print("### 1. Análisis de Ocupación de Escritorios (Detallado) ###")
    
    total_desks = len(all_desks)
    if total_desks == 0:
        print("No hay escritorios definidos en la instancia.")
        return

    assignments_by_day = df_assignments.groupby('Dia', observed=True) 
    print(f"Total de escritorios disponibles: {total_desks}\n")
    
    # Usamos la lista predefinida para asegurar un orden cronológico en la salida.
    for day in DAY_ORDER:
        if day not in assignments_by_day.groups:
            continue # Si no hubo asignaciones ese día, lo saltamos.
            
        group_df = assignments_by_day.get_group(day)
        count = len(group_df)
        percentage = (count / total_desks) * 100
        print(f"--- Día {day}: {count}/{total_desks} escritorios asignados ({percentage:.1f}%) ---")
        
        # El sort_values() ahora funcionará correctamente por la categorización del día.
        for index, row in group_df.sort_values(by='Escritorio').iterrows():
            print(f"  - {row['Escritorio']}: {row['Empleado']}")

def _analyze_preference_mismatches(df_assignments, raw_data):
    """
    MODIFICADO: Cuenta las asignaciones en días no preferidos usando los datos originales
    para ser más robusto y no depender de los pesos del modelo.
    """
    print("\n### 2. Análisis de Preferencias de Días ###")
    
    employee_day_preferences = raw_data.get('Days_E', {})
    mismatch_count = 0
    
    for index, row in df_assignments.iterrows():
        employee = row['Empleado']
        day = row['Dia']
        # Comprobamos directamente contra la lista de preferencias originales.
        if day not in employee_day_preferences.get(employee, []):
            mismatch_count += 1
            
    print(f"Se realizaron {mismatch_count} asignaciones en días NO preferidos por los empleados.")

def _analyze_group_dispersion(df_assignments_enhanced):
    """
    MODIFICADO: Analiza la dispersión de grupos. Ahora recibe el DataFrame ya enriquecido.
    """
    print("\n### 3. Análisis de Dispersión de Grupos por Zona (Detallado) ###")

    # La salida ahora estará ordenada cronológicamente por día gracias a la categorización.
    print("Distribución de los grupos en las zonas cada día que tienen miembros presentes:")
    for (group, day), group_day_df in df_assignments_enhanced.groupby(['Grupo', 'Dia'], observed=True):
        present_count = len(group_day_df)
        # Obtenemos el tamaño total del grupo del DataFrame enriquecido.
        total_members = group_day_df['Tamaño_Grupo'].iloc[0]
        
        zone_counts = group_day_df['Zona'].value_counts()
        distribution_str = ", ".join([f"{zone} ({count})" for zone, count in zone_counts.items()])
        
        print(f"- Grupo {group} - Día {day}: Presentes {present_count}/{total_members}. Distribución: {distribution_str}")

def _analyze_full_group_attendance(df_assignments_enhanced, df_meetings):
    """
    MODIFICADO: Verifica la asistencia en reuniones usando el DataFrame enriquecido
    para mayor eficiencia.
    """
    print("\n### 4. Análisis de Asistencia en Días de Reunión ###")

    for index, row in df_meetings.iterrows():
        meeting_group = row['Grupo']
        meeting_day = row['Dia_Reunion']
        
        # Filtramos el DataFrame ya enriquecido, lo cual es más rápido.
        attendees = df_assignments_enhanced[
            (df_assignments_enhanced['Dia'] == meeting_day) & 
            (df_assignments_enhanced['Grupo'] == meeting_group)
        ]
        
        num_attendees = len(attendees)
        # Obtenemos el tamaño del grupo del DataFrame.
        total_members = attendees['Tamaño_Grupo'].iloc[0] if not attendees.empty else 0
        
        if num_attendees == total_members:
            print(f"- Grupo {meeting_group}: CUMPLE. Asisten los {num_attendees}/{total_members} miembros el día de su reunión ({meeting_day}). ✔️")
        else:
            print(f"- Grupo {meeting_group}: NO CUMPLE. Solo asisten {num_attendees}/{total_members} miembros el día de su reunión ({meeting_day}). ❌")

def _analyze_desk_compatibility(df_assignments, raw_data):
    """Verifica que cada asignación respete la lista de escritorios compatibles."""
    print("\n### 5. Verificación de Compatibilidad de Escritorios (Desks_E) ###")
    
    desk_compatibilities = raw_data.get('Desks_E', {})
    violations = []

    for index, row in df_assignments.iterrows():
        employee = row['Empleado']
        desk = row['Escritorio']
        allowed_desks = desk_compatibilities.get(employee, [])
        if desk not in allowed_desks:
            violations.append(f"  - Empleado {employee} asignado a {desk}, pero sus escritorios permitidos son: {allowed_desks}")

    if not violations:
        print("VERIFICACIÓN CUMPLIDA: Todas las asignaciones respetan la compatibilidad. ✔️")
    else:
        print("¡ALERTA! Se encontraron asignaciones incompatibles con Desks_E: ❌")
        for v in violations:
            print(v)

def _analyze_employee_assignments(df_assignments_enhanced):
    """
    Crea un resumen para cada empleado mostrando los días y escritorios asignados.
    Ahora ordena cronológicamente.
    """
    print("\n### 6. Resumen de Asignaciones por Empleado ###")

    # El groupby y sort_values ahora respetan el orden cronológico de los días.
    for employee, assignments in df_assignments_enhanced.groupby('Empleado'):
        assignment_details = [f"{row['Dia']}: {row['Escritorio']}" for index, row in assignments.sort_values(by='Dia').iterrows()]
        details_str = ", ".join(assignment_details)
        num_days = len(assignments)
        print(f"- {employee}: Asignado {num_days} día(s) -> {details_str}")


def analyze_solution(results, model_data, raw_data):
    """
    Función principal que ejecuta una serie de análisis sobre la solución obtenida.
    """
    if not results or 'asignaciones' not in results or results['asignaciones'].empty:
        print("No hay resultados de asignaciones para analizar.")
        return
        
    df_assignments = results['asignaciones'].copy() # Usamos una copia para evitar warnings
    df_meetings = results.get('reuniones', pd.DataFrame())
    
    # --- INICIO DE LAS MEJORAS: PRE-PROCESAMIENTO CENTRALIZADO ---

    # 1. Convertir la columna 'Dia' a un tipo categórico ordenado.
    #    Esto asegura que cualquier ordenamiento por día sea cronológico (L, Ma, Mi...).
    day_categorical_type = pd.CategoricalDtype(categories=DAY_ORDER, ordered=True)
    df_assignments['Dia'] = df_assignments['Dia'].astype(day_categorical_type)

    # 2. Enriquecer el DataFrame de asignaciones una sola vez con toda la información necesaria.
    desk_to_zone = {desk: zone for zone, desks in raw_data.get('Desks_Z', {}).items() for desk in desks}
    employee_to_group = {emp: group for group, emps in raw_data.get('Employees_G', {}).items() for emp in emps}
    group_sizes = {group: len(emps) for group, emps in raw_data.get('Employees_G', {}).items()}
    
    df_assignments['Zona'] = df_assignments['Escritorio'].map(desk_to_zone)
    df_assignments['Grupo'] = df_assignments['Empleado'].map(employee_to_group)
    df_assignments['Tamaño_Grupo'] = df_assignments['Grupo'].map(group_sizes)
    
    # --- FIN DE LAS MEJORAS ---
    
    # Las funciones de análisis ahora reciben el DataFrame enriquecido o los datos que necesitan.
    _analyze_desk_occupancy(df_assignments, model_data['sets']['Desks'])
    _analyze_preference_mismatches(df_assignments, raw_data) # Pasa raw_data para ser más robusto
    _analyze_group_dispersion(df_assignments)
    if not df_meetings.empty:
        _analyze_full_group_attendance(df_assignments, df_meetings)
    _analyze_desk_compatibility(df_assignments, raw_data)
    _analyze_employee_assignments(df_assignments)