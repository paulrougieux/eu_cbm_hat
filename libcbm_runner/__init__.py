#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Special variables #
__version__ = '0.3.1'

# Built-in modules #
import os, sys

# First party modules #
from autopaths import Path
from autopaths.dir_path import DirectoryPath
from plumbing.git import GitRepo

# Constants #
project_name = 'libcbm_runner'
project_url  = 'https://github.com/xapple/libcbm_runner'

# Get paths to module #
self       = sys.modules[__name__]
module_dir = Path(os.path.dirname(self.__file__))

# The repository directory #
repos_dir = module_dir.directory

# The module is maybe in a git repository #
git_repo = GitRepo(repos_dir, empty=True)

# Where is the data, default case #
libcbm_data_dir = DirectoryPath("~/repos/libcbm_data/")

# But you can override that with an environment variable #
if os.environ.get("LIBCBM_DATA"):
    libcbm_data_dir = DirectoryPath(os.environ['LIBCBM_DATA'])
