#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.

A script to run the imaginary `ZZ` country to test the pipeline.
This version runs with the environment variable set to a temporary file.

Typically you would run this file from a command line like this:

    ipython3 -i -- ~/deploy/eu_cbm/eu_cbm_hat/scripts/running/run_zz_in_temp_dir_without_eu_cbm_data.py


On a development machine, you can update the ZZ dataset stored inside this repository with:

    ipython3 -i -- ~/deploy/eu_cbm/eu_cbm_hat/scripts/setup/copy_zz_from_eu_cbm_data_to_runner_test_dir.py

"""

from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil

temp_dir = TemporaryDirectory()
dest_path = Path(temp_dir.name) / "eu_cbm_data"
# Define the environment variable
# This has to happen before we import anything from eu_cbm_hat
os.environ["EU_CBM_DATA"] = str(dest_path)

# Internal modules
from eu_cbm_hat import module_dir
orig_path = Path(module_dir) / "tests/eu_cbm_data"
# Copy ZZ test data to a temporary directory
shutil.copytree(orig_path, dest_path)

# This has to happen after we copy ZZ data to a temporary directory
from eu_cbm_hat.core.continent import continent
runner = continent.combos['reference'].runners['ZZ'][-1]
# Create the AIDB symlink
runner.country.aidb.symlink_all_aidb()
runner.num_timesteps = 30
# Run the test country ZZ
runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

# Remove the temporary directory
temp_dir.cleanup()
