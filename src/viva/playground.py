# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

from viva.interpreter import generateFlowEngine
import pandas as pd


def static_simulation():
    sources = [
        """
    life: Paul, man, born 2005
    event: child_birth, in 2028
    flow: child_expense, -20k per year, upon child_birth, for 20 years
    flow: saving, 1k per year, until year 2030
    """,
        """
    event: child_birth, in 2027
    flow: child_expense, -20k monthly, upon child_birth, for 3 years
    """,
        """
    life: Paul, man, born 1928
    flow: insurance, 1m, upon Paul.death
    """,
    ]

    for source in sources:
        print(source)
        # With seed= explicitly: returns list of flows (one realization)
        engine = generateFlowEngine(source, start_year=2025, horizon_years=7)
        flows = engine.drawFlows(seed=42)
        print(
            pd.DataFrame(flows).to_string(
                index=False, formatters={"amount": lambda x: f"{x:,.0f}"}
            )
        )
        print("-" * 100)


def dynamic_simulation():
    sources = [
        """
        life: Simone, woman, born 1950 
        event: university_admission, in 2030, with probability 50%
        flow: savings, 1k annually, until Simone's death
        flow: university_expense, -10k annually, upon university_admission, for 4 years
        """,
    ]

    for source in sources:
        print(source)
        # No seed kwarg: returns the FlowEngine for controlled sampling
        engine = generateFlowEngine(source, start_year=2025, horizon_years=15)
        params = engine.params
        distrib = engine.param_distribs
        get_flows = engine.getFlows
        # draw_flows = engine.drawFlows  # available if you want one-shot draws inside the loop

        for k in range(10):
            print(f"Scenario {k}:")
            kwargs = {}
            for re in params:
                re_val = distrib[re](seed=k)
                print(f"{re}: {re_val}")
                kwargs[re] = re_val
            flows = get_flows(**kwargs)
            df = pd.DataFrame(flows)
            print(
                df.to_string(index=False, formatters={"amount": lambda x: f"{x:,.0f}"})
            )
            print("-" * 100)


if __name__ == "__main__":
    static_simulation()
    dynamic_simulation()
