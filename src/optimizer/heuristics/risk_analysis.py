def calculate_risk_and_top_desks(raw_data):
    """
    Calcula el índice de riesgo de cada empleado y devuelve una lista ordenada
    de los escritorios recomendados (con mayor potencial de cohesión).
    """
    
    # --- 1. Preparar Estructuras de Datos Auxiliares (igual que antes) ---
    desk_to_zone_map = {d: z for z, desks in raw_data.get('Desks_Z', {}).items() for d in desks}
    employee_to_group_map = {e: g for g, emps in raw_data.get('Employees_G', {}).items() for e in emps}
    desk_compatibilities = raw_data.get('Desks_E', {})
    employees_in_group = raw_data.get('Employees_G', {})
    
    employee_risk_data = {}

    # --- 2. Calcular para Cada Empleado ---
    for employee in raw_data.get('Employees', []):
        
        compatible_desks_for_employee = desk_compatibilities.get(employee, [])
        
        if not compatible_desks_for_employee:
            employee_risk_data[employee] = {'risk_index': 1.0, 'recommended_desks': []}
            continue
            
        employee_group = employee_to_group_map.get(employee)
        if not employee_group:
            employee_risk_data[employee] = {'risk_index': 0.0, 'recommended_desks': compatible_desks_for_employee[:3]}
            continue

        teammates = [e for e in employees_in_group[employee_group] if e != employee]
        desk_risk_details = []

        # --- 3. Evaluar el Riesgo de cada Escritorio Compatible ---
        for desk in compatible_desks_for_employee:
            # ... (Lógica para calcular desk_risk, igual que antes) ...
            desk_zone = desk_to_zone_map.get(desk)
            if not desk_zone: continue
            total_teammate_options_in_zone = sum(1 for teammate in teammates for d_teammate in desk_compatibilities.get(teammate, []) if desk_to_zone_map.get(d_teammate) == desk_zone)
            desk_risk = 1 / (1 + total_teammate_options_in_zone)
            desk_risk_details.append((desk_risk, desk))

        if not desk_risk_details:
            employee_risk_data[employee] = {'risk_index': 1.0, 'recommended_desks': []}
            continue

        # 4. Ordenar la lista de escritorios por su riesgo (de menor a mayor)
        desk_risk_details.sort(key=lambda item: item[0])
        
        # 5. Extraer solo los nombres de los 3 mejores escritorios
        top_3_desks = [desk for risk, desk in desk_risk_details[:3]]
        
        # 6. Calcular el riesgo promedio
        avg_risk_index = sum(risk for risk, desk in desk_risk_details) / len(desk_risk_details)

        # 7. Guardar la nueva estructura de datos
        employee_risk_data[employee] = {
            'risk_index': avg_risk_index,
            'recommended_desks': top_3_desks
        }
        
        
    return employee_risk_data