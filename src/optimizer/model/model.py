import pyomo.environ as pyo

# --- Lógica de Restricciones para el Modelo de Horarios ---

def _objective_rule_step1(model):
    """
    Función Objetivo Mejorada: Maximiza preferencias MENOS la penalización por riesgo.
    """
    # 1. El término original que recompensa las preferencias de días
    preference_score = sum(
        model.S_ek[e, k] * model.Asiste_ek[e, k]
        for e in model.Employees
        for k in model.Days
    )

    # 2. El NUEVO término que penaliza por programar empleados de alto riesgo
    # Se suma el riesgo de cada empleado por cada día que asiste.
    total_risk_penalty = model.w_riesgo * sum(
        model.Risk_Index[e] * model.Asiste_ek[e, k]
        for e in model.Employees
        for k in model.Days
    )
    
    # El objetivo final es el balance de ambos
    return preference_score - total_risk_penalty

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
    """
    if model.M_eg[e, g] == 0:
        return pyo.Constraint.Skip
    
    return model.Asiste_ek[e, k] >= model.Y_gk[g, k]

def _capacity_constraint_rule(model, k):
    """
    NUEVA RESTRICCIÓN de Capacidad: El número de empleados que asisten en un día 'k'
    no puede exceder el número total de escritorios disponibles.
    """
    employees_attending_on_day_k = sum(model.Asiste_ek[e, k] for e in model.Employees)
    total_desks = len(model.Desks)
    return employees_attending_on_day_k <= total_desks

# --- Procesador de Resultados para el Modelo de Horarios ---

def _process_schedule_results(model):
    """
    Procesa los resultados del modelo de horarios y los devuelve en un formato estructurado.
    """
    acceptable_termination = [pyo.TerminationCondition.optimal, pyo.TerminationCondition.feasible]
    
    if model.results.solver.termination_condition not in acceptable_termination:
        return None

    meeting_days = {g: k for g in model.Groups for k in model.Days if pyo.value(model.Y_gk[g, k]) == 1}
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

def solve_schedule_model(model_data, existing_cuts=[]):
    """
    Construye y resuelve el modelo de Pyomo para la Planificación Maestra de Horarios (Paso 1).
    """
    model = pyo.ConcreteModel(name="Planificacion_Horarios_Step1")

    # --- Sets (Conjuntos) ---
    model.Employees = pyo.Set(initialize=model_data['sets']['Employees'])
    model.Desks = pyo.Set(initialize=model_data['sets']['Desks']) # Necesario para len()
    model.Days = pyo.Set(initialize=model_data['sets']['Days'])
    model.Groups = pyo.Set(initialize=model_data['sets']['Groups'])

    # --- Parameters (Parámetros) ---
    model.S_ek = pyo.Param(model.Employees, model.Days, initialize=model_data['params']['S_ek'])
    model.M_eg = pyo.Param(model.Employees, model.Groups, initialize=model_data['params']['M_eg'])
    model.Risk_Index = pyo.Param(model.Employees, initialize=model_data['params']['Risk_Index'])
    model.w_riesgo = pyo.Param(initialize=model_data['params']['w_riesgo'])

    # --- Variables de Decisión ---
    model.Asiste_ek = pyo.Var(model.Employees, model.Days, domain=pyo.Binary)
    model.Y_gk = pyo.Var(model.Groups, model.Days, domain=pyo.Binary)

    # --- Función Objetivo ---
    model.objective = pyo.Objective(rule=_objective_rule_step1, sense=pyo.maximize)

    # --- Restricciones ---
    model.attendance_constraint = pyo.Constraint(model.Employees, rule=_attendance_window_rule_step1)
    model.meeting_uniqueness_constraint = pyo.Constraint(model.Groups, rule=_meeting_uniqueness_rule_step1)
    model.mandatory_attendance_constraint = pyo.Constraint(model.Employees, model.Groups, model.Days, rule=_mandatory_meeting_attendance_rule_step1)
    
    # RESTRICCIÓN AÑADIDA
    model.capacity_constraint = pyo.Constraint(model.Days, rule=_capacity_constraint_rule)
    
    model.feasibility_cuts = pyo.ConstraintList()
    
    # --- Restricciones de Corte (Aprendizaje Iterativo) ---
    # Se crea un contenedor para las restricciones de corte que vienen de Etapa 4
    for cut_info in existing_cuts:
        problematic_day = cut_info['day']
        problematic_employees = cut_info['employees']
        
        # La expresión de la suma para el corte
        expr = sum(model.Asiste_ek[e, problematic_day] for e in problematic_employees)
        
        # Se añade la restricción: sum(...) <= N - 1
        model.feasibility_cuts.add(expr <= len(problematic_employees) - 1)
    
    solver = pyo.SolverFactory('cbc')
    model.results = solver.solve(model, tee=False)
    
    return _process_schedule_results(model)