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

# Special variables #
__version__ = '1.0.2'

# Built-in modules #
import os
import sys
import pathlib

# First party modules #
from autopaths import Path
from autopaths.dir_path import DirectoryPath
from plumbing.git import GitRepo

# Constants #
project_name = 'eu_cbm_hat'
project_url  = 'https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat'
CARBON_FRACTION_OF_BIOMASS = 0.49

# Get paths to module #
self       = sys.modules[__name__]
module_dir = Path(os.path.dirname(self.__file__))

# The repository directory #
repos_dir = module_dir.directory

# The module is maybe in a git repository #
git_repo = GitRepo(repos_dir, empty=True)

# Where is the data, default case #
eu_cbm_data_dir = DirectoryPath("~/eu_cbm/eu_cbm_data/")

# But you can override that with an environment variable #
if os.environ.get("EU_CBM_DATA"):
    eu_cbm_data_dir = DirectoryPath(os.environ['EU_CBM_DATA'])

# Prepare the move to pathlib
eu_cbm_data_pathlib = pathlib.Path(str(eu_cbm_data_dir))

# Where are the AIDBs, default case
eu_cbm_aidb_dir = DirectoryPath("~/eu_cbm/eu_cbm_aidb/")

# But you can override that with an environment variable #
if os.environ.get("EU_CBM_AIDB"):
    eu_cbm_aidb_dir = DirectoryPath(os.environ['EU_CBM_AIDB'])
