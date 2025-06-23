import pyomo.environ as pyo

def solve_daily_assignment_model(day, attending_employees, anchor_map, raw_data, weights):
    """
    Resuelve el modelo de asignación optimizada para un único día.
    El objetivo es minimizar una función ponderada de aislamiento y falta de consistencia.

    Args:
        day (str): El día que se está resolviendo (ej: "L").
        attending_employees (list): Lista de empleados que asisten ese día.
        anchor_map (dict): Mapeo de empleado a su escritorio ancla.
        raw_data (dict): Datos crudos del JSON.
        weights (dict): Pesos para la función objetivo ('aislamiento', 'consistencia').

    Returns:
        list: Una lista de diccionarios con las asignaciones del día.
    """
    model = pyo.ConcreteModel(name=f"Asignacion_Diaria_{day}")

    # --- Sets Dinámicos (solo para los que asisten hoy) ---
    model.Attending_Employees = pyo.Set(initialize=attending_employees)
    model.All_Desks = pyo.Set(initialize=raw_data.get('Desks', []))
    model.All_Zones = pyo.Set(initialize=raw_data.get('Zones', []))
    
    employee_to_group = {emp: g for g, emps in raw_data.get('Employees_G', {}).items() for emp in emps}
    attending_groups_set = {employee_to_group[e] for e in attending_employees if e in employee_to_group}
    model.Attending_Groups = pyo.Set(initialize=list(attending_groups_set))

    # --- Parámetros ---
    desk_to_zone = {d: z for z, desks in raw_data.get('Desks_Z', {}).items() for d in desks}
    
    # Pares válidos de (empleado, escritorio) solo para los que asisten y son compatibles
    compatible_pairs = [
        (e, d) for e in model.Attending_Employees 
        for d in raw_data.get('Desks_E', {}).get(e, [])
    ]
    model.Valid_Pairs = pyo.Set(initialize=compatible_pairs, dimen=2)

    # --- Variables de Decisión ---
    model.X_ed = pyo.Var(model.Valid_Pairs, domain=pyo.Binary)
    model.I_gz = pyo.Var(model.Attending_Groups, model.All_Zones, domain=pyo.Binary)

    # --- Función Objetivo: MINIMIZAR penalizaciones ---
    def objective_rule(m):
        # Penalización por Aislamiento (muy alta)
        penalizacion_aislamiento = weights['aislamiento'] * sum(m.I_gz[g, z] for g in m.Attending_Groups for z in m.All_Zones)
        
        # Penalización por Consistencia (baja)
        # Se suma 1 por cada empleado que NO es asignado a su escritorio ancla
        penalizacion_consistencia = weights['consistencia'] * sum(
            m.X_ed[e, d] for e, d in m.Valid_Pairs if d != anchor_map.get(e)
        )
        return penalizacion_aislamiento + penalizacion_consistencia
    model.objective = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

    # --- Restricciones Fundamentales ---
    # 1. A cada empleado que asiste se le asigna un único escritorio
    def one_desk_per_employee_rule(m, e):
        return sum(m.X_ed[e, d_] for d_ in m.All_Desks if (e, d_) in m.Valid_Pairs) == 1
    model.one_desk_constraint = pyo.Constraint(model.Attending_Employees, rule=one_desk_per_employee_rule)

    # 2. Cada escritorio es usado por máximo un empleado
    def one_employee_per_desk_rule(m, d):
        return sum(m.X_ed[e, d] for e in m.Attending_Employees if (e, d) in m.Valid_Pairs) <= 1
    model.one_employee_constraint = pyo.Constraint(model.All_Desks, rule=one_employee_per_desk_rule)
 
    # --- Restricciones para el Aislamiento ---
    def get_employees_in_group_in_zone(m, g, z):
        return [e for e in m.Attending_Employees if employee_to_group.get(e) == g and (e, desk_to_zone.get(e)) == (e,z)]

    # I_gz se activa si exactamente un miembro del grupo g está en la zona z
    def isolation_link_rule_1(m, g, z):
        sum_expr = sum(m.X_ed[e, d] for e, d in m.Valid_Pairs if employee_to_group.get(e) == g and desk_to_zone.get(d) == z)
        return sum_expr >= m.I_gz[g, z]
    model.isolation_link_1 = pyo.Constraint(model.Attending_Groups, model.All_Zones, rule=isolation_link_rule_1)

    def isolation_link_rule_2(m, g, z):
        sum_expr = sum(m.X_ed[e, d] for e, d in m.Valid_Pairs if employee_to_group.get(e) == g and desk_to_zone.get(d) == z)
        # Si la suma es 0 o >= 2, I_gz debe ser 0. Si la suma es 1, I_gz puede ser 1.
        return sum_expr - 1 <= len(m.Attending_Employees) * (1 - m.I_gz[g, z])
    model.isolation_link_2 = pyo.Constraint(model.Attending_Groups, model.All_Zones, rule=isolation_link_rule_2)
    
    # --- Resolver el modelo del día ---
    solver = pyo.SolverFactory('cbc')
    solver.solve(model, tee=False)

    # --- Procesar y devolver los resultados del día ---
    assignments = []
    # Itera sobre las variables de asignación (X_ed)
    for (e, d), var in model.X_ed.items():
        # Se obtiene el valor de la variable de forma segura
        val = pyo.value(var) 
        # Se comprueba que el valor no sea nulo y que sea 1 (usando round para seguridad numérica)
        if val is not None and round(val) == 1:
            assignments.append({'Empleado': e, 'Escritorio': d, 'Dia': day})
    return assignments