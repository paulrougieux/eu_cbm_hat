#!/usr/bin/env python3
"""
This python script is called by the bash script that runs on IIASA accelerator.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil

# Input parameters
LAST_YEAR = 2050
COMBO_NAME = "reference"
COUNTRIES = ["CZ", "IE", "IT"]

# Setup
dest_path = Path("/app/local_data/eu_cbm_data")
dest_path.parent.mkdir(parents=True, exist_ok=True)
# Define the environment variable
# This has to happen before we import anything from eu_cbm_hat
os.environ["EU_CBM_DATA"] = str(dest_path)
# Import has to happen after we set the environment variable
from eu_cbm_hat.core.continent import continent
# Create symbolic links for all country AIDBs
for country in continent:
    country.aidb.symlink_all_aidb()

# Run the scenario combinations for the given list of countries
continent.combos[COMBO_NAME].run(LAST_YEAR, COUNTRIES)
