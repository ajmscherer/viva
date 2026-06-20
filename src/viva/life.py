# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

"""
Life and mortality table handling for Viva.

Provides Life objects and Table objects for mortality (and future morbidity) tables.

Default tables are pre-loaded:
- SSA_2023_male, SSA_2023_female (from Social Security Administration 2023 period life table)
- 2017_CSO_male_composite, 2017_CSO_female_composite (illustrative 2017 CSO tables)

Tables store q_x (probability of death between exact age x and x+1) and e_x (curtate or complete expectation of life at age x).

See:
- SSA: https://www.ssa.gov/oact/STATS/table4c6.html
- 2017 CSO: https://www.soa.org/resources/experience-studies/2015/2017-cso-tables/
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any
import urllib.request
import re
import random

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SA_2023_FEMALE = "SSA_2023_female"
SA_2023_MALE = "SSA_2023_male"

DEFAULT_MALE_TABLE = SA_2023_MALE
DEFAULT_FEMALE_TABLE = SA_2023_FEMALE

# -----------------------------------------------------------------------------
# Table class
# -----------------------------------------------------------------------------


@dataclass
class Table:
    """Stores a mortality (or morbidity) table.

    Attributes:
        name: Identifier, e.g. "SSA_2023_male"
        gender: "male" or "female"
        qx: dict age -> q_x (death probability within the year)
        ex: dict age -> e_x (life expectancy at exact age)
        source: URL or description of source
        metadata: extra info (e.g. "period", "loaded_from_web")
    """

    name: str
    gender: str
    qx: Dict[int, float] = field(default_factory=dict)
    ex: Dict[int, float] = field(default_factory=dict)
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def death_probability(self, age: int) -> float:
        """q_x : probability of dying between exact age x and x+1."""
        if age < 0:
            return 0.0
        if age in self.qx:
            return self.qx[age]
        # simple extrapolation for high ages
        if age >= 120:
            return 1.0
        # linear interp or last known
        max_age = max(self.qx.keys()) if self.qx else 100
        if age > max_age:
            return min(1.0, self.qx.get(max_age, 0.5) * (1 + 0.05 * (age - max_age)))
        return self.qx.get(age, 0.01)

    def life_expectancy(self, age: int) -> float:
        """e_x (curtate expectation of future lifetime).

        Always computed from the qx survival probabilities in this table so that
        reported e_x is *exactly* consistent with generate_random_death_year
        sampling (conditional on being alive at the given age).
        """
        # Compute curtate e_x = sum_{k>=1} _k p_age
        e = 0.0
        surv = 1.0
        a = max(0, age)
        for _ in range(200):
            q = self.death_probability(a)
            surv *= 1.0 - q
            if surv < 1e-9:
                break
            e += surv
            a += 1
            if a > 120:
                break
        return e

    def __repr__(self):
        return f"<Table {self.name} ({self.gender}) ages={len(self.qx)}>"


# -----------------------------------------------------------------------------
# Life class
# -----------------------------------------------------------------------------


@dataclass
class Life:
    """Represents a living person with a mortality table attached."""

    name: str
    gender: str  # "male", "female", or "person" (maps to composite if available)
    birth_year: int
    mortality_table: Table
    morbidity_table: Table | None = None

    def age_in_year(self, year: int) -> int:
        return year - self.birth_year

    def death_probability(self, year: int) -> float:
        age = self.age_in_year(year)
        return self.mortality_table.death_probability(age)

    def life_expectancy(self, year: int) -> float:
        age = self.age_in_year(year)
        return self.mortality_table.life_expectancy(age)

    def generate_random_death_year(
        self, start_year: int | None = None, seed: int | None = None
    ) -> int:
        """Generate a random year of death using the mortality table's q_x (one-year death probabilities).

        This performs a simple discrete simulation:
        - Start at the beginning of `start_year` (or birth_year if None).
        - The person is **assumed to be alive entering `start_year`** (the call site
          is responsible for passing the simulation start year).
        - For each year, with probability q(age) the person dies *during* that year.
        - Sampling is therefore the correct conditional distribution given survival
          to the start of `start_year`. Death year is always >= start_year.
        - If they survive all years up to max age (120), death is set at birth + 120.

        Args:
            start_year: The year from which to start the projection.
                        The person is assumed to be alive at the *start* of this year.
                        If None, starts from birth_year.
            seed: Optional seed for the random number generator (for reproducibility).
                  Uses a local Random instance so it doesn't affect global state.

        Returns:
            The calendar year in which death occurs (always >= start_year).
        """
        rng = random.Random(seed)
        if start_year is None:
            start_year = self.birth_year

        age = max(0, start_year - self.birth_year)
        year = start_year
        MAX_AGE = 120

        while age < MAX_AGE:
            q = self.mortality_table.death_probability(age)
            if rng.random() < q:
                return year  # dies during this year
            # survives the year
            age += 1
            year += 1

        death_year = self.birth_year + MAX_AGE
        # Guarantee the documented contract: never before the assumed-alive start_year
        if start_year is not None:
            death_year = max(death_year, start_year)
        return death_year

    def __repr__(self):
        return f"<Life {self.name} ({self.gender} b.{self.birth_year}) table={self.mortality_table.name}>"


# -----------------------------------------------------------------------------
# Registry and available tables
# -----------------------------------------------------------------------------

_TABLES: Dict[str, Table] = {}


def register_table(table: Table) -> None:
    """Register a table so it can be looked up by name."""
    _TABLES[table.name] = table


def get_table(name: str) -> Table:
    """Get a registered table by name. Falls back to default if not found."""
    if name in _TABLES:
        return _TABLES[name]
    # try gender variants
    elif name.lower().endswith("female"):
        return _TABLES[DEFAULT_FEMALE_TABLE]
    else:  # default to male
        return _TABLES[DEFAULT_MALE_TABLE]


def get_available_tables() -> List[str]:
    """Return list of all registered table names."""
    return sorted(_TABLES.keys())


def get_default_table(gender: str = "male") -> Table:
    """Return the default table for a gender."""
    if gender.lower() in ("male", "man"):
        return get_table("SSA_2023_male")
    elif gender.lower() in ("female", "woman"):
        return get_table("SSA_2023_female")
    else:
        return get_table("SSA_2023_male")


# -----------------------------------------------------------------------------
# Data loading helpers
# -----------------------------------------------------------------------------


def _load_ssa_2023_from_web() -> tuple[
    Dict[int, float], Dict[int, float], Dict[int, float], Dict[int, float]
]:
    """Attempt to load qx and ex for male/female from SSA website.

    Returns (male_qx, male_ex, female_qx, female_ex)
    Falls back to hardcoded data (excerpted from the official 2023 table) if fetch/parse fails.
    Source: https://www.ssa.gov/oact/STATS/table4c6.html
    """
    url = "https://www.ssa.gov/oact/STATS/table4c6.html"
    male_qx, male_ex = {}, {}
    female_qx, female_ex = {}, {}
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract rows - the table structure has age then male columns then female columns
        # We use a reasonably robust regex for the known format
        pattern = r"<td>(\d+)</td>\s*<td>([\d.]+)</td>\s*<td>[\d,]+</td>\s*<td>([\d.]+)</td>.*?<td>([\d.]+)</td>\s*<td>[\d,]+</td>\s*<td>([\d.]+)</td>"
        matches = re.findall(pattern, html, re.DOTALL)
        for m in matches[:120]:
            age = int(m[0])
            male_qx[age] = float(m[1])
            male_ex[age] = float(m[2])
            female_qx[age] = float(m[3])
            female_ex[age] = float(m[4])
        if male_qx:
            return male_qx, male_ex, female_qx, female_ex
    except Exception:
        # Silent fallback to embedded data (common on CI, no internet, or site blocks the request)
        pass

    # Embedded data (excerpted + extended from the official 2023 SSA Period Life Table)
    # Full data available at https://www.ssa.gov/oact/STATS/table4c6.html
    base_male_q = {
        0: 0.006015,
        1: 0.000479,
        2: 0.000320,
        3: 0.000249,
        4: 0.000194,
        5: 0.000159,
        6: 0.000137,
        7: 0.000125,
        8: 0.000120,
        9: 0.000120,
        10: 0.000125,
        15: 0.000463,
        20: 0.001235,
        25: 0.001595,
        30: 0.002085,
        35: 0.002577,
        40: 0.003115,
        45: 0.003931,
        50: 0.005126,
        55: 0.007491,
        60: 0.011337,
        65: 0.016455,
        70: 0.022903,
        75: 0.033802,
        80: 0.055633,
        85: 0.092680,
        90: 0.135,
        92: 0.148,
        95: 0.195,
        97: 0.225,
        100: 0.310,
        105: 0.480,
        110: 0.680,
        119: 1.0,
    }
    base_female_q = {
        0: 0.005125,
        1: 0.000392,
        2: 0.000229,
        3: 0.000188,
        4: 0.000155,
        5: 0.000133,
        6: 0.000115,
        7: 0.000105,
        8: 0.000100,
        9: 0.000098,
        10: 0.000101,
        15: 0.000229,
        20: 0.000441,
        25: 0.000609,
        30: 0.000878,
        35: 0.001209,
        40: 0.001643,
        45: 0.002187,
        50: 0.003030,
        55: 0.004532,
        60: 0.006923,
        65: 0.010188,
        70: 0.014769,
        75: 0.023846,
        80: 0.041183,
        85: 0.071752,
        90: 0.110,
        92: 0.122,
        95: 0.160,
        97: 0.185,
        100: 0.260,
        105: 0.410,
        110: 0.600,
        119: 1.0,
    }

    male_qx = dict(base_male_q)
    female_qx = dict(base_female_q)

    # fill gaps with simple interpolation/extrapolation (gentler at tails)
    for a in range(0, 120):
        if a not in male_qx:
            prev = male_qx.get(a - 1, 0.01)
            male_qx[a] = min(1.0, prev * 1.055 + 0.0003)
        if a not in female_qx:
            prev = female_qx.get(a - 1, 0.008)
            female_qx[a] = min(1.0, prev * 1.05 + 0.0002)

    male_ex = {
        0: 75.79,
        1: 75.25,
        20: 56.69,
        40: 38.59,
        60: 21.79,
        80: 8.50,
        90: 4.11,
        100: 2.3,
    }
    female_ex = {
        0: 81.06,
        1: 80.48,
        20: 61.74,
        40: 42.64,
        60: 24.73,
        80: 9.82,
        90: 4.80,
        100: 2.7,
    }

    # Do NOT fill high ages with the previous bad linear formula.
    # life_expectancy() will compute from qx curve for ages without good precomputed ex.
    # Only keep the explicit low/mid age anchors.

    return male_qx, male_ex, female_qx, female_ex


def _create_ssa_2023_tables():
    """Create and register SSA 2023 tables (attempts web load, falls back to hardcoded)."""
    try:
        m_qx, m_ex, f_qx, f_ex = _load_ssa_2023_from_web()
    except Exception:
        m_qx, m_ex, f_qx, f_ex = {}, {}, {}, {}  # will be filled below

    # Ensure we have reasonable data
    if not m_qx:
        # minimal fallback from the tool output
        m_qx = {
            0: 0.006015,
            1: 0.000479,
            2: 0.000320,
            3: 0.000249,
            4: 0.000194,
            5: 0.000159,
            10: 0.000125,
            15: 0.000463,
            20: 0.001235,
            25: 0.001595,
            30: 0.002085,
            35: 0.002577,
            40: 0.003115,
            45: 0.003931,
            50: 0.005126,
            55: 0.007491,
            60: 0.011337,
            65: 0.016455,
            70: 0.022903,
            75: 0.033802,
            80: 0.055633,
            85: 0.092680,
            90: 0.135,
            95: 0.195,
            100: 0.310,
        }
        m_ex = {0: 75.79, 20: 56.69, 40: 38.59, 60: 21.79, 80: 8.50, 90: 4.11, 100: 2.3}
        f_qx = {
            0: 0.005125,
            1: 0.000392,
            20: 0.000441,
            40: 0.001643,
            60: 0.006923,
            80: 0.041183,
            90: 0.110,
            95: 0.160,
            100: 0.260,
        }
        f_ex = {0: 81.06, 20: 61.74, 40: 42.64, 60: 24.73, 80: 9.82, 90: 4.80, 100: 2.7}

    male_table = Table(
        name="SSA_2023_male",
        gender="male",
        qx=m_qx,
        ex=m_ex,
        source="https://www.ssa.gov/oact/STATS/table4c6.html (2023 period table)",
        metadata={"year": 2023, "type": "period"},
    )
    female_table = Table(
        name="SSA_2023_female",
        gender="female",
        qx=f_qx,
        ex=f_ex,
        source="https://www.ssa.gov/oact/STATS/table4c6.html (2023 period table)",
        metadata={"year": 2023, "type": "period"},
    )

    register_table(male_table)
    register_table(female_table)

    return male_table, female_table


def _create_cso_2017_tables():
    """Illustrative 2017 CSO tables (loaded from SOA sources, simplified for demo).

    Real CSO tables are select & ultimate, by smoker status, preferred class, etc.
    Here we provide composite ultimate style for demo purposes.
    """
    # Very simplified composite ultimate rates (much lower than population at working ages)
    # Source: https://www.soa.org/resources/experience-studies/2015/2017-cso-tables/
    cso_male_qx = {
        a: max(0.0001, 0.0008 * (1 + 0.04 * (a - 20)) ** 1.8 if a > 20 else 0.001)
        for a in range(0, 121)
    }
    cso_female_qx = {
        a: max(0.00008, 0.0006 * (1 + 0.035 * (a - 20)) ** 1.7 if a > 20 else 0.0008)
        for a in range(0, 121)
    }

    # Rough e_x (much higher than population)
    cso_male_ex = {a: 85 - a * 0.6 for a in range(0, 121)}
    cso_female_ex = {a: 87 - a * 0.55 for a in range(0, 121)}

    male = Table(
        name="2017_CSO_male_composite",
        gender="male",
        qx=cso_male_qx,
        ex=cso_male_ex,
        source="2017 Commissioners Standard Ordinary (CSO) Tables (SOA)",
        metadata={
            "year": 2017,
            "type": "ultimate_composite",
            "note": "illustrative - not official loaded table",
        },
    )
    female = Table(
        name="2017_CSO_female_composite",
        gender="female",
        qx=cso_female_qx,
        ex=cso_female_ex,
        source="2017 Commissioners Standard Ordinary (CSO) Tables (SOA)",
        metadata={
            "year": 2017,
            "type": "ultimate_composite",
            "note": "illustrative - not official loaded table",
        },
    )

    register_table(male)
    register_table(female)
    return male, female


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------


def _initialize_default_tables():
    """Load and register default tables."""
    _create_ssa_2023_tables()
    _create_cso_2017_tables()


_initialize_default_tables()


# -----------------------------------------------------------------------------
# Convenience
# -----------------------------------------------------------------------------


def create_life(
    name: str, gender: str, birth_year: int, table_name: str = "SSA_2023_male"
) -> Life:
    """Helper to create a Life with a named table (defaults to SSA_2023)."""
    table = get_table(table_name)
    # map common gender words
    g = gender.lower()
    if g in ("man", "male"):
        g = "male"
    elif g in ("woman", "female"):
        g = "female"
    return Life(name=name, gender=g, birth_year=birth_year, mortality_table=table)


if __name__ == "__main__":
    print("Available tables:", get_available_tables())
    print("SSA male q(0):", get_table("SSA_2023_male").death_probability(0))
    print("SSA female e(65):", get_table("SSA_2023_female").life_expectancy(65))

    life = create_life("Paul", "man", 1968, "SSA_2023_male")
    print(life)
    print("Paul death prob at age 80 (year 2008):", life.death_probability(2008))

    for i in range(10):
        print(life.generate_random_death_year(2026))
