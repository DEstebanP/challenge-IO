import json
import argparse
import os

def _create_parameter_S_ek(raw_data, penalty_cost):
    """
    Crea el parámetro S_ek (puntuación de asignación) con una penalización.

    Args:
        raw_data (dict): El diccionario completo cargado desde el archivo JSON.
        penalty_cost (float): El valor del costo (penalización) por asignar
                              un día no preferido. Debe ser un número positivo.

    Returns:
        dict: Un diccionario representando el parámetro S_ek.
              Las claves son tuplas (empleado, dia) y los valores son 1 o -C.
    """
    # Se obtienen los datos necesarios
    all_employees = raw_data.get('Employees', [])
    all_days = raw_data.get('Days', [])
    employee_day_preferences = raw_data.get('Days_E', {})

    # Se inicializa el diccionario para el parámetro S_ek
    S_ek = {}

    # Se itera sobre cada combinación posible
    for e in all_employees:
        for k in all_days:
            # Si el día es preferido, la puntuación es 1 (la recompensa)
            if k in employee_day_preferences.get(e, []):
                S_ek[(e, k)] = 1.0
            # Si el día NO es preferido, la puntuación es la penalización negativa
            else:
                S_ek[(e, k)] = -penalty_cost
    
    return S_ek

def _create_parameter_M_eg(raw_data):
    """
    Crea el parámetro M_eg (pertenencia de un empleado a un grupo).

    Args:
        raw_data (dict): El diccionario completo cargado desde el archivo JSON.

    Returns:
        dict: Un diccionario representando el parámetro M_eg.
              Las claves son tuplas (empleado, grupo) y los valores son 1 o 0.
    """
    # Se obtienen los datos necesarios.
    all_employees = raw_data.get('Employees', [])
    all_groups = raw_data.get('Groups', [])
    group_memberships = raw_data.get('Employees_G', {})

    # Se inicializa el diccionario para el parámetro.
    M_eg = {}

    # Se itera sobre cada combinación de empleado y grupo.
    for e in all_employees:
        for g in all_groups:
            # A diferencia de los otros parámetros, aquí la fuente de datos
            # (group_memberships) está organizada por grupo.
            # Por lo tanto, verificamos si el empleado 'e' está en la lista
            # de miembros del grupo 'g'.
            if e in group_memberships.get(g, []):
                M_eg[(e, g)] = 1
            else:
                M_eg[(e, g)] = 0
                
    return M_eg

def _create_parameter_L_dz(raw_data):
    """
    Crea el parámetro L_dz (pertenencia de un escritorio a una zona).
    """
    all_desks = raw_data.get('Desks', [])
    all_zones = raw_data.get('Zones', [])
    zone_to_desks_map = raw_data.get('Desks_Z', {})

    L_dz = {}
    for d in all_desks:
        for z in all_zones:
            desks_in_zone = zone_to_desks_map.get(z, [])
            if d in desks_in_zone:
                L_dz[(d, z)] = 1
            else:
                L_dz[(d, z)] = 0
    return L_dz

def load_and_preprocess_data(instance_name):
    """
    Función principal y pública del módulo. Carga los datos crudos de una instancia,
    los procesa y devuelve una estructura de datos lista para el modelo de optimización.

    Args:
        instance_name (str): El nombre del archivo de la instancia (ej: "instance10.json").

    Returns:
        dict: Un diccionario anidado que contiene los conjuntos y parámetros del modelo.
              Retorna None si ocurre un error al cargar el archivo.
    """
    # Obtener la ruta absoluta del directorio donde está este archivo (load_data.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Subir un nivel (a src/) y luego bajar a /data
    root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
    file_path = os.path.join(root_dir, 'data', instance_name)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print(f"Error Crítico: No se encontró el archivo de instancia en '{file_path}'.")
        return None
    
    # Se centraliza la creación de todos los parámetros llamando a las
    # funciones ayudantes correspondientes.
    s_ek_parameter = _create_parameter_S_ek(raw_data, 1)
    c_ed_parameter = _create_parameter_C_ed(raw_data)
    m_eg_parameter = _create_parameter_M_eg(raw_data)
    l_dz_parameter = _create_parameter_L_dz(raw_data)
    
    # Crear una lista de tuplas (e, d) solo para las asignaciones permitidas
    # basado en los datos de compatibilidad del archivo JSON ('Desks_E').
    valid_assignments_list = []
    desk_compatibilities = raw_data.get('Desks_E', {})
    for employee, allowed_desks in desk_compatibilities.items():
        for desk in allowed_desks:
            valid_assignments_list.append((employee, desk))
    
    # Se organiza la salida en un diccionario claro y estructurado.
    model_data = {
        'sets': {
            'Employees': raw_data.get('Employees', []),
            'Desks': raw_data.get('Desks', []),
            'Days': raw_data.get('Days', []),
            'Groups': raw_data.get('Groups', []),
            'Zones': raw_data.get('Zones', []),
            'Valid_Assignments': valid_assignments_list
        },
        'params': {
            'S_ek': s_ek_parameter,
            'M_eg': m_eg_parameter,
            'L_dz': l_dz_parameter,
        }
    }
    
    return model_data, raw_data


# Este bloque permite ejecutar el script directamente para hacer pruebas.
if __name__ == '__main__':
    # Se configura el parser para aceptar el nombre del archivo desde la terminal.
    parser = argparse.ArgumentParser(
        description="Carga y preprocesa los datos de una instancia para el reto ASOCIO."
    )
    parser.add_argument(
        "--file",
        type=str,
        required=True,
        help='Nombre del archivo de la instancia JSON. Ejemplo: "instance10.json"'
    )
    args = parser.parse_args()

    # Se llama a la función principal con el nombre del archivo proporcionado.
    print(f"Cargando instancia: {args.file}...")
    final_model_data = load_and_preprocess_data(args.file)

    if final_model_data:
        print("¡Datos cargados y procesados exitosamente!")
        print(final_model_data[0]['params']['S_ek'])

