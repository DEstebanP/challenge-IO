import argparse
import pandas as pd

# Importamos las funciones principales que hemos creado en los otros módulos.
from data.load_data import load_and_preprocess_data
from optimizer.model import build_and_solve

def main():
    """
    Función principal que orquesta la ejecución del modelo de optimización.
    """
    # Se configura para aceptar el nombre del archivo de instancia desde la terminal.
    parser = argparse.ArgumentParser(
        description="Script principal para resolver el reto de asignación de puestos ASOCIO."
    )
    parser.add_argument(
        "--file",
        type=str,
        required=True,
        help='Nombre del archivo de la instancia JSON a resolver. Ejemplo: "instance10.json"'
    )
    args = parser.parse_args()

    # --- PASO 1: Cargar y preprocesar los datos de la instancia ---
    print(f"Iniciando proceso para la instancia: {args.file}")
    print("----------------------------------------------------")
    print("1. Cargando y preprocesando datos...")
    
    model_data = load_and_preprocess_data(args.file)

    if not model_data:
        print("Finalizando ejecución debido a un error en la carga de datos.")
        return # Termina el script si no se pudieron cargar los datos

    print("   Datos cargados exitosamente.")

    # --- PASO 2: Construir y resolver el modelo de optimización ---
    print("\n2. Construyendo y resolviendo el modelo con Pyomo y GLPK...")
    
    results = build_and_solve(model_data)

    # --- PASO 3: Presentar los resultados ---
    print("\n----------------------------------------------------")
    if results:
        print("3. ¡Solución Óptima Encontrada! Mostrando resultados:")
        
        # Opciones para que pandas muestre todas las filas de los resultados
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', 100) # Ajusta el ancho de la tabla

        print(f"\nValor Máximo de la Función Objetivo (Suma de Preferencias): {results['valor_objetivo']:.2f}")
        
        print("\n--- Días de Reunión por Grupo ---")
        print(results['reuniones'].to_string(index=False))
        
        print("\n--- Asignaciones de Escritorios por Empleado y Día ---")
        # Se ordena el resultado para mejor legibilidad
        sorted_assignments = results['asignaciones'].sort_values(by=['Dia', 'Empleado'])
        print(sorted_assignments.to_string(index=False))

    else:
        print("3. El modelo no pudo encontrar una solución óptima.")
    
    print("\n----------------------------------------------------")
    print("Proceso finalizado.")


# Este es el punto de entrada estándar para un script de Python.
if __name__ == "__main__":
    main()