import pyomo.environ as pyo
import pandas as pd

# --- Lógica de Restricciones para el Modelo de Horarios ---

def _objective_rule_step1(model):
    """
    Función Objetivo: Maximizar la suma de las puntuaciones de preferencia de los empleados
    basado en los días que asisten.
    """
    return sum(
        model.S_ek[e, k] * model.Asiste_ek[e, k]
        for e in model.Employees
        for k in model.Days
    )

def _attendance_window_rule_step1(model, e):
    """
    Restricción: Cada empleado debe asistir entre 2 y 3 días.
    """
    total_days_attended = sum(model.Asiste_ek[e, k] for k in model.Days)
    return pyo.inequality(2, total_days_attended, 3)

def _meeting_uniqueness_rule_step1(model, g):
    """
    Restricción: Cada grupo tiene exactamente un día de reunión.
    """
    return sum(model.Y_gk[g, k] for k in model.Days) == 1

def _mandatory_meeting_attendance_rule_step1(model, e, g, k):
    """
    Restricción de Vínculo: Si es día de reunión del grupo 'g', todos sus miembros 'e' deben asistir.
    La asistencia del empleado (Asiste_ek) debe ser al menos tan grande como la variable de reunión (Y_gk).
    """
    if model.M_eg[e, g] == 0:
        return pyo.Constraint.Skip  # La restricción no aplica si el empleado no está en el grupo
    
    return model.Asiste_ek[e, k] >= model.Y_gk[g, k]

# --- Procesador de Resultados para el Modelo de Horarios ---

def _process_schedule_results(model):
    """
    Procesa los resultados del modelo de horarios y los devuelve en un formato estructurado.
    """
    acceptable_termination = [pyo.TerminationCondition.optimal, pyo.TerminationCondition.feasible]
    
    if model.results.solver.termination_condition not in acceptable_termination:
        print("El solver no encontró una solución exitosa para el horario.")
        print(f"Condición de Terminación: {model.results.solver.termination_condition}")
        return None

    # Procesar días de reunión
    meeting_days = {g: k for g in model.Groups for k in model.Days if pyo.value(model.Y_gk[g, k]) == 1}
    
    # Procesar horario de asistencia
    weekly_schedule = {
        k: [e for e in model.Employees if pyo.value(model.Asiste_ek[e, k]) == 1]
        for k in model.Days
    }

    return {
        'dias_reunion': meeting_days,
        'horario_semanal': weekly_schedule,
        'valor_objetivo': pyo.value(model.objective)
    }

# --- Función Principal del Módulo ---

def solve_schedule_model(model_data):
    """
    Construye y resuelve el modelo de Pyomo para la Planificación Maestra de Horarios (Paso 1).
    """
    print("Construyendo el modelo de horarios (Paso 1)...")
    
    model = pyo.ConcreteModel(name="Planificacion_Horarios_Step1")

    # --- Sets (Conjuntos) ---
    # Notar que no necesitamos escritorios ni zonas en este paso
    model.Employees = pyo.Set(initialize=model_data['sets']['Employees'])
    model.Days = pyo.Set(initialize=model_data['sets']['Days'])
    model.Groups = pyo.Set(initialize=model_data['sets']['Groups'])

    # --- Parameters (Parámetros) ---
    # Notar que no necesitamos el parámetro de compatibilidad de escritorios C_ed
    model.S_ek = pyo.Param(model.Employees, model.Days, initialize=model_data['params']['S_ek'])
    model.M_eg = pyo.Param(model.Employees, model.Groups, initialize=model_data['params']['M_eg'])

    # --- Variables de Decisión ---
    # La variable de asignación ahora es mucho más simple: ¿asiste o no?
    model.Asiste_ek = pyo.Var(model.Employees, model.Days, domain=pyo.Binary)
    model.Y_gk = pyo.Var(model.Groups, model.Days, domain=pyo.Binary)

    # --- Función Objetivo ---
    model.objective = pyo.Objective(rule=_objective_rule_step1, sense=pyo.maximize)

    # --- Restricciones ---
    model.attendance_constraint = pyo.Constraint(model.Employees, rule=_attendance_window_rule_step1)
    model.meeting_uniqueness_constraint = pyo.Constraint(model.Groups, rule=_meeting_uniqueness_rule_step1)
    model.mandatory_attendance_constraint = pyo.Constraint(model.Employees, model.Groups, model.Days, rule=_mandatory_meeting_attendance_rule_step1)
    
    print("Modelo de horarios construido. Resolviendo...")
    
    # --- Resolver y Procesar ---
    solver = pyo.SolverFactory('cbc')
    model.results = solver.solve(model, tee=False) # tee=False para no mostrar el log detallado
    
    print("Resolución finalizada.")
    
    return _process_schedule_results(model)