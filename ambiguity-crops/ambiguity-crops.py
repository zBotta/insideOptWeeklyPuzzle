"""
Pyomo model for the Ambiguity Crops problem.

This model considers two crops (A and B) with uncertain yields based on weather
 scenarios (wet and dry).

Requirements:
    pip install pyomo
    Install CBC, IPOPT (or SCIP) and ensure it's on PATH. If CBC is not found,
    the script will attempt 'scip'.

 Usage (PowerShell with python environment activated with Pyomo):
    python .\ambiguity-crops\pyomo_model.py --solve
    python .\ambiguity-crops\pyomo_model.py --solve --scenario wet
    python .\ambiguity-crops\pyomo_model.py --solve --scenario dry
    python .\ambiguity-crops\pyomo_model.py --solve --scenario both
    python .\ambiguity-crops\pyomo_model.py --solve --scenario maxmin
    python .\ambiguity-crops\pyomo_model.py --solve --scenario minmax_regret
    python .\ambiguity-crops\pyomo_model.py --solve --scenario multi_weighted --w-wet 0.7 --w-dry 0.3 --risk-lambda 0.1

"""
import argparse
from ast import main
import shutil
from pyomo.environ import (
    ConcreteModel,
    Var,
    Objective,
    Constraint,
    NonNegativeReals,
    Reals,
    SolverFactory,
    value,
    minimize,
    maximize,
    Expression,
)


SCENARIOS = {
    "wet": {
        "pre_sold_price_A": 3.90,
        "pre_sold_price_B": 3.90,
        "penalty_A": 1.50,
        "penalty_B": 1.45,
        "var_cost_A": 50.0,   # variable cost per acre (scenario table)
        "var_cost_B": 150.0,
        "yield_A": 800.0,     # units per acre
        "yield_B": 150.0,
        "spot_price_A": 2.50,
        "spot_price_B": 5.00,
    },
    "dry": {
        "pre_sold_price_A": 3.90,
        "pre_sold_price_B": 3.90,
        "penalty_A": 1.50,
        "penalty_B": 1.45,
        "var_cost_A": 200.0,
        "var_cost_B": 40.0,
        "yield_A": 300.0,
        "yield_B": 600.0,
        "spot_price_A": 4.50,
        "spot_price_B": 3.00,
    },
}

TOTAL_ACRES = 100.0
MIN_PROFIT = 50000.0
FIXED_COST_A = 150 # fixed cost for Crop A
FIXED_COST_B = 100 # fixed cost for Crop B


def summarize_model(m):
    """Produce results summary for both scenarios."""
    headers = ["Variable", "Wet Scenario", "Dry Scenario"]
    rows = [
        ["Acres of Crop A (S_A)", value(m.S_A), value(m.S_A)],
        ["Acres of Crop B (S_B)", value(m.S_B), value(m.S_B)],
        ["Pre-sold units of Crop A (pre_U_A)", value(m.pre_U_A), value(m.pre_U_A)],
        ["Pre-sold units of Crop B (pre_U_B)", value(m.pre_U_B), value(m.pre_U_B)],
        ["Produced units of Crop A (prod_U_A)", value(m.prod_U_A_wet), value(m.prod_U_A_dry)],
        ["Produced units of Crop B (prod_U_B)", value(m.prod_U_B_wet), value(m.prod_U_B_dry)],
        ["Shortfall A", value(m.short_A_wet), value(m.short_A_dry)],
        ["Shortfall B", value(m.short_B_wet), value(m.short_B_dry)],
        ["Profit in Wet scenario", value(m.profit_wet), ""],
        ["Profit in Dry scenario", "", value(m.profit_dry)],
    ]

    print("\n----- Model Summary -----")
    print("{:<40} {:<20} {:<20}".format(*headers))
    for row in rows:
        print("{:<40} {:<20} {:<20}".format(*row))
    print("------------------------\n")

def build_model():
    """Builds and returns the Pyomo model for the Ambiguity Crops problem."""
    m = ConcreteModel()

    # Variables
    m.S_A = Var(within=NonNegativeReals, bounds=(0, TOTAL_ACRES), doc="Acres of Crop A")
    m.S_B = Var(within=NonNegativeReals, bounds=(0, TOTAL_ACRES), doc="Acres of Crop B")

    m.pre_U_A = Var(within=NonNegativeReals, bounds=(0, 800 * TOTAL_ACRES), doc="Pre-sold units of Crop A")
    m.pre_U_B = Var(within=NonNegativeReals, bounds=(0, 600 * TOTAL_ACRES), doc="Pre-sold units of Crop B")

    m.prod_U_A_wet = Var(within=NonNegativeReals, bounds=(0, 800 * TOTAL_ACRES), doc="Produced units of Crop A")
    m.prod_U_B_wet = Var(within=NonNegativeReals, bounds=(0, 600 * TOTAL_ACRES), doc="Produced units of Crop B")
    m.prod_U_A_dry = Var(within=NonNegativeReals, bounds=(0, 800 * TOTAL_ACRES), doc="Produced units of Crop A")
    m.prod_U_B_dry = Var(within=NonNegativeReals, bounds=(0, 600 * TOTAL_ACRES), doc="Produced units of Crop B")

    m.short_A_wet = Var(within=NonNegativeReals, doc="Shortfall units of Crop A")
    m.short_B_wet = Var(within=NonNegativeReals, doc="Shortfall units of Crop B")
    m.short_A_dry = Var(within=NonNegativeReals, doc="Shortfall units of Crop A")
    m.short_B_dry = Var(within=NonNegativeReals, doc="Shortfall units of Crop B")

    # Cost, Benefit, and Penalty calculations for Wet scenario
    Cost_wet = - ( (SCENARIOS["wet"]["var_cost_A"] + FIXED_COST_A) * m.S_A + 
                (SCENARIOS["wet"]["var_cost_B"] + FIXED_COST_B) * m.S_B)

    Benefit_wet = SCENARIOS["wet"]["pre_sold_price_A"] * m.pre_U_A + \
                SCENARIOS["wet"]["pre_sold_price_B"] * m.pre_U_B + \
                SCENARIOS["wet"]["spot_price_A"] * (m.prod_U_A_wet - m.pre_U_A) + \
                SCENARIOS["wet"]["spot_price_B"] * (m.prod_U_B_wet - m.pre_U_B)

    Penalty_wet = - SCENARIOS["wet"]["penalty_A"] * m.short_A_wet - SCENARIOS["wet"]["penalty_B"] * m.short_B_wet


    Cost_dry = - ( (SCENARIOS["dry"]["var_cost_A"] + FIXED_COST_A) * m.S_A + 
                (SCENARIOS["dry"]["var_cost_B"] + FIXED_COST_B) * m.S_B)
    Benefit_dry = SCENARIOS["dry"]["pre_sold_price_A"] * m.pre_U_A + \
                SCENARIOS["dry"]["pre_sold_price_B"] * m.pre_U_B + \
                SCENARIOS["dry"]["spot_price_A"] * (m.prod_U_A_dry - m.pre_U_A) + \
                SCENARIOS["dry"]["spot_price_B"] * (m.prod_U_B_dry - m.pre_U_B)

    Penalty_dry = - SCENARIOS["dry"]["penalty_A"] * m.short_A_dry - SCENARIOS["dry"]["penalty_B"] * m.short_B_dry

    # Profit expressions (as Pyomo Expression components)
    m.profit_wet = Expression(expr=Benefit_wet + Cost_wet + Penalty_wet)
    m.profit_dry = Expression(expr=Benefit_dry + Cost_dry + Penalty_dry)

    # Constraints
    m.Const_Total_Acres = Constraint(expr=m.S_A + m.S_B == TOTAL_ACRES)

    # Attach constraints to the model (use m.<name> = Constraint(...))
    m.Const_A_wet = Constraint(expr=m.prod_U_A_wet == SCENARIOS["wet"]["yield_A"] * m.S_A)
    m.Const_B_wet = Constraint(expr=m.prod_U_B_wet == SCENARIOS["wet"]["yield_B"] * m.S_B)

    m.Const_A_dry = Constraint(expr=m.prod_U_A_dry == SCENARIOS["dry"]["yield_A"] * m.S_A)
    m.Const_B_dry = Constraint(expr=m.prod_U_B_dry == SCENARIOS["dry"]["yield_B"] * m.S_B)

    # Shortfall: short >= pre - prod (and short >= 0 via variable domain)
    m.Const_Shortfall_A_wet = Constraint(expr=m.short_A_wet >= m.pre_U_A - m.prod_U_A_wet)
    m.Const_Shortfall_B_wet = Constraint(expr=m.short_B_wet >= m.pre_U_B - m.prod_U_B_wet)

    m.Const_Shortfall_A_dry = Constraint(expr=m.short_A_dry >= m.pre_U_A - m.prod_U_A_dry)
    m.Const_Shortfall_B_dry = Constraint(expr=m.short_B_dry >= m.pre_U_B - m.prod_U_B_dry)

    # Min profit constraints per scenario
    m.Const_Min_Profit_wet = Constraint(expr=m.profit_wet >= MIN_PROFIT)
    m.Const_Min_Profit_dry = Constraint(expr=m.profit_dry >= MIN_PROFIT)
    return m

def solve_model(m, solver_name='scip', tee=False):
    """Builds, solves the model, and summarizes results."""
    # Try to locate solver binary
    if shutil.which(solver_name) is None:
        print(f"Solver '{solver_name}' not found on PATH.")
        # fallback to SCIP
        fallback = 'scip'
        if shutil.which(fallback) is None:
            raise RuntimeError(f"Neither '{solver_name}' nor '{fallback}' were found on PATH. Please install CBC or GLPK.")
        else:
            solver_name = fallback
            print(f"Falling back to solver '{fallback}'.")

    solver = SolverFactory(solver_name)
    result = solver.solve(m, tee=tee)
    return result

def main():
    # add argparser to select to solve scenario wet, dry or both (uniform)
    parser = argparse.ArgumentParser(description="Solve crop ambiguity scenarios")
    parser.add_argument("--scenario", choices=[
        "wet",
        "dry",
        "both",
        "maxmin",
        "minmax_regret",
        "multi_weighted",
    ], default="both", help="Scenario/strategy to solve")
    parser.add_argument("--solver", choices=["scip", "ipopt", "cbc"], default="scip", help="Solver to use")
    parser.add_argument("--tee", action="store_true", help="Display solver output")

    # Multi-objective controls
    parser.add_argument("--w-wet", dest="w_wet", type=float, default=0.5,
                        help="Weight on wet-scenario profit (for weighted objectives)")
    parser.add_argument("--w-dry", dest="w_dry", type=float, default=0.5,
                        help="Weight on dry-scenario profit (for weighted objectives)")
    parser.add_argument("--risk-lambda", dest="risk_lambda", type=float, default=0.0,
                        help="Penalty on imbalance |profit_wet - profit_dry| (>=0). Adds robustness.")
    args = parser.parse_args()

    m = build_model()
    # Define objective function based on selected scenario
    # Nota: the objective function will always minimize something, so we need to change signs accordingly
    if args.scenario == "wet":
        obj_fct = - m.profit_wet 
    elif args.scenario == "dry":
        obj_fct = - m.profit_dry 
    elif args.scenario == "both":
        # Maximize total expected-like sum across scenarios (uniform), i.e., minimize negative sum
        obj_fct = - (m.profit_wet + m.profit_dry)
    elif args.scenario == "maxmin":
        # Maximize the worst-case profit: introduce z <= profit_sce for all sce
        m.z = Var(domain=Reals)
        m.z_le_wet = Constraint(expr=m.z <= m.profit_wet)
        m.z_le_dry = Constraint(expr=m.z <= m.profit_dry)
        m.min_profit_cons = Constraint(expr=m.z >= MIN_PROFIT)
        obj_fct = - m.z 
    elif args.scenario == "minmax_regret":
        # Minimize the maximum regret. Need best profits per scenario as constants.
        print("Calculating best profits per scenario for regret computation...")
        m_best_wet = build_model()
        m_best_dry = build_model()
        m_best_wet.profit = Objective(expr=m_best_wet.profit_wet, sense=maximize)
        m_best_dry.profit = Objective(expr=m_best_dry.profit_dry, sense=maximize)
        solve_model(m_best_wet, solver_name=args.solver, tee=False)
        solve_model(m_best_dry, solver_name=args.solver, tee=False)
        best_wet = value(m_best_wet.profit_wet)
        best_dry = value(m_best_dry.profit_dry)
        print(f"Best profit in Wet scenario: {best_wet}")
        print(f"Best profit in Dry scenario: {best_dry}")
        print("Building regret constraints...")
        regret_wet = best_wet - m.profit_wet
        regret_dry = best_dry - m.profit_dry
        m.R = Var(domain=NonNegativeReals) # Regret
        m.R_ge_wet = Constraint(expr=m.R >= regret_wet)
        m.R_ge_dry = Constraint(expr=m.R >= regret_dry)
        obj_fct = m.R # I want to minimize Regret (no sign change needed)
    elif args.scenario == "multi_weighted":
        # Weighted-sum multi-objective with optional robustness penalty.
        # Objective: maximize w_wet*profit_wet + w_dry*profit_dry - risk_lambda*|profit_wet - profit_dry|
        # Convert to minimization and linearize absolute value via auxiliary variable D >= |pw - pd|
        w_wet = args.w_wet
        w_dry = args.w_dry
        lam = max(0.0, args.risk_lambda)

        # Optional imbalance variable only if needed
        if lam > 0:
            if not hasattr(m, "D"):
                m.D = Var(domain=NonNegativeReals)
                m.D_ge_wet_minus_dry = Constraint(expr=m.D >= m.profit_wet - m.profit_dry)
                m.D_ge_dry_minus_wet = Constraint(expr=m.D >= m.profit_dry - m.profit_wet)
            risk_term = lam * m.D
        else:
            risk_term = 0.0

        obj_fct = - (w_wet * m.profit_wet + w_dry * m.profit_dry) + risk_term

    # Set objective function
    m.J = Objective(expr= obj_fct, 
                    sense=minimize, 
                    doc="Minimize negative profit (i.e., maximize profit)")
    result = solve_model(m, solver_name=args.solver, tee=args.tee)
    summarize_model(m)


if __name__ == "__main__":
    main()