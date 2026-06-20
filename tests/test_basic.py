# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

from viva import (
    parse,
    get_parse_tree,
    generateFlowEngine,
    set_default_parser,
    get_default_parser,
    Parser,
    ParseTree,
    LarkParser,
    create_life,
)

from datetime import date
from viva.parsers.base import Parser as BaseParser


def test_version():
    """Check that version is defined."""
    from viva import __version__

    assert __version__ == "0.1.0"


def test_generateFlowEngine_output_shape_and_currency():
    """generateFlowEngine + drawFlows returns the exact required flat list with Jan-1 dates + currency=USD."""
    src = open("examples/example_seminal.viva").read()
    engine = generateFlowEngine(src, start_year=2025, horizon_years=5)
    events = engine.drawFlows(seed=99)
    assert isinstance(events, list)
    assert len(events) > 0
    for e in events:
        assert isinstance(e["date"], date)
        assert e["date"].month == 1 and e["date"].day == 1
        assert isinstance(e["name"], str)
        assert isinstance(e["amount"], float)
        assert e["currency"] == "USD"


def test_generateFlowEngine_deterministic_with_seed():
    """Same seed produces identical output (reproducible)."""
    src = open("examples/example_seminal.viva").read()
    engine = generateFlowEngine(src, start_year=2025, horizon_years=10)
    a = engine.drawFlows(seed=42)
    b = engine.drawFlows(seed=42)
    assert a == b
    # Different seed likely different (but not asserted, just that mechanism exists)
    assert len(a) == len(b)


def test_parser_abstraction_interface():
    """The abstract Parser interface and LarkParser implementation are available and usable."""
    # Type check / protocol
    p = LarkParser()
    assert isinstance(p, BaseParser)
    assert isinstance(p, Parser)

    src = open("examples/example_seminal.viva").read()

    # High-level functions still work
    prog = parse(src)
    assert len(prog.lives) >= 1

    tree = get_parse_tree(src)
    assert isinstance(tree, ParseTree) or hasattr(tree, "pretty")
    pretty = tree.pretty()
    assert "program" in pretty.lower() or "declaration" in pretty.lower()


def test_set_default_parser():
    """Users can globally swap the parser implementation."""
    original = get_default_parser()
    try:
        # Create a second instance (same backend, but demonstrates the API)
        new_parser = LarkParser()
        set_default_parser(new_parser)

        assert get_default_parser() is new_parser

        # Functionality is preserved after swap
        src = open("examples/retirement.viva").read()
        engine = generateFlowEngine(src, start_year=2025, horizon_years=3)
        events = engine.drawFlows(seed=7)
        assert len(events) > 0
        assert all(e["currency"] == "USD" for e in events)
    finally:
        # Restore original for other tests
        set_default_parser(original)


def test_new_deterministic_flow_modifiers():
    """Parser supports the new deterministic range syntax elements:
    - from year YYYY
    - after N years
    - to year YYYY / until year YYYY
    """
    cases = [
        # from year + for
        (
            "flow: tuition, -50k per year, from year 2027, for 4 years",
            [{"kind": "from_year", "year": 2027}, {"kind": "for", "years": 4}],
        ),
        # after N years + for
        (
            "flow: phase2, 10k per year, after 4 years, for 5 years",
            [{"kind": "after_years", "years": 4}, {"kind": "for", "years": 5}],
        ),
        # from year + until year
        (
            "flow: tuition, -50k per year, from year 2028, until year 2032",
            [
                {"kind": "from_year", "year": 2028},
                {"kind": "until", "target": 2032, "is_year": True},
            ],
        ),
        # from year + to year
        (
            "flow: tuition, -50k per year, from year 2028, to year 2032",
            [
                {"kind": "from_year", "year": 2028},
                {"kind": "until", "target": 2032, "is_year": True},
            ],
        ),
        # until year without from (absolute end)
        (
            "flow: savings, -5k per year, until year 2030",
            [{"kind": "until", "target": 2030, "is_year": True}],
        ),
    ]

    for src, expected_mods in cases:
        prog = parse(src)
        assert len(prog.flows) == 1, f"Failed for: {src}"
        assert prog.flows[0].modifiers == expected_mods, (
            f"Modifiers mismatch for: {src}"
        )

    # End-to-end: generateFlowEngine should produce the correct years
    src = "flow: tuition, -50k per year, from year 2027, for 4 years"
    engine = generateFlowEngine(src, start_year=2025, horizon_years=10)
    events = engine.drawFlows()
    years = [e["date"].year for e in events if e["name"] == "tuition"]
    assert years == [2027, 2028, 2029, 2030]

    # after + for simulation
    src = "flow: phase, 10k per year, after 3 years, for 4 years"
    engine = generateFlowEngine(src, start_year=2025, horizon_years=15)
    events = engine.drawFlows()
    years = [e["date"].year for e in events if e["name"] == "phase"]
    assert years == [2028, 2029, 2030, 2031]


def test_no_per_with_duration_is_syntax_error():
    """Flows with duration ('for', etc.) but no 'per year/month' should be syntax error (per user request)."""
    src = """
    event: child_birth, in 2027
    flow: child_expense, -20k, upon child_birth, for 3 years
    """
    try:
        parse(src)
        assert False, "Should have raised ValueError for missing per"
    except ValueError as e:
        assert "per year" in str(e) or "per month" in str(e)


def test_playground_source1_example():
    """Test corresponding to playground.py source2 (with required 'per year')."""
    src = """
    event: child_birth, in 2027
    flow: child_expense, -20k per year, upon child_birth, for 3 years
    """
    engine = generateFlowEngine(src, start_year=2025, horizon_years=7)
    events = engine.drawFlows(seed=42)
    years = [e["date"].year for e in events if e["name"] == "child_expense"]
    names = set([e["name"] for e in events])
    assert years == [2027, 2028, 2029]
    assert all(e["amount"] == -20000.0 for e in events if e["name"] == "child_expense")
    assert names == {"child_expense"}


def test_playground_source2_example():
    """Test corresponding to playground.py source2 (with required 'monbthly')."""
    src = """
    event: saintglinglin, in 2028
    flow: interest_payment, -1m monthly, upon saintglinglin, for 3 years
    """
    engine = generateFlowEngine(src, start_year=2025, horizon_years=7)
    events = engine.drawFlows(seed=42)
    years = [e["date"].year for e in events if e["name"] == "interest_payment"]
    names = set([e["name"] for e in events])
    assert years == [2028, 2029, 2030]
    assert all(
        e["amount"] == -12_000_000.0 for e in events if e["name"] == "interest_payment"
    )
    assert names == {"interest_payment"}


def _monte_carlo_validation(
    life,
    start_year,
    N=10000,
    qx_tol=0.01,
    surv_tol=0.015,
    mean_tol=1.0,
    ages_to_check=None,
    print_results=True,
):
    """Helper for Monte Carlo validation of death generation against table.

    - Checks empirical q_x (conditional death prob) vs table q_x
    - Checks empirical survival to age vs theoretical product (1-q)
    - Checks mean death age vs table life expectancy at start age
    - Configurable tolerances and N

    Sampling now performed via the FlowEngine interface (params/param_distribs)
    for statistical validation of the factored generateFlowEngine.
    """
    import random

    if ages_to_check is None:
        start_age = max(0, start_year - life.birth_year)
        ages_to_check = list(range(start_age, min(start_age + 30, 110), 5))

    rng = random.Random(42)

    # Use the new generateFlowEngine API to obtain the param_distribs for statistical checks.
    # Build a minimal Viva source declaring the life (with mortality if non-default).
    # This exercises generateFlowEngine -> params/param_distribs for the death RV.
    table_name = life.mortality_table.name if hasattr(life, "mortality_table") else None
    # Reconstruct a source that will cause generateFlowEngine to attach the same table.
    # If explicit non-default table, include mortality= clause (supported by grammar).
    if table_name and table_name not in (
        None,
        "SSA_2023",
        "SSA_2023_male",
        "SSA_2023_female",
    ):
        src = (
            f"life: {life.name}, person, born {life.birth_year}, mortality={table_name}"
        )
    else:
        g = getattr(life, "gender", "male")
        src = f"life: {life.name}, {g}, born {life.birth_year}"

    engine = generateFlowEngine(src, start_year=start_year, horizon_years=120)
    death_rv = f"{life.name}_death"
    assert death_rv in engine.params, (
        f"Expected death RV {death_rv} in FlowEngine params"
    )
    distrib_death = engine.param_distribs[death_rv]

    death_years = []
    for i in range(N):
        seed = rng.randint(0, 2**32 - 1)
        dy = distrib_death(seed=seed)
        death_years.append(dy)

    death_ages = [dy - life.birth_year for dy in death_years]
    start_age = max(0, start_year - life.birth_year)

    qx_results = []
    surv_results = []
    max_qx_diff = 0.0
    max_surv_diff = 0.0

    def theoretical_survival_to(age):
        if age <= start_age:
            return 1.0
        surv = 1.0
        for a in range(start_age, age):
            surv *= 1 - life.mortality_table.death_probability(a)
        return surv

    for age in ages_to_check:
        year_of_age = life.birth_year + age
        if year_of_age < start_year:
            continue

        reached = sum(1 for da in death_ages if da >= age)
        died = sum(1 for da in death_ages if da == age)

        if reached >= max(50, N // 200):
            emp_q = died / reached
            table_q = life.mortality_table.death_probability(age)
            qx_diff = abs(emp_q - table_q)
            max_qx_diff = max(max_qx_diff, qx_diff)
            qx_results.append((age, table_q, emp_q, qx_diff))

            emp_surv = reached / N
            theo_surv = theoretical_survival_to(age)
            surv_diff = abs(emp_surv - theo_surv)
            max_surv_diff = max(max_surv_diff, surv_diff)
            surv_results.append((age, theo_surv, emp_surv, surv_diff))

    mean_death_age = sum(death_ages) / len(death_ages)
    table_e0 = life.mortality_table.life_expectancy(start_age)
    mean_diff = abs(mean_death_age - (start_age + table_e0))

    if print_results:
        print(f"\nMC validation for {life.name} (N={N}, start_age={start_age}):")
        print(
            f"Mean death age: {mean_death_age:.2f}  | Table e_x: {start_age + table_e0:.2f}  | diff: {mean_diff:.2f}"
        )
        print("q_x comparison:")
        print(f"{'Age':>4} | {'Table':>8} | {'Emp':>8} | {'Diff':>8}")
        for age, tq, eq, d in qx_results:
            print(f"{age:4d} | {tq:8.5f} | {eq:8.5f} | {d:8.5f}")
        print("Survival (to age) comparison:")
        for age, ts, es, d in surv_results:
            print(f"{age:4d} | {ts:8.5f} | {es:8.5f} | {d:8.5f}")

    assert max_qx_diff < qx_tol, f"qx diff too large: {max_qx_diff}"
    assert max_surv_diff < surv_tol, f"surv diff too large: {max_surv_diff}"
    assert mean_diff < mean_tol, f"mean lifetime diff too large: {mean_diff}"


def test_late_birth_death_sampling():
    """A life born after start_year must still die after its birth year.

    This turns the previous manual verification loop into a proper unit test.
    """
    life = create_life("LateBorn", "male", 2030, "SSA_2023_male")
    N = 200
    for seed in range(N):
        # This mirrors exactly how the interpreter adjusts death sampling
        # when birth_year > start_year.
        death_start = max(2025, life.birth_year)
        dy = life.generate_random_death_year(start_year=death_start, seed=seed)
        assert dy >= life.birth_year, f"death year {dy} before birth {life.birth_year}"
        assert dy >= 2025


def test_monte_carlo_death_probability_consistency():
    """Comprehensive MC tests (N=10000) for q_x, survival, mean lifetime.
    Covers full lifetime and multiple tables. Uses generateFlowEngine.
    """
    N = 20_000

    # SSA Male - full lifetime from birth
    life_m = create_life("MC_Male_SSA", "male", 1950, "SSA_2023_male")
    _monte_carlo_validation(
        life_m,
        start_year=life_m.birth_year,
        N=N,
        # qx_tol=0.06,
        # surv_tol=0.025,
        # mean_tol=3.0,
        ages_to_check=list(range(0, 101, 10)) + [105],
    )

    # SSA Female
    life_f = create_life("MC_Female_SSA", "female", 1950, "SSA_2023_female")
    _monte_carlo_validation(
        life_f,
        start_year=life_f.birth_year,
        N=N,
        qx_tol=0.06,
        surv_tol=0.025,
        # mean_tol=3.0,
        ages_to_check=list(range(0, 101, 10)) + [105],
    )

    # 2017 CSO Male (illustrative)
    life_cso = create_life("MC_Male_CSO", "male", 1950, "2017_CSO_male_composite")
    _monte_carlo_validation(
        life_cso,
        start_year=life_cso.birth_year,
        N=N,
        # qx_tol=0.04,
        # surv_tol=0.025,
        # mean_tol=20.0,
        ages_to_check=list(range(20, 101, 10)),
    )

    # Late birth scenario (birth after simulation start_year).
    # The interpreter starts mortality sampling at the birth year in this case.
    # We verify that deaths are still statistically consistent with the table's qx
    # (conditional on survival to birth).
    life_late = create_life("MC_LateBorn", "male", 2030, "SSA_2023_male")
    _monte_carlo_validation(
        life_late,
        start_year=life_late.birth_year,
        N=N,
        # qx_tol=0.06,
        # surv_tol=0.025,
        # mean_tol=3.0,
        ages_to_check=list(range(0, 101, 10)) + [105],
    )
