# Viva Project Roadmap

**Status:** Initial draft (June 3, 2026)  
**Origin:** Derived directly from `genesis.txt`  
**Maintainer:** Alexandre Scherer (owner) with Grok 4.3 (assistant)  
**Repository:** https://github.com/ajmscherer/viva (public) — Note: This is a fresh history repository. The full original history is in the private https://github.com/ajmscherer/viva_original .

---

## 1. Origin and Introduction

This roadmap originates from the `genesis.txt` document created on June 3, 2026.


**How we will proceed:**
- We will use this `roadmap.md` as the living planning document.
- It will be amended from time to time as the project evolves.
- Primary activities: iterative definition of syntax + semantics, building the interpreter, testing, and exploration of LLM assistance.
- All source code, tests, documentation, and related artifacts will live in this repository.
- Communication will happen via updates to files in this repo (e.g., this roadmap, `genesis.txt`, new source files, notes).

---

## 2. Project Vision and Background

**Viva** is a human-friendly, English-like language designed to help people define and model **streams of future money flows**. These include:

- Salaries and income
- Expenses (regular or event-driven)
- Gifts
- Taxes
- Contributions to savings
- Withdrawals / withholdings from savings
- Insurance payouts
- And many other cash flow events over a lifetime or multi-year horizon

**Core Objects in the Language:**
- **money flow** (positive or negative amounts over time)
- **life event** (stochastic or deterministic triggers)
- **living creatures (lives)** (people or entities with attributes like birth date, death, etc.)

**Example Viva Code** (from `genesis.txt`):

```viva
life: Paul, man, born 2005
event: child_birth, in the next 10 years, uniform annual probability 80%
flow: child_expense, -20k, upon child_birth, for 20 years
flow: saving, 1k per month
flow: insurance, 1m, upon Paul.death
```

**Interpreter Output Requirement (MVP simplified model):**

The Viva code should be interpreted into a **Python function** (via `generateFlowEngine()`) that returns a FlowEngine with a factored control interface (for MC).

list[dict['date': date, 'name': str, 'amount': float, 'currency': str]]

- 'date': a Python `date` object (from datetime.date) for when the flow occurs. **MVP simplification** (to reach a working end-to-end solution faster and conserve tokens): dates are year-granular only. The value is always January 1 of the year: `date(year, 1, 1)`. In Viva source, birth dates and absolute time windows use bare years (e.g. `born 2005`, `in 2028`). Full flexible date formats, day/month precision, natural language dates, and ambiguity warnings are deferred (see Deferred Requirements below).
- 'name': the flow name (e.g. 'child_expense', 'saving', 'insurance')
- 'amount': the float amount of the flow (positive for inflows, negative for outflows)
- 'currency': always `'USD'` in the MVP. Multicurrency support (variable currency per flow/event, and the field reflecting it) is deferred.

"per month" (and similar recurring periods) in the MVP: the interpreter emits **one entry per year** dated January 1 (year-level granularity). Full per-period atomic entries (e.g. 12 monthly entries with proper dates) is deferred.

This flat event-list model (instead of yearly buckets) avoids the need to prorate monthly or periodic flows. The model will be refined later while keeping the same top-level list-of-dicts shape.

The simulation should properly handle:
- Time-dependent flows
- Event-triggered flows (with probabilities)
- Lifespan events (birth, death, etc.)
- Recurring flows (per month, per year, etc.)
- Stochastic elements for realistic Monte-Carlo style projections

---

## 3. Project Goals

1. Design a clean, extensible, readable syntax for Viva that feels natural to humans (close to English).
2. Build a parser that constructs a tree / AST (abstract syntax tree / "tree graph") from Viva source.
3. Implement semantic actions / analysis on the tree to validate and understand the program (lives, events, flows, dependencies, time scopes).
4. Develop a code generator / interpreter that emits a self-contained Python function matching the required output format.
5. Create a robust testing framework (unit tests for parser, semantics, interpreter; integration tests with example scenarios; property-based or Monte-Carlo validation).
6. Iteratively refine and fine-tune the syntax based on real-world usage and expressiveness needs.
7. Explore complementary use of small, local, open-source LLM models:
   - (a) As a checker / corrector for user-written Viva code.
   - (b) To translate plain English descriptions into valid Viva programs (e.g., "Paul may have a child in the next 10 years with 80% probability...").
8. Produce high-quality documentation, examples, and eventually a user-friendly interface or CLI for the Viva interpreter.

Important considerations:
- The code should run on a local computer without any internet connection or external services. We may do temporary exception to this rule to use an external service for a limited time to develop the project.
- The privacy promise should be guaranteed by a test code that is public and demonstrates that the code operates without interactions with external services or computers.

---

## 4. High-Level Architecture

- **Frontend / Parser**: Grammar definition + parser (recommended: Python ecosystem tools such as Lark, PLY, or ANTLR with Python target for ease).
- **Semantic Layer**: Symbol table for lives, event registry, flow definitions, time/dependency graph.
- **Interpreter / Backend**: Execution model that resolves events stochastically and emits a flat list of dated cash flow events (each with date, name, and amount).
- **Output**: Pure Python function (no external Viva runtime required at runtime of the generated function).
- **Optional LLM Layer**: Local model (e.g., via llama.cpp, Ollama, or Hugging Face transformers) for code assistance.

The core deliverable is a Python package that can:
- Parse Viva source → AST
- Interpret AST → Python callable

---

## 5. Phased Development Roadmap

### Phase 0: Setup & Foundations (Current)
- [x] Project repo initialized (independent git, initially private on GitHub; later made public)
- [x] `genesis.txt` with ownership, vision, and initial examples
- [x] This `roadmap.md` created
- [x] Basic project structure (src/viva, tests/, examples/, docs/, pyproject.toml, .gitignore)
- [x] README.md (high-level overview)
- [x] Licenses (proprietary + MIT template for public tests) and header template

### Phase 1: Syntax Definition & Grammar (Priority)
- Formalize the syntax (EBNF / PEG / context-free grammar).
- Support for:
  - `life:` declarations with attributes (name, gender/type, birth date, other properties)
  - `event:` declarations with timing windows and probability models
  - `flow:` declarations with amounts (fixed, per-period), triggers (upon event, upon life.death, recurring), duration
- Handle keywords, identifiers, dates, numbers, probabilities, time expressions ("per month", "for 20 years", "in the next 10 years", "uniform annual probability").
- Create a growing set of example `.viva` files.
- **Deliverable**: Documented grammar + reference examples. Initial parser prototype that can at least tokenize and build a basic tree.

### Phase 2: Parser & AST
- Implement a working parser that produces a clean AST / tree representation.
- Error reporting (syntax errors with good messages and locations).
- **Deliverable**: Python module `viva.parser` that can parse example programs into AST.

### Phase 3: Semantic Analysis
- Build symbol tables and resolution for lives, events, and flows.
- Validate references (e.g., "upon child_birth" must refer to a declared event).
- Compute time scopes, dependencies, and probability models.
- Handle edge cases (overlapping flows, multiple lives, infinite vs. finite horizons).
- **Deliverable**: Semantic analyzer that can "understand" a Viva program and report issues or produce an intermediate representation.

### Phase 4: Interpreter & Python Code Generation
- Core execution engine: resolve stochastic events and emit a flat list of dated cash flow events.
- Generate (or directly execute to produce) a Python function with the exact required signature and output format (list of dicts: {'date': date, 'name': str, 'amount': float}).
- Support randomness / seeding for reproducibility.
- **Deliverable**: End-to-end interpreter. Given a Viva program, produce a Python function that can be called to get a list of dated cash flow events.

### Phase 5: Testing, Validation & Fine-Tuning
- Comprehensive test suite:
  - Parser tests (valid + invalid syntax)
  - Semantic tests
  - Interpreter tests against known scenarios (deterministic and stochastic)
  - Example-based tests using the scenarios from `genesis.txt` and new ones
- Monte-Carlo validation: run many simulations and check statistical properties.
- Syntax fine-tuning based on usability feedback (add syntactic sugar, improve readability).
- **Deliverable**: Green test suite + confidence that the interpreter produces correct cash flow models.

### Phase 6: LLM Assistance Exploration (Parallel / Later)
- Set up a small local open-source LLM (e.g., Phi-3, Mistral 7B, Gemma, or Llama-3 quantized).
- Prototype 1: Viva code validator / auto-corrector.
- Prototype 2: Natural language → Viva translator (e.g., the "Paul may have a child..." example).
- Evaluate quality, integration points (CLI tool, in-editor, or as part of the interpreter pipeline).
- **Deliverable**: Experimental LLM module + evaluation notes. Decide on production inclusion.

### Phase 7: Packaging, Documentation & Iteration
- CLI tool: `viva compile input.viva --output simulation.py` or `viva run input.viva --years 30 --sims 1000`
- Python package distribution (PyPI-ready).
- User documentation (syntax reference, tutorials, best practices).
- Example real-world models (retirement planning, family cash flows, business projections, etc.).
- Continuous amendment of this roadmap and `genesis.txt`.
- **Deliverable**: Usable tool + docs. Project ready for broader use and further evolution. (Note: licensing model evolved to dual MIT + commercial after this was written.)

---

## 6. Milestones & Success Criteria

- **M1 (Syntax + Basic Parser)**: Can parse the example from `genesis.txt` and a few variations without errors.
- **M2 (End-to-End Interpreter)**: The generated Python function correctly models the `child_birth` / `child_expense` / `saving` / `insurance` example (including stochastic child birth and death-triggered insurance).
- **M3 (Tested & Robust)**: 80%+ code coverage + passing tests on a battery of scenarios.
- **M4 (LLM Prototypes)**: At least one working LLM-assisted feature (checker or translator).
- **M5 (Usable Tool)**: Non-expert user can write a Viva program, run the interpreter, and get a sensible list of dated cash flow events.

---

## 7. Technical Preferences & Constraints

- Target language for interpreter output: **Python 3** (clean, modern, no unnecessary dependencies in the generated function).
- Development language: Python (for parser, semantics, generator).
- Parser technology: Prefer lightweight and maintainable (Lark is a strong candidate for its grammar-first approach and good error messages).
- Randomness: Use `random` or `numpy.random` with explicit seeding.
- No external services in the core interpreter.
- Keep the generated simulation function pure / side-effect free where possible.
- Version control: Git (this repo). All changes via commits.
- Documentation: Markdown in-repo (this file, README, etc.).

---

## 8. Open Questions & Future Exploration

- Exact API of the generated function (parameters for years, number of simulations, random seed, start date/horizon, etc.).
- Handling of inflation, interest, investment returns on savings.
- Multiple lives and interactions between them (e.g. `upon Jordan.death`, `at age 18 for Child`).
- Continuous time vs discrete years (currently MVP is discrete years).
- Visualization of results (later).
- LLM model choice and local inference stack.
- Potential for a "Viva standard library" of common flows/events.

### Deferred / Future Requirements (tracked for later refinement)
These were deprioritized to reach a working MVP interpreter faster (year-granular dates + single currency). All prior detailed specs are preserved here so we don't forget them:

- **Full date support**: Accept any common formats (mm/dd/yyyy, mm.dd.yyyy, dd/mm/yyyy, dd.mm.yyyy, yyyy.mm.dd, yyyy/mm/dd, "April 3, 2019", etc.). Parser must normalize to Python `date` and issue warnings on ambiguous cases (e.g. 02/03/2010 could be Feb 3 or Mar 2 depending on locale). "born" dates and time windows will support full dates + relative + age + event-based.
- **Per-period granularity & "per month"**: "per month" (and similar) assumes the 1st day of the month unless day is explicitly specified. In final model, recurring flows emit separate dated entries for each period (no proration in output consumer). MVP currently collapses to one Jan-1 entry per year.
- **Multicurrency**: Add variable 'currency' per flow (default 'USD'). Support currency in amounts, conversion? (later).
- **Amount caps like "until 100k total"**: Grammar + semantics for cumulative total caps on flows (in addition to time durations like "for 20 years" or "for life").
- **"for life" durations** and other duration forms.
- **Age references scoped to specific lives**: e.g. `at age 18 for Child` (requires multi-life support in time windows).
- **Probability models**: Currently "uniform annual probability N%", "probability 5% per year", "probability 100%". Later richer distributions?
- **"until X total" handling** as special duration (stop emitting when cumulative reaches cap).
- (Previously resolved in detailed spec but now deferred): exact per-month day defaults, ambiguity warnings, full natural language dates.

See also the simplified MVP rules now in the Interpreter Output Requirement section above. These deferred items will be re-introduced iteratively after we have a working end-to-end simple interpreter.

---

## 9. Next Immediate Steps (updated post MVP birth/death/relative years work)

1. [x] Review/amend `roadmap.md`, `genesis.txt`, `grammar.md`, examples, README, and pptx script for the simplified MVP (bare years + Jan 1 dates, 'currency':'USD' default, all future reqs tracked in Deferred section).
2. [x] Grammar EBNF + diagram updated for year-only date, extended duration (until N total, for life), MVP notes everywhere.
3. [x] Lark added as runtime dep + installed in .venv. Full Lark parser, AST (`Program` etc.), and `simulate()` (later renamed to `generateFlowEngine()`) implemented end-to-end (later refactored to FlowEngine with params/param_distribs/getFlows etc. API).
4. [x] Added `get_parse_tree(source)` returning the raw Lark `Tree` so the grammar can directly produce syntactic trees (`.pretty()`). Created `documentation/lark-grammar-diagram.mmd` + updated `grammar.md` with the full Lark source, syntactic tree examples, and mindmap visualization of the grammar rules.
5. [x] Core features implemented: birth references (symmetric to death, including 's possessive and "N years after"), compact `from year X to/until year Y`, relative small years (<100 offset from start_year), big-number words (thousand/million/billion/trillion + k/m/b/t), death sampling respects late births. MC tests + validation updated. All core docs reviewed/updated.
6. Build / polish the interpreter (already producing correct flat `list[dict(date=Jan1, name, amount, currency='USD')]` for all examples).
7. Add/update tests for the 4 examples (focus on deterministic + basic stochastic paths first). (Ongoing — basic coverage exists.)
8. Once MVP "hello world" simulation is polished, celebrate and then incrementally re-introduce deferred features from the roadmap list (full dates first, etc.).
9. Still: consider a notes/ folder for other explorations. (Consider CLI, more examples using new birth/relative syntax.)

The pivot to simple year model (per your request) makes Phases 1-4 far more tractable quickly while protecting token budget. Full prior specs are safe in the Deferred section.

---

## 10. Amendment Log

- **2026-06-19**: Enhanced public documentation for the `FlowEngine` API in README.md (detailed explanation of `generateFlowEngine`, its 5 members, usage patterns for deterministic vs controlled MC). Clarified the `source` parameter. Updated `scripts/generate_examples_md.py` and regenerated `documentation/examples.md` to document both `drawFlows` (convenience) and the explicit `getFlows`/`params`/`param_distribs` patterns. Cleaned legacy `hello()` placeholder from `src/viva/__init__.py` and its test. Polished `pyproject.toml` (better description, Alpha status, keywords, OS classifier, readme metadata) for public packaging. (Grok)
- **2026-06-04**: User requested simplification to accelerate to working solution and optimize token usage: (1) Dates MVP = bare year only; all transactions dated January 1 of the year (`date(year, 1, 1)`); full flexible dates, natural language, per-month day precision, and ambiguity warnings deferred to roadmap "Deferred Requirements". (2) Add 'currency' field to output dicts (always 'USD' for MVP; multicurrency deferred). Updated genesis.txt (example + output spec), roadmap.md (Interpreter Output Requirement rewritten for MVP, Open Questions expanded with Deferred list + previous detailed specs moved there for safekeeping, amendment), grammar.md + grammar-diagram.mmd (date production simplified to `year`, notes and diagram updated), and all example .viva files (born dates normalized to bare years). This pivots from the prior detailed date model while preserving the flat list output shape and all future requirements for later. (Grok)
- **2026-06-05**: User requested "the lark grammar to be displayed in a syntactic tree". Added `get_parse_tree(source)` (returns raw `lark.Tree`; use `.pretty()` for the syntactic tree of any Viva program). Created `documentation/lark-grammar-diagram.mmd` (Mermaid mindmap of the actual Lark productions). Updated `grammar.md` with the complete current Lark grammar source, instructions + example for getting syntactic trees, and the new diagram. Also updated `roadmap.md` next-steps and amendment log. (Grok)
- **2026-06-17**: Completed integration of mortality tables into core simulation: fixed `upon X.death` grammar/transformer (now correctly populates `attr: 'death'`), standardized `LifeDecl.birth_year`, wired `create_life` + `generate_random_death_year` (with seed derivation) into `simulate()` (later renamed/refactored to `generateFlowEngine()`) for realistic stochastic deaths and "for life" durations. Cleaned duplicate MC validation code. All tests pass; seminal + playground examples now use table-driven deaths. (Grok)
- **Recent (post 2026-06-17, finalized ~June 2026)**: Added full birth references (`upon X.birth` / `X's birth`, `from X.birth`, `N years after X's birth`, direct `event: foo, X's birth` or `Paul's birth`). Extended all death/upon/after/from/until to support both `NAME.death`/`NAME.birth` and possessive `NAME's death`/`NAME's birth` (via APOS_S). Added compact range syntax `from year X to year Y` and `from year X until year Y`. Small year numbers (<100) treated as relative offsets from `start_year` (year N = start_year + N-1). Extended amounts to k/m/b/t + words (thousand/million/billion/trillion, case-insensitive). Death sampling respects `max(start_year, birth_year)` so late-born lives die correctly per q_x. Full grammar + semantic actions, updated MC tests, and all docs reviewed. (Grok)
- **2026-06-18**: Renamed/refactored `simulate` to `generateFlowEngine()` returning a FlowEngine (with .params, .param_distribs, .getFlows, .drawParamRealization, .drawFlows). Removed seed overload entirely. Updated parser facade, __init__, playground, all tests, and docs (README, grammar.md, roadmap). (Grok)
- **2026-06-03**: Initial roadmap created by Grok based on `genesis.txt` annotations and instructions. (This document)
- **2026-06-03 (later)**: Project skeleton setup completed (pyproject.toml, .gitignore, src/viva/, tests/, examples/, licenses/, header template). README updated. Phase 0 items marked done. Next steps refined. Licenses (proprietary + MIT) added per discussion.
- **2026-06-03 (later)**: Added 3 more example .viva files (retirement, family with education, small business) to expand the test cases before formal grammar work. Grammar.md draft started in documentation/.
- **2026-06-03 (later)**: Detailed date handling spec (per user): accept any common formats (mm/dd/yyyy, mm.dd.yyyy, dd/mm/yyyy, dd.mm.yyyy, yyyy.mm.dd, yyyy/mm/dd, "April 3, 2019", etc.). Parser normalizes to Python `date` and must warn on ambiguous dates (e.g. 02/03/2010 vs 03/02/2010). "per month" (and similar recurring) assumes the 1st day of the month unless otherwise specified. Exact interpreter output signature: list[dict['date': date, 'name': str, 'amount': float]]. Updated genesis.txt, roadmap.md (including open questions and amendment), grammar.md (date rule and notes). This resolves the dates question and the per-month/proration issue. (Now superseded by 2026-06-04 simplification; prior spec preserved under Deferred Requirements.)

We will append new entries here each time the roadmap is significantly updated.

---

*End of initial roadmap. Ownership of Viva remains 100% with Alexandre Scherer. This document is a planning artifact to guide our collaborative work.*

**Signed / Acknowledged:**  
Grok 4.3 (xAI) — acting strictly as assistant per the agreement in `genesis.txt`.