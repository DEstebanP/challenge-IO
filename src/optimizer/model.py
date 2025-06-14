import pyomo.environ as pyo
import pandas as pd

# --- Funciones "Rule" para el Modelo ---
# Es una buena práctica definir la lógica de las restricciones y objetivos
# en funciones separadas para mayor claridad.

def _objective_rule(model):
    """
    Regla para la función objetivo: Maximizar las preferencias de días.
    """
    return sum(
        model.P_ek[e, k] * model.X_edk[e, d, k]
        for e in model.Employees
        for d in model.Desks
        for k in model.Days
    )

def _attendance_window_rule(model, e):
    """
    Regla para la restricción de asistencia: Cada empleado asiste entre 2 y 3 días.
    """
    total_days_attended = sum(model.X_edk[e, d, k] for d in model.Desks for k in model.Days)
    return pyo.inequality(2, total_days_attended, 3)

def _unique_desk_occupancy_rule(model, d, k):
    """
    Regla para la restricción de ocupación: Un escritorio es usado por máximo un empleado por día.
    """
    return sum(model.X_edk[e, d, k] for e in model.Employees) == 1

def _unique_employee_assignment_rule(model, e, k):
    """
    Regla para la restricción de asignación: Un empleado usa máximo un escritorio por día.
    """
    return sum(model.X_edk[e, d, k] for d in model.Desks) <= 1

def _compatibility_rule(model, e, d, k):
    """
    Regla para la restricción de compatibilidad: La asignación debe ser compatible.
    """
    return model.X_edk[e, d, k] <= model.C_ed[e, d]

def _meeting_uniqueness_rule(model, g):
    """
    Regla para la restricción de unicidad de reunión: Cada grupo tiene una sola reunión.
    """
    return sum(model.Y_gk[g, k] for k in model.Days) == 1

def _mandatory_meeting_attendance_rule(model, e, g, k):
    """
    Regla para la restricción de asistencia obligatoria: Si es día de reunión del grupo, el empleado debe asistir.
    """
    # Esta restricción solo aplica si el empleado 'e' pertenece al grupo 'g'.
    if model.M_eg[e, g] == 0:
        # Si no pertenece, se omite la restricción para esta combinación.
        return pyo.Constraint.Skip
    
    # Si pertenece, se aplica la regla de implicación: Y_gk=1 => sum(X_edk) >= 1
    return sum(model.X_edk[e, d, k] for d in model.Desks) >= model.Y_gk[g, k]

def _process_results(model):
    """
    Procesa los resultados del modelo resuelto y los devuelve en un formato legible.
    """
    if str(model.results.solver.status) != 'ok' or str(model.results.solver.termination_condition) != 'optimal':
        print("No se encontró una solución óptima.")
        print(f"Estado del Solver: {model.results.solver.status}")
        print(f"Condición de Terminación: {model.results.solver.termination_condition}")
        return None

    # Procesar asignaciones de escritorios
    assignments_list = []
    for e in model.Employees:
        for d in model.Desks:
            for k in model.Days:
                if pyo.value(model.X_edk[e, d, k]) == 1:
                    assignments_list.append({
                        'Empleado': e,
                        'Escritorio': d,
                        'Dia': k
                    })
    
    # Procesar días de reunión de grupos
    meeting_days_list = []
    for g in model.Groups:
        for k in model.Days:
            if pyo.value(model.Y_gk[g, k]) == 1:
                meeting_days_list.append({
                    'Grupo': g,
                    'Dia_Reunion': k
                })

    # Usar pandas para un formato de salida más amigable
    df_assignments = pd.DataFrame(assignments_list)
    df_meetings = pd.DataFrame(meeting_days_list)

    return {
        'asignaciones': df_assignments,
        'reuniones': df_meetings,
        'valor_objetivo': pyo.value(model.objective)
    }


# --- Función Principal del Módulo ---

def build_and_solve(model_data):
    """
    Construye el modelo de Pyomo, lo resuelve y devuelve los resultados.
    """
    print("Construyendo el modelo de Pyomo...")
    
    # 1. Crear la instancia del modelo
    model = pyo.ConcreteModel(name="Asignacion_Puestos_v1")

    # 2. Definir los Componentes del Modelo
    
    # Sets
    model.Employees = pyo.Set(initialize=model_data['sets']['Employees'])
    model.Desks = pyo.Set(initialize=model_data['sets']['Desks'])
    model.Days = pyo.Set(initialize=model_data['sets']['Days'])
    model.Groups = pyo.Set(initialize=model_data['sets']['Groups'])

    # Parámetros
    model.P_ek = pyo.Param(model.Employees, model.Days, initialize=model_data['params']['P_ek'])
    model.C_ed = pyo.Param(model.Employees, model.Desks, initialize=model_data['params']['C_ed'])
    model.M_eg = pyo.Param(model.Employees, model.Groups, initialize=model_data['params']['M_eg'])

    # Variables de Decisión
    model.X_edk = pyo.Var(model.Employees, model.Desks, model.Days, domain=pyo.Binary)
    model.Y_gk = pyo.Var(model.Groups, model.Days, domain=pyo.Binary)

    # 3. Añadir Función Objetivo y Restricciones al Modelo
    
    # Objetivo
    model.objective = pyo.Objective(rule=_objective_rule, sense=pyo.maximize)

    # Restricciones
    model.attendance_constraint = pyo.Constraint(model.Employees, rule=_attendance_window_rule)
    model.unique_desk_constraint = pyo.Constraint(model.Desks, model.Days, rule=_unique_desk_occupancy_rule)
    model.unique_employee_constraint = pyo.Constraint(model.Employees, model.Days, rule=_unique_employee_assignment_rule)
    model.compatibility_constraint = pyo.Constraint(model.Employees, model.Desks, model.Days, rule=_compatibility_rule)
    model.meeting_uniqueness_constraint = pyo.Constraint(model.Groups, rule=_meeting_uniqueness_rule)
    model.mandatory_attendance_constraint = pyo.Constraint(model.Employees, model.Groups, model.Days, rule=_mandatory_meeting_attendance_rule)
    
    print("Modelo construido. Iniciando la resolución...")
    
    # 4. Resolver el Modelo
    solver = pyo.SolverFactory('glpk')
    model.results = solver.solve(model, tee=True) # tee=True muestra el log del solver

    print("Resolución finalizada.")
    
    # 5. Procesar y Devolver Resultados
    return _process_results(model)