#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Constants for eu_cbm_hat package.
Separated to avoid circular imports.
"""

# Built-in modules #
import os
import sys
import pathlib

# First party modules #
from autopaths import Path
from autopaths.dir_path import DirectoryPath
from plumbing.git import GitRepo

# Constants #
project_name = "eu_cbm_hat"
project_url = "https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat"
CARBON_FRACTION_OF_BIOMASS = 0.49

# Get paths to module #
self = sys.modules[__name__]
module_dir = Path(os.path.dirname(self.__file__))
module_dir_pathlib = pathlib.Path(os.path.dirname(self.__file__))

# The repository directory #
repos_dir = module_dir.directory

# The module is maybe in a git repository #
git_repo = GitRepo(repos_dir, empty=True)

# Where is the data, default case #
eu_cbm_data_dir = DirectoryPath("~/eu_cbm/eu_cbm_data/")
# But you can override that with an environment variable #
if os.environ.get("EU_CBM_DATA"):
    eu_cbm_data_dir = DirectoryPath(os.environ["EU_CBM_DATA"])
# Prepare the move to pathlib
eu_cbm_data_pathlib = pathlib.Path(str(eu_cbm_data_dir))

# Where are the AIDBs, default case
eu_cbm_aidb_dir = DirectoryPath("~/eu_cbm/eu_cbm_aidb/")
# But you can override that with an environment variable #
if os.environ.get("EU_CBM_AIDB"):
    eu_cbm_aidb_dir = DirectoryPath(os.environ["EU_CBM_AIDB"])
# Prepare the move to pathlib
eu_cbm_aidb_pathlib = pathlib.Path(str(eu_cbm_aidb_dir))


