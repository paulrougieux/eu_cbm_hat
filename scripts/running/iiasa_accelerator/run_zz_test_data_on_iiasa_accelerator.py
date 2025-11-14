#!/usr/bin/env python3
"""
This python script is called by the bash script that runs on IIASA accelerator.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil

dest_path = Path("/app/local_data/output/eu_cbm_data_tests")
dest_path.parent.mkdir(parents=True, exist_ok=True)
# Define the environment variable
# This has to happen before we import anything from eu_cbm_hat
os.environ["EU_CBM_DATA"] = str(dest_path)

# Import has to happen after we set the environment variable
from eu_cbm_hat import module_dir
orig_path = Path(module_dir) / "tests/eu_cbm_data"
# Copy ZZ test data to a temporary directory
shutil.copytree(orig_path, dest_path)

# Import has to happen after we copy ZZ data to the destination directory
from eu_cbm_hat.core.continent import continent
runner = continent.combos['reference'].runners['ZZ'][-1]
# Create the AIDB symlink
runner.country.aidb.symlink_all_aidb()
runner.num_timesteps = 30
# Run the test country ZZ
runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

