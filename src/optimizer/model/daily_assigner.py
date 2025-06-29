import pyomo.environ as pyo
import pandas as pd

# --- Funciones "Rule" para el Modelo de Asignación Diaria ---

# --- Objetivo: Minimizar Aislamiento y Desviación de Ancla ---
def _daily_objective_rule(model):
    """
    Función Objetivo: Minimizar una suma ponderada de penalizaciones.
    La mayor penalización es por aislar a un empleado.
    """
    # Penalización total por cada caso de aislamiento detectado
    isolation_penalty = model.w_aislamiento * sum(
        model.I_gz[g, z] for g in model.Groups for z in model.Zones
    )
    
    # Penalización total por cada empleado que no es asignado a su escritorio ancla
    consistency_penalty = model.w_consistencia * sum(
        model.SeDesvia_e[e] for e in model.Attending_Employees
    )
    
    return isolation_penalty + consistency_penalty

# --- Restricciones de Asignación Fundamentales ---
def _mandatory_assignment_rule(model, e):
    """Cada empleado que asiste hoy DEBE ser asignado a exactamente un escritorio."""
    return sum(model.X_ed[e, d] for d in model.CompatibleDesks[e]) == 1

def _unique_desk_occupancy_rule_step3(model, d):
    """Cada escritorio es usado por máximo una persona."""
    # Sumamos solo sobre los empleados que asisten hoy y son compatibles con el escritorio 'd'
    return sum(model.X_ed[e, d] for e in model.Attending_Employees if (e,d) in model.ValidDailyAssignments) <= 1

# --- Restricciones para la Lógica de Aislamiento ---
def _isolation_logic_rule1(model, g, z):
    """Regla 1 de Aislamiento: Exclusividad mutua."""
    return model.I_gz[g, z] + model.GE2_gz[g, z] <= 1

def _isolation_logic_rule2(model, g, z):
    """Regla 2 de Aislamiento: Vínculo de límite inferior."""
    count = sum(model.X_ed[e, d] for e, d in model.ValidDailyAssignments 
                if model.M_eg[e, g] == 1 and model.L_dz[d, z] == 1)
    return count >= model.I_gz[g, z] + 2 * model.GE2_gz[g, z]

def _isolation_logic_rule3(model, g, z):
    """Regla 3 de Aislamiento: Vínculo de límite superior (Big M)."""
    count = sum(model.X_ed[e, d] for e, d in model.ValidDailyAssignments
                if model.M_eg[e, g] == 1 and model.L_dz[d, z] == 1)
    M = len(model.Attending_Employees)
    return count <= model.I_gz[g, z] + M * model.GE2_gz[g, z]

# --- Restricción para la Lógica de Consistencia ---
def _consistency_link_rule_step3(model, e):
    """
    Regla de vínculo para la consistencia: Activa SeDesvia_e si el empleado 'e'
    no es asignado a su escritorio ancla.
    """
    anchor_desk = model.AnchorAssignments[e]
    
    # Si el escritorio ancla no es compatible con el empleado, no se puede forzar la consistencia.
    if anchor_desk is None or (e, anchor_desk) not in model.ValidDailyAssignments:
        # Forzamos la desviación si el ancla no es válida
        return model.SeDesvia_e[e] == 1

    # La bandera de desviación se activa (>=1) si la asignación al ancla es 0.
    # Como la variable es binaria, la forzará a ser 1.
    return model.SeDesvia_e[e] >= 1 - model.X_ed[e, anchor_desk]

# --- Función Principal del Módulo ---
def solve_daily_assignment_model(daily_data):
    """
    Construye y resuelve el modelo de Pyomo para la asignación de un solo día (Paso 3).
    """
    model = pyo.ConcreteModel(name="Asignacion_Diaria_Step3")

    # --- Sets (Conjuntos para este día) ---
    model.Attending_Employees = pyo.Set(initialize=daily_data['sets']['Attending_Employees'])
    model.Desks = pyo.Set(initialize=daily_data['sets']['Desks'])
    model.Groups = pyo.Set(initialize=daily_data['sets']['Groups'])
    model.Zones = pyo.Set(initialize=daily_data['sets']['Zones'])
    
    # Set optimizado de asignaciones válidas solo para los empleados que asisten hoy
    model.ValidDailyAssignments = pyo.Set(
        initialize=daily_data['sets']['Valid_Daily_Assignments'], 
        dimen=2
    )
    # Un set auxiliar para que la restricción de asignación sea más eficiente
    model.CompatibleDesks = pyo.Set(
        model.Attending_Employees, 
        initialize=lambda m, e: [d for (emp, d) in m.ValidDailyAssignments if emp == e]
    )

    # --- Parameters (Parámetros para este día) ---
    model.M_eg = pyo.Param(model.Attending_Employees, model.Groups, initialize=daily_data['params']['M_eg'])
    model.L_dz = pyo.Param(model.Desks, model.Zones, initialize=daily_data['params']['L_dz'])
    model.AnchorAssignments = pyo.Param(model.Attending_Employees, within=pyo.Any, initialize=daily_data['params']['Anchor_Assignments'])
    model.w_aislamiento = pyo.Param(initialize=daily_data['params']['w_aislamiento'])
    model.w_consistencia = pyo.Param(initialize=daily_data['params']['w_consistencia'])

    # --- Variables de Decisión (para este día) ---
    model.X_ed = pyo.Var(model.ValidDailyAssignments, domain=pyo.Binary)
    model.I_gz = pyo.Var(model.Groups, model.Zones, domain=pyo.Binary)
    model.GE2_gz = pyo.Var(model.Groups, model.Zones, domain=pyo.Binary)
    model.SeDesvia_e = pyo.Var(model.Attending_Employees, domain=pyo.Binary)

    # --- Función Objetivo ---
    model.objective = pyo.Objective(rule=_daily_objective_rule, sense=pyo.minimize)

    # --- Restricciones ---
    model.mandatory_assignment = pyo.Constraint(model.Attending_Employees, rule=_mandatory_assignment_rule)
    model.unique_desk_occupancy = pyo.Constraint(model.Desks, rule=_unique_desk_occupancy_rule_step3)
    model.isolation_logic1 = pyo.Constraint(model.Groups, model.Zones, rule=_isolation_logic_rule1)
    model.isolation_logic2 = pyo.Constraint(model.Groups, model.Zones, rule=_isolation_logic_rule2)
    model.isolation_logic3 = pyo.Constraint(model.Groups, model.Zones, rule=_isolation_logic_rule3)
    model.consistency_link = pyo.Constraint(model.Attending_Employees, rule=_consistency_link_rule_step3)

    # --- Resolver ---
    solver = pyo.SolverFactory('cbc')
    solver.options['seconds'] = 20 # Límite de 120 segundos por día
    solver.options['ratioGap'] = 0.05
    results = solver.solve(model, tee=False)

    term_cond = results.solver.termination_condition
    status = results.solver.status
    
    solution_is_acceptable = (
        term_cond in [pyo.TerminationCondition.optimal, pyo.TerminationCondition.feasible] 
        or
        (term_cond == pyo.TerminationCondition.maxTimeLimit and len(results.solution.items()) > 0)
    )

    if not solution_is_acceptable:
        print(f"  -> El día {daily_data['day']} no tuvo solución factible. Condición: {term_cond}")
        # Devolvemos None para la solución y un gap 'infinito' para indicar fallo
        return None, float('inf')

    # 1. Extraer los límites del problema resuelto
    # Usamos try-except por si el solver no reporta los límites
    try:
        # Para un problema de MINIMIZACIÓN:
        # El límite inferior es la mejor cota teórica.
        # El límite superior es la mejor solución entera encontrada.
        lower_bound = results.problem[0].lower_bound
        upper_bound = results.problem[0].upper_bound
        
        # 2. Calcular el gap
        if abs(upper_bound) > 1e-9: # Evitar división por cero
            gap = abs(upper_bound - lower_bound) / abs(upper_bound)
        else:
            gap = 0.0
            
    except (AttributeError, IndexError):
        # Si no se pueden leer los límites, no podemos calcular el gap.
        gap = None

    if term_cond == pyo.TerminationCondition.optimal:
        # Mensaje de éxito si la solución es perfecta.
        print(f"  -> Éxito para el día {daily_data['day']}: Solución óptima encontrada (Gap: {gap * 100:.2f}%).")
    else:
        # Mensaje de alerta para los demás casos (límite de tiempo, gap, etc.).
        print(f"  -> Alerta para el día {daily_data['day']}: Se usará solución no óptima (Condición: {term_cond}, Gap: {gap * 100:.2f}%).")

    final_assignments = []
    for (e, d) in model.ValidDailyAssignments:
        if pyo.value(model.X_ed[e, d], exception=False) >= 0.99:
            final_assignments.append({'Empleado': e, 'Escritorio': d, 'Dia': daily_data['day']})

    # 3. Devolver tanto el DataFrame de la solución como el gap calculado
    return pd.DataFrame(final_assignments), gap