#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Special variables #
__version__ = '0.4.0'

# Built-in modules #
import os, sys

# First party modules #
from autopaths import Path
from autopaths.dir_path import DirectoryPath
from plumbing.git import GitRepo

# Constants #
project_name = 'eu_cbm_hat'
project_url  = 'https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat'

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

# Where are the AIDBs, default case
eu_cbm_aidb_dir = DirectoryPath("~/eu_cbm/eu_cbm_aidb/")

# But you can override that with an environment variable #
if os.environ.get("EU_CBM_AIDB"):
    eu_cbm_aidb_dir = DirectoryPath(os.environ['EU_CBM_AIDB'])
