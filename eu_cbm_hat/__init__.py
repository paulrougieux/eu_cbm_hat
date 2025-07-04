#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair, Paul Rougieux and Viorel Blujdea.

JRC Biomass Project.
Unit D1 Bioeconomy.

- The core simulation tools are documented at `eu_cbm_hat.core`.
- Scenario combinations are defined in `eu_cbm_hat.combos` (the current
mechanism is subjected to change to allow user defined scenarios, provide
feedback under [issue
50](https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat/-/issues/50) ).
- The Harvest Allocation Tool is implemented in `eu_cbm_hat.cbm.dynamic`.

"""

# Special variables
__version__ = '2.0.1'

# Import constants first (no circular dependency)
from eu_cbm_hat.constants import (
    project_name,
    project_url,
    CARBON_FRACTION_OF_BIOMASS,
    module_dir,
    module_dir_pathlib,
    repos_dir,
    git_repo,
    eu_cbm_data_dir,
    eu_cbm_data_pathlib,
    eu_cbm_aidb_dir,
    eu_cbm_aidb_pathlib,
)

# Now import classes (after constants are available)
from eu_cbm_hat.bud import Bud

# Use __all__ to let type checkers know what is part of the public API.
__all__ = [
    "Bud",
    "eu_cbm_aidb_dir",
    "eu_cbm_aidb_pathlib",
    "eu_cbm_data_dir",
    "eu_cbm_data_pathlib",
    "repos_dir",
    "module_dir",
    "module_dir_pathlib",
    "CARBON_FRACTION_OF_BIOMASS",
    "project_name",
    "project_url",
]

