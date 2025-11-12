 Source Meinolf Sellmann [source here](https://www.linkedin.com/pulse/ambiguity-meinolf-sellmann-nefje/?trackingId=tRT8CHaWTHyHQXCBLqrs%2Bg%3D%3D)
 
# Problem statement

Decision Science must provide answers even if we face problems that are not fully quantified. Can you handle ambiguity?

George manages **100 acres of land**. He faces an annual dilemma that is now compounded by climate volatility: He must commit to his planting and pre-selling contracts without knowing the weather. The coming summer could be severely wet or agonizingly dry, and George must choose a plan that secures the financial well-being of his company.

He plans to grow two crops. 

## Fixed cost per crop type

| Crop | Characteristic | Fixed Cost (per acre) |
|---|---:|---:|
| Crop A | Optimized for wet weather | $150 |
| Crop B | Optimized for dry weather | $100 |


## Pre-Sale Contracts & Penalties

The Pre-Sale Contract Parameters

George can pre-sell units of either crop before planting, guaranteeing a stable income stream at a price of **$3.90** per unit for both Crop A and Crop B, provided he can deliver on his promises.

However, if George fails to deliver the contracted amount, he faces penalties:

| Item | Crop A | Crop B |
|---|---:|---:|
| Pre-sale price (per unit) | $3.90 | $3.90 |
| Penalty for shortfall (per unit) | $1.50 | $1.45 |

All amounts in USD.

## Scenario 1: The Heavy Rains (Wet Summer)

This scenario strongly favors Crop A.

| Crop | Variable cost (per acre) | Yield (units per acre) | Sport Market Price (per unit) |
|---|---:|---:| ---:|
| Crop A | $50 | 800 | $2.50 (high yield nationwide drives prices down) |
| Crop B | $150 | 150 | $5.00 (low national supply drives prices up) |

## Scenario 2: The Extended Drought (Dry Summer)

This scenario requires expensive inputs for Crop A but is ideal for Crop B.

| Crop | Variable cost (per acre) | Yield (units per acre) | Sport Market Price (per unit) |
|---|---:|---:| ---:|
| Crop A | $200 | 300 | $4.50 (low national supply drives prices up) |
| Crop B | $40 | 600 | $3.00 (high yield nationwide drives prices down) |

## The Decision Challenge

George must determine his plan for the 100 acres:

    1. Acreage Allocation: How many acres of Crop A and Crop B should be planted? Fractions of acres are allowed.
    2. Contract Commitments: How many units of Crop A and Crop B should be pre-sold?

Finally, George needs to make at least **$50,000** to cover the other fixed costs of his business. What would you recommend that George should do given that we have no probabilities for either scenario? 

# Solution

The solution is found in the `ambiguity-crops.py` file.
Solution and explainations can be found in the [puzzle](https://www.linkedin.com/pulse/ambiguity-meinolf-sellmann-nefje/?trackingId=wptcX%2FTjQb6%2FNZdFvFQgug%3D%3D).

## Multi-objective strategies

This repo includes several decision strategies you can try from the command line:

- wet, dry: optimize for a single scenario.
- both: maximize total profit across both scenarios (uniform weights).
- maxmin: maximize the worst-case profit.
- minmax_regret: minimize maximum regret relative to the per-scenario ideal solutions.
- multi_weighted: weighted-sum across scenarios with optional robustness penalty.
- multi_tchebycheff: minimize the maximum normalized shortfall from each scenario's "excellent" level (Chebyshev scalarization).

Key flags (PowerShell examples):

```powershell
# Weighted-sum: maximize 0.7*wet + 0.3*dry
python .\ambiguity-crops\ambiguity-crops.py --scenario multi_weighted --w-wet 0.7 --w-dry 0.3

# Weighted-sum with robustness: penalize imbalance |profit_wet - profit_dry|
python .\ambiguity-crops\ambiguity-crops.py --scenario multi_weighted --w-wet 0.5 --w-dry 0.5 --risk-lambda 0.1

# Worst-case profit
python .\ambiguity-crops\ambiguity-crops.py --scenario maxmin

# Minimax regret
python .\ambiguity-crops\ambiguity-crops.py --scenario minmax_regret

# Chebyshev multi-objective (balance normalized shortfalls)
python .\ambiguity-crops\ambiguity-crops.py --scenario multi_tchebycheff --alpha-wet 1.0 --alpha-dry 1.0 --rho 0.001
```

Notes:
- The model enforces a base minimum profit of $50,000 in each scenario by default; the epsilon constraints add further bounds if provided.
- The imbalance penalty is linearized internally to keep the model linear/MILP-friendly.
- The Chebyshev option computes "excellent" and "okay" levels via auxiliary solves, then minimizes the maximum normalized shortfall t with a tiny augmentation rho*(sw+sd) for tie-breaking; use alpha weights to emphasize one scenario.
- You need a MILP/NLP solver installed (e.g., CBC, SCIP, or IPOPT) and on your PATH.

### Tchebycheff (Chebyshev) strategy

The Chebyshev scalarization addresses a limitation of linear weighted sums: they cannot reverse trades when one scenario is already excellent and the other is poor. This strategy:

1. Computes an "excellent" level for each scenario by maximizing that scenario's profit alone.
2. Observes the other scenario's profit at that solution and defines an "okay" level as max(observed, 50,000).
3. Normalizes shortfalls from excellent to okay for each scenario and minimizes the maximum weighted shortfall.

Control parameters:
- --alpha-wet, --alpha-dry: weights on wet/dry normalized shortfalls (default 1.0 each).
- --rho: small positive augmentation on the sum of shortfalls to break ties (default 0.001).

Example runs:

```powershell
# Balanced emphasis on both scenarios
python .\ambiguity-crops\ambiguity-crops.py --scenario multi_tchebycheff --alpha-wet 1.0 --alpha-dry 1.0 --rho 0.001

# Emphasize closing the wet shortfall faster
python .\ambiguity-crops\ambiguity-crops.py --scenario multi_tchebycheff --alpha-wet 2.0 --alpha-dry 1.0 --rho 0.001
```

#### How does it work in the objective function.

To set an example, the normalized shortfall for the wet scenario is as follows for the wet scenario:

$S_i >= \frac{Prod_{i}^{*} - Profit_{i}}{Prod_{i}^{*}-Prod_{{i}_{min}}}$ (for $i = wet, dry$)

NB: *see lines 297 and 298 in code to see the implementation*.

The model will try to **minimize** $S_w$ and $S_d$ variables through the variable $t$.

The variable $t$ is the *maximum aggregator* (as we are minimizing).

$t >= \alpha_{w} * S_w$
$t >= \alpha_{d} * S_d$

The objective function **minimizes** $t$:

$J = t + \rho * (S_w + S_d)$

#### Discussion on using a weighted sum vs Tchebycheff with the normalized shortfall
- Weighted sums assume constant marginal rates of substitution between objectives, so they can’t reverse trades dynamically.
- **Chebyshev** focuses on the worst normalized shortfall—when one side is weak, it gets priority; when it improves, focus shifts. This matches your “we’d trade X for Y when wet is great, but reverse when dry is great” behavior