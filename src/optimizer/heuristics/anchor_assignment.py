def assign_anchor_desks(raw_data, risk_data):
    """
    Asigna un escritorio "ancla" a cada empleado usando una heurística estratégica.
    Prioriza a los empleados con mayor riesgo de aislamiento y les asigna el
    escritorio recomendado que mejor equilibre la carga.

    Args:
        raw_data (dict): El diccionario con los datos crudos del JSON.
        risk_data (dict): El diccionario con los resultados de la Etapa 0, que contiene
                          el 'risk_index' y la lista de 'recommended_desks' por empleado.

    Returns:
        dict: Un diccionario que mapea cada ID de empleado a su ID de escritorio ancla.
    """
    
    # --- Extracción de Datos ---
    all_employees = raw_data.get('Employees', [])
    all_desks = raw_data.get('Desks', [])
    desk_compatibilities = raw_data.get('Desks_E', {})

    # --- Paso 1: Recopilar Datos para el Ordenamiento ---
    # Creamos una lista de tuplas con toda la información necesaria para ordenar:
    # (índice de riesgo, número de opciones, id del empleado)
    employee_priority_list = []
    for e in all_employees:
        num_options = len(desk_compatibilities.get(e, []))
        # Obtenemos el riesgo del diccionario generado en la Etapa 0
        risk_index = risk_data.get(e, {}).get('risk_index', 1.0) # Por defecto, riesgo máximo
        employee_priority_list.append((risk_index, num_options, e))

    # --- Paso 2: Ordenamiento Estratégico (Doble Criterio) ---
    # Usamos una clave de ordenamiento personalizada:
    # 1. Ordena por el índice de riesgo en orden DESCENDENTE (el -x[0] invierte el orden).
    # 2. Si hay empate en el riesgo, ordena por el número de opciones en orden ASCENDENTE (x[1]).
    employee_priority_list.sort(key=lambda x: (-x[0], x[1]))

    # --- Paso 3: Inicializar Contadores y Resultados ---
    desk_usage_counts = {desk: 0 for desk in all_desks}
    anchor_desk_assignments = {}

    # --- Paso 4: Asignar Iterativamente con la Nueva Lógica ---
    # Recorremos la lista ya ordenada estratégicamente.
    for risk, num_options, employee_id in employee_priority_list:
        
        # Obtenemos la lista de los mejores escritorios recomendados de la Etapa 0
        recommended_desks = risk_data.get(employee_id, {}).get('recommended_desks', [])
        
        # Si no hay escritorios recomendados o compatibles, asignamos None.
        if not recommended_desks:
            anchor_desk_assignments[employee_id] = None
            continue

        # --- Lógica de Selección Mejorada ---
        # En lugar de buscar entre TODOS los escritorios compatibles, ahora solo
        # consideramos el "Top 3" recomendado. De entre esas excelentes opciones,
        # elegimos la que tenga la menor carga actual.
        best_desk = min(recommended_desks, key=lambda d: desk_usage_counts.get(d, 0))
        
        anchor_desk_assignments[employee_id] = best_desk
        
        # Incrementamos el contador de uso para el escritorio elegido.
        if best_desk is not None:
            desk_usage_counts[best_desk] += 1

    return anchor_desk_assignments

# --- Ejemplo de cómo se usaría esta función ---
if __name__ == '__main__':
    # Este bloque es solo para demostrar el funcionamiento.
    # En tu proyecto, llamarías a esta función desde tu script principal (main.py).
    
    # 1. Se simulan los datos crudos
    sample_raw_data = { "Employees": ["Ana", "Beto"], "Desks": ["D1", "D2"], "Desks_E": {"Ana": ["D1", "D2"], "Beto": ["D1"]} }
    
    # 2. Se simula la salida de la Etapa 0 (Análisis de Riesgo)
    sample_risk_data = {
        "Ana": {"risk_index": 0.9, "recommended_desks": ["D1", "D2"]}, # Alto riesgo
        "Beto": {"risk_index": 0.2, "recommended_desks": ["D1", "D2"]}      # Bajo riesgo
    }

    # El orden de procesamiento será: Ana (riesgo 0.9) y luego Beto (riesgo 0.2).
    
    # 3. Se llama a la función de Etapa 2 con ambas piezas de información
    anchor_assignments = assign_anchor_desks(sample_raw_data, sample_risk_data)
    
    print("Asignaciones de Escritorios Ancla (Estratégicas):")
    print(anchor_assignments)
    # Resultado esperado: {'Ana': 'D1', 'Beto': 'D1'} 
    # Ana es procesada primero. Sus opciones recomendadas son D1 y D2. Ambas tienen 0 usos.
    # Elige D1. Luego Beto es procesado y su única opción es D1.