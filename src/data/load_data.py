import json
import argparse
import os

def _create_parameter_P_ek(raw_data):
    """
    Crea el parámetro P_ek a partir de los datos de la instancia.
    Esta versión utiliza bucles for explícitos para mayor claridad en el proceso.

    Args:
        raw_data (dict): El diccionario cargado desde el archivo JSON de la instancia.

    Returns:
        dict: Un diccionario representando el parámetro P_ek.
              Las claves son tuplas (empleado, dia) y los valores son 1 o 0.
    """
    # Se obtienen los conjuntos de empleados y días para construir el parámetro.
    employees = raw_data.get('Employees', [])
    days = raw_data.get('Days', [])
    
    # Se obtiene el diccionario de preferencias de días de los empleados.
    employee_day_preferences = raw_data.get('Days_E', {})

    # Inicializamos el diccionario para el parámetro P_ek
    P_ek = {}

    # Se itera sobre cada empleado y cada día para construir la matriz completa.
    for e in employees:
        for k in days:
            # Se verifica si el día 'k' está en la lista de días preferidos del empleado 'e'.
            # Usar .get(e, []) es una buena práctica para evitar errores si un empleado
            # no tuviera una entrada en el diccionario.
            if k in employee_day_preferences.get(e, []):
                P_ek[(e, k)] = 1
            else:
                P_ek[(e, k)] = 0
    
    return P_ek

def _create_parameter_C_ed(raw_data):
    """
    Crea el parámetro C_ed (compatibilidad de escritorios por empleado).

    Args:
        raw_data (dict): El diccionario completo cargado desde el archivo JSON.

    Returns:
        dict: Un diccionario representando el parámetro C_ed.
              Las claves son tuplas (empleado, escritorio) y los valores son 1 o 0.
    """
    # Se obtienen los datos necesarios del diccionario principal.
    # Usar .get() con un valor por defecto previene errores si la clave no existe.
    all_employees = raw_data.get('Employees', [])
    all_desks = raw_data.get('Desks', [])
    desk_compatibilities = raw_data.get('Desks_E', {})

    # Se inicializa el diccionario que contendrá el parámetro.
    C_ed = {}

    # Se itera sobre cada combinación de empleado y escritorio.
    for e in all_employees:
        for d in all_desks:
            # Se revisa si el escritorio 'd' está en la lista de escritorios
            # compatibles para el empleado 'e'.
            if d in desk_compatibilities.get(e, []):
                C_ed[(e, d)] = 1
            else:
                C_ed[(e, d)] = 0
                
    return C_ed

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
    p_ek_parameter = _create_parameter_P_ek(raw_data)
    c_ed_parameter = _create_parameter_C_ed(raw_data)
    m_eg_parameter = _create_parameter_M_eg(raw_data)
    
    # Se organiza la salida en un diccionario claro y estructurado.
    model_data = {
        'sets': {
            'Employees': raw_data.get('Employees', []),
            'Desks': raw_data.get('Desks', []),
            'Days': raw_data.get('Days', []),
            'Groups': raw_data.get('Groups', []),
            'Zones': raw_data.get('Zones', []),
        },
        'params': {
            'P_ek': p_ek_parameter,
            'C_ed': c_ed_parameter,
            'M_eg': m_eg_parameter,
        }
    }
    
    return model_data, raw_data


# Este bloque permite ejecutar el script directamente para hacer pruebas.
if __name__ == '__main__':
    pass
    '''
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
    '''
