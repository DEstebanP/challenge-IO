def assign_anchor_desks(raw_data):
    """
    Asigna un escritorio "ancla" a cada empleado usando un algoritmo "greedy"
    que prioriza a los empleados con menos opciones y equilibra la carga.

    Args:
        raw_data (dict): El diccionario completo cargado desde el archivo JSON,
                         que contiene 'Employees', 'Desks' y 'Desks_E'.

    Returns:
        dict: Un diccionario que mapea cada ID de empleado a su ID de escritorio ancla.
              Ejemplo: {'E0': 'D5', 'E1': 'D8', ...}
    """
    
    # --- Extracción de Datos ---
    all_employees = raw_data.get('Employees', [])
    all_desks = raw_data.get('Desks', [])
    desk_compatibilities = raw_data.get('Desks_E', {})

    # --- Paso 1: Calcular la Flexibilidad de Cada Empleado ---
    # Creamos una lista de tuplas (numero_de_opciones, id_del_empleado)
    # para poder ordenarla fácilmente.
    employee_options = []
    for e in all_employees:
        num_options = len(desk_compatibilities.get(e, []))
        employee_options.append((num_options, e))

    # --- Paso 2: Ordenar por Escasez ---
    # Ordenamos la lista. Python ordena las tuplas por su primer elemento por defecto,
    # así que los empleados con menos opciones quedarán al principio.
    employee_options.sort()

    # --- Paso 3: Inicializar Contadores y Estructura de Resultados ---
    # Un diccionario para contar cuántos empleados han sido anclados a cada escritorio.
    desk_usage_counts = {desk: 0 for desk in all_desks}
    # El diccionario final que contendrá las asignaciones.
    anchor_desk_assignments = {}

    # --- Paso 4: Asignar Iterativamente ---
    # Recorremos la lista ordenada de empleados, del más restringido al más flexible.
    for num_options, employee_id in employee_options:
        
        compatible_desks = desk_compatibilities.get(employee_id, [])
        
        # Caso de seguridad: si un empleado no tiene escritorios compatibles.
        if not compatible_desks:
            anchor_desk_assignments[employee_id] = None # O se podría lanzar un error
            continue

        # Lógica para encontrar el mejor escritorio:
        # De la lista de escritorios compatibles para este empleado, encontramos
        # aquel que tenga el menor número de asignaciones hasta el momento.
        # La función min() con una clave lambda es una forma elegante y eficiente de hacerlo.
        best_desk = min(compatible_desks, key=lambda d: desk_usage_counts[d])
        
        # Asignamos el escritorio ancla encontrado a nuestro empleado.
        anchor_desk_assignments[employee_id] = best_desk
        
        # Incrementamos el contador de uso para ese escritorio.
        desk_usage_counts[best_desk] += 1

    return anchor_desk_assignments

# --- Ejemplo de cómo se usaría esta función ---
if __name__ == '__main__':
    # Este bloque es solo para demostrar el funcionamiento.
    # En tu proyecto, llamarías a esta función desde tu script principal (main.py).
    
    # Simulamos la carga de datos de una instancia.
    # (Este es un extracto de instance1.json)
    sample_raw_data = {
        "Employees": ["E0", "E1", "E2", "E3", "E4"],
        "Desks": ["D0", "D1", "D2", "D3", "D4"],
        "Desks_E": {
            "E0": ["D4", "D3", "D2"],      # 3 opciones
            "E1": ["D2", "D4"],            # 2 opciones
            "E2": ["D1", "D3", "D0"],      # 3 opciones
            "E3": ["D4", "D1"],            # 2 opciones
            "E4": ["D4"]                   # 1 opción (el más restringido)
        }
    }
    
    # Llamamos a la función para obtener el mapeo de anclas.
    anchor_assignments = assign_anchor_desks(sample_raw_data)
    
    print("Asignaciones de Escritorios Ancla:")
    print(anchor_assignments)
    
    # Resultado esperado (el orden de E1/E3 y E0/E2 puede variar si hay empates):
    # El algoritmo procesará en el orden: E4, E1, E3, E0, E2
    # E4 -> D4 (única opción)
    # E1 -> D2 (opciones D2, D4; D2 tiene 0 usos, D4 tiene 1)
    # E3 -> D1 (opciones D1, D4; D1 tiene 0 usos, D4 tiene 1)
    # E0 -> D3 (opciones D4,D3,D2; D3 tiene 0 usos)
    # E2 -> D0 (opciones D1,D3,D0; D0 tiene 0 usos)
    # Salida: {'E4': 'D4', 'E1': 'D2', 'E3': 'D1', 'E0': 'D3', 'E2': 'D0'}