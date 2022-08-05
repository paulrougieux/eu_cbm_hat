#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.

A script to run the imaginary `ZZ` country to test the pipeline.
This version runs with the environment variable set to a temporary file.

Typically you would run this file from a command line like this:

    ipython3 -i -- ~/deploy/libcbm_runner/scripts/running/run_zz_in_temp_dir_without_libcbm_data.py


"""

from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil

temp_dir = TemporaryDirectory()
dest_path = Path(temp_dir.name) / "libcbm_data"
# Define the environment variable
# This has to happen before we import anything from libcbm_runner
os.environ["LIBCBM_DATA"] = str(dest_path)

# Internal modules
from libcbm_runner import module_dir
orig_path = Path(module_dir) / "tests/libcbm_data"
# Copy ZZ test data to a temporary directory
shutil.copytree(orig_path, dest_path)

# This has to happen after we copy ZZ data to a temporary directory
from libcbm_runner.core.continent import continent
runner = continent.combos['hat'].runners['ZZ'][-1]
# Create the AIDB symlink
runner.country.aidb.symlink_all_aidb()
runner.num_timesteps = 30
# Run the test country ZZ
runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

# Remove the temporary directory
temp_dir.cleanup()
