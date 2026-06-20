# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

from datetime import date

from viva import parse, generateFlowEngine


def test_parse_examples():
    """Parser accepts all four example programs (MVP grammar)."""
    for name in (
        "example_seminal.viva",
        "retirement.viva",
        "family_education.viva",
        "small_business.viva",
        "full_syntax.viva",
    ):
        src = open(f"examples/{name}").read()
        prog = parse(src)
        assert len(prog.lives) >= 1
        # At least some flows
        assert len(prog.flows) >= 1


def test_generateFlowEngine_all_examples():
    """All example .viva programs must generate a FlowEngine without error and produce the expected flows.

    We use fixed seeds for reproducibility. We assert:
    - Correct output shape for every event.
    - Presence of key deterministic flows.
    - Correct year ranges / counts for flows whose triggers are deterministic
      (absolute years, 100% events, age events on the primary life, etc.).
    """
    cases = [
        {
            "name": "example_seminal.viva",
            "start": 2025,
            "horizon": 30,
            "seed": 42,
            "must_have": ["saving", "child_expense"],
            "checks": {
                "saving": {"min_years": 25, "start_year": 2025},
            },
        },
        {
            "name": "retirement.viva",
            "start": 2025,
            "horizon": 50,
            "seed": 42,
            "must_have": ["salary", "401k_withdrawal", "social_security"],
            "checks": {
                "salary": {"min_years": 15},  # until retirement cuts it off
            },
        },
        {
            "name": "family_education.viva",
            "start": 2025,
            "horizon": 45,
            "seed": 42,
            "must_have": [
                "baby_bonus",
                "k12_education",
                "college_tuition",
                "spouse_salary",
            ],
            "checks": {
                "baby_bonus": {"years": [2028]},
                "college_tuition": {"min_years": 4, "start_year": 2046},
                "spouse_salary": {"max_year": 2028},
            },
        },
        {
            "name": "small_business.viva",
            "start": 2025,
            "horizon": 30,
            "seed": 42,
            "must_have": ["product_sales", "loan_repayment", "equipment_purchase"],
            "checks": {
                "equipment_purchase": {"years": [2025]},
                "loan_repayment": {"min_years": 10, "start_year": 2025},
            },
        },
        {
            "name": "full_syntax.viva",
            "start": 2025,
            "horizon": 20,
            "seed": 42,
            "must_have": [
                "initial_capital",
                "one_time_setup",
                "founder_salary",
                "growth_phase",
                "office_rent",
            ],
            "checks": {
                "initial_capital": {"years": [2025]},
                "one_time_setup": {"years": [2025]},
                "growth_phase": {"years": [2026, 2027, 2028, 2029, 2030]},
                "founder_salary": {"min_years": 5, "start_year": 2025},
            },
        },
    ]

    for case in cases:
        src = open(f"examples/{case['name']}").read()
        engine = generateFlowEngine(
            src, start_year=case["start"], horizon_years=case["horizon"]
        )

        # Get flows using the engine
        events = engine.drawFlows(seed=case["seed"])

        # Shape and basic validity
        assert isinstance(events, list)
        assert len(events) > 0
        for e in events:
            assert isinstance(e["date"], date)
            assert e["date"].month == 1 and e["date"].day == 1
            assert isinstance(e["name"], str) and e["name"]
            assert isinstance(e["amount"], float)
            assert e["currency"] == "USD"

        names = {e["name"] for e in events}
        for req in case["must_have"]:
            assert req in names, f"{case['name']}: expected flow {req} not present"

        # Detailed checks
        by_name = {}
        for e in events:
            by_name.setdefault(e["name"], []).append(e["date"].year)

        for fname, chk in case.get("checks", {}).items():
            if fname not in by_name:
                continue
            years = sorted(set(by_name[fname]))
            if "years" in chk:
                assert years == chk["years"], f"{case['name']} {fname} years mismatch"
            if "start_year" in chk:
                assert years[0] == chk["start_year"], f"{case['name']} {fname} start"
            if "max_year" in chk:
                assert years[-1] <= chk["max_year"]
            if "min_years" in chk:
                assert len(years) >= chk["min_years"]
