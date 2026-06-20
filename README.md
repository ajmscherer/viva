# Viva

**Viva** is a human-friendly, English-like domain-specific language for defining and simulating streams of future cash flows (salaries, expenses, taxes, savings, insurance, gifts, and other money movements tied to life events and probabilities).

## Core Idea

You describe *lives*, *events*, and *flows* in readable syntax. Viva is then interpreted into a Python function that produces stochastic yearly projections.

### Example

```viva
life: Paul, man, born 2005
event: child_birth, in the next 10 years, uniform annual probability 80%
flow: child_expense, -20k, upon child_birth, for 20 years
flow: saving, 1k per month
flow: insurance, 1m, upon Paul.death
flow: allowance, 5k annually, from Paul's birth
```

Newer syntax also supports:
- Possessive: `Paul's death`, `Baby's birth`
- Birth references: `upon X.birth`, `N years after X's birth`, or direct `event: foo, X's birth`
- Compact ranges: `from year 2027 to year 2029` or `from year 2027 until year 2029`
- Relative years: `from year 3` (when <100, treated as start_year + (N-1))
- Big numbers: `3 million`, `4.2 thousand`, `2 trillion`, `1B`, `5m` (case-insensitive)
- Late births: a life born after `start_year` can still die randomly (sampling starts at birth year)

The interpreter turns this into a Python function that returns a flat list of dated cash flow events: `list[dict['date': date (Jan 1 of year in MVP), 'name': str, 'amount': float, 'currency': 'USD']]`. See `genesis.txt` and `roadmap.md` for the exact current model + deferred refinements (full dates, multicurrency, per-period granularity).

## Goals

- Design a clean, expressive syntax close to natural English.
- Build a parser + semantic engine that understands lives, events, and time-dependent flows.
- Generate self-contained Python simulation functions (no external dependencies at runtime).
- Support realistic Monte-Carlo style projections with stochastic events.
- Keep everything local (no internet calls in the core interpreter — computation is private by design).

## Project Structure

- `genesis.txt` — Origin, vision, and ownership statement.
- `roadmap.md` — Detailed development plan, phases, and current status.
- `AI - transcripts/` — Conversation logs and research notes.
- `src/viva/`:
  - `grammars/viva.lark` — The Lark grammar definition (source of truth for the language syntax; supports birth/death refs with `.` and `'s`, compact from-to/until, relative years, big number words).
  - `life.py` — Life and Table objects, mortality tables (SSA_2023, 2017 CSO), `get_available_tables()`, `generate_random_death_year` (respects birth year even if after `start_year`).
  - `nodes.py` — Backend-independent AST (`Program`, `LifeDecl` with `birth_year`, modifiers with `attr` for death/birth).
  - `parsers/base.py` — Abstract `Parser` + `ParseTree` protocol.
  - `parsers/lark_parser.py` — `LarkParser` (only place that imports the `lark` library). The grammar can be passed to its constructor. Includes `_convert_str2amount` and validation.
  - `interpreter.py` — Simulation logic (generateFlowEngine() returns FlowEngine with params, param_distribs, getFlows, drawParamRealization, drawFlows).
  - `parser.py` — Public facade with `parse()`, `get_parse_tree()`, `set_default_parser()`, etc.
- `tests/`, `examples/`, `documentation/`, `playground.py` (demo), and the Viva interpreter.

## Current Status

MVP interpreter is functional:

- Lives with birth year + optional mortality table (SSA 2023, 2017 CSO).
- Events with time windows (absolute/relative years, at age, after event/life birth/death) and probabilities.
- Flows with amounts (including k/m/thousand/million/billion/trillion words), periods ("annually", "per year", etc.), and modifiers (upon, from/to/until year or life.death/birth, for years/life, after years, starting at age).
- Compact syntax: `from year 2027 to year 2029`, `N years after X's birth`.
- Relative small years (<100): `from year 3` with `start_year=2026` → 2028.
- Death sampling respects birth year (late-born lives still die randomly per their q_x).
- Deterministic + stochastic (Monte-Carlo) via `generateFlowEngine(source, ...)` (returns FlowEngine with .params, .param_distribs, .getFlows, .drawParamRealization, .drawFlows for reproducible statistical checks).
- Output: flat list of `{'date': date(year,1,1), 'name', 'amount', 'currency':'USD'}`.

The parser uses an abstract `Parser` interface (see `viva.parsers.base`) with a `LarkParser` implementation. This allows swapping the backend (e.g. to a future pure-Python implementation) without changing the rest of the code or the public API.

See [roadmap.md](roadmap.md) for the full phased plan, implemented items, and next steps.

## Ownership

100% owned by Alexandre Scherer. This repository supports collaborative development under the terms described in `genesis.txt`.

## License

Viva can be used under two different licensing options depending on your needs:

- Under the **MIT License**, Viva is available for personal projects, learning, and any deterministic flows (where no probabilistic or uncertain elements are used).

- For models that include probabilistic features (such as uncertain events or life outcomes with probability below 100%), the **Viva Pro** commercial license applies after a 30-day evaluation period.

Support, training, and consulting services are available separately.

For the full details:
- [LICENSE](LICENSE) – MIT License
- [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md) – Viva Pro terms

**Quick summary**: Deterministic use is free under MIT. Probabilistic features require Viva Pro after 30 days of evaluation. Support is offered separately.

License files (`LICENSE`, `COMMERCIAL-LICENSE.md`, `NOTICE`, and `LICENSE_HEADER.txt`) live at the root of the repository (standard practice for visibility).

## Installation

### For end users and downstream projects (e.g. finproj)

The easiest way is to install directly from the public GitHub repository:

```bash
pip install git+https://github.com/ajmscherer/viva.git
```

This gives you a standalone, versioned package without needing to clone the repo yourself.

You can also pin a specific commit or tag if needed:

```bash
pip install git+https://github.com/ajmscherer/viva.git@<commit-or-tag>
```

### For developers (editable install)

```bash
git clone https://github.com/ajmscherer/viva.git
cd viva
pip install -e .
```

### Building a distributable package yourself

If you want a `.whl` or `.tar.gz` to distribute internally:

```bash
pip install build
python -m build
```

This produces files in `dist/`. The resulting wheel is completely standalone (no git dependency at runtime).

### Using Viva from other projects (loose integration)

Viva is designed to remain fully independent. In a project like finproj you can integrate it loosely:

```python
try:
    from viva import generateFlowEngine
    HAS_VIVA = True
except ImportError:
    HAS_VIVA = False

if HAS_VIVA:
    engine = generateFlowEngine(viva_source)
    flows = engine.drawFlows(seed=...)   # or use .getFlows() for more control
else:
    # fallback to your existing deterministic cash-flow logic
    flows = legacy_generate_flows(...)
```

Only deterministic models are covered by the free MIT license. Probabilistic usage requires the separate "Viva Pro" commercial license (30-day evaluation).

See the [FlowEngine](#flowengine) section below for the full recommended API.

## Usage

```python
from viva import generateFlowEngine

# Deterministic example - returns a FlowEngine
engine_d = generateFlowEngine("flow: salary, 5000 per year, for 12 years")
flows = engine_d.getFlows()   # invoke to get the list of flows

# For full probabilistic models (requires Viva Pro license after evaluation)
engine_p = generateFlowEngine("""life: Julian, person, born 1980
event: retirement, at age 65
flow: pension, 3000, upon retirement""")
flows = engine_p.drawFlows(seed=123)
```

## FlowEngine

`generateFlowEngine(source)` is the primary way to use Viva. The `source` argument is a string containing your Viva DSL program. It returns a `FlowEngine` — an object that gives you explicit control over the random parameters and the resulting cash flows.

This "factored" design is useful for:
- Purely deterministic projections
- Reproducible Monte-Carlo runs
- Custom statistical analysis or sensitivity testing

### Creating a FlowEngine

The first argument to `generateFlowEngine()` is called `source`. It is a string containing your Viva program written in the DSL.

You can pass the source either as a variable or directly as a string literal:

```python
# As a variable
source = """
life: Julian, person, born 1980
event: retirement, at age 65
flow: pension, 3000, upon retirement
"""

engine = generateFlowEngine(
    source,
    start_year=2025,     # reference year for relative dates (e.g. "in 3 years")
    horizon_years=40     # length of the projection
)

# Or inline (common for short programs)
engine = generateFlowEngine("flow: salary, 5000 per year, for 12 years")
```

### Properties and Members

| Member                    | Description |
|---------------------------|-------------|
| `.params`                 | `dict[str, type]`<br>Names and declared types of all random variables (death years are always `int`; stochastic events are usually `bool` or `int \| None`). |
| `.param_distribs`         | `dict[str, Callable]`<br>Sampling functions. Call `distrib(seed=...)` to get a reproducible draw for that parameter. |
| `.getFlows(realizations)` | The core method. Pass a dictionary (or use `**kwargs`) containing values for the parameters in `.params`. Returns the list of dated cash flows.<br>Unknown keys or wrong types raise `ValueError` / `TypeError`. |
| `.drawParamRealization(seed=None)` | Draws one complete set of realizations for all parameters. |
| `.drawFlows(seed=None)`   | Convenience method: draws realizations internally then calls `getFlows`. Ideal for quick one-off runs. |

All members are **read-only**.

### How to Use Them

**Deterministic models** (no `Life` or `Event` with probability < 100%):

```python
flows = engine.getFlows()      # no arguments required
# or explicitly:
flows = engine.getFlows({})
```

**Quick probabilistic run**:

```python
flows = engine.drawFlows(seed=42)
```

**Controlled / statistical sampling** (powerful pattern):

```python
params = engine.params
distribs = engine.param_distribs
get_flows = engine.getFlows

results = []
for i in range(10000):
    realizations = {name: distribs[name](seed=i) for name in params}
    flows = get_flows(**realizations)
    # collect statistics, write to dataframe, etc.
    results.append(analyze(flows))
```

You can also pass realizations as a dict:

```python
flows = get_flows(realizations_dict)
```

See `src/viva/playground.py` for a complete working example of the controlled sampling pattern.

## Getting Started

Explore the examples in the `examples/` directory, or read `documentation/examples.md` for a rendered view of sample programs and their output.

See `genesis.txt` and `roadmap.md` for background and development history.

---

Viva is dual-licensed: MIT License (deterministic use) and Viva Pro commercial license (probabilistic features).  
Copyright © 2026 Alexandre Scherer. All rights reserved.