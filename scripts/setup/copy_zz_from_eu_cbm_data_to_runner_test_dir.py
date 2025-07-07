""" This script copies the ZZ data from the eu_cbm_data repository

Usage:

    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/setup/copy_zz_from_eu_cbm_data_to_runner_test_dir.py

It has to be run on a machine that has the eu_cbm_data repository. ZZ data is
treated in an identical manner to any other country and remains under version
control in the eu_cbm_data repository. However, for users who do not have
access to the private eu_cbm_data repository, we disseminate this data as part
of the eu_cbm_hat package. The purpose of this script is to copy data
necessary to run ZZ from the eu_cbm_data folder to a folder inside this package
eu_cbm_hat/tests/eu_cbm_data
"""

from pathlib import Path
import shutil
from eu_cbm_hat import eu_cbm_data_dir
from eu_cbm_hat import module_dir

# Path to copy data to
test_data_dir = Path(module_dir) / "tests/eu_cbm_data"
if not test_data_dir.exists():
    test_data_dir.mkdir(parents=True)

# File paths to copy data from
# After deleting all files not necessary to run ZZ
# from the eu_cbm_data repository
# I copied the output of the bash command
#     cd ~/rp/eu_cbm_data
#     find  combos/ common/ countries/ harvest/ -type f
files = """combos/reference.yaml
common/reference_years.csv
common/country_codes.csv
countries/ZZ/common/disturbance_types.csv
countries/ZZ/common/classifiers.csv
countries/ZZ/common/age_classes.csv
countries/ZZ/silv/harvest_factors.csv
countries/ZZ/silv/vol_to_mass_coefs.csv
countries/ZZ/silv/irw_frac_by_dist.csv
countries/ZZ/silv/events_templates.csv
countries/ZZ/activities/mgmt/inventory.csv
countries/ZZ/activities/mgmt/growth_curves.csv
countries/ZZ/activities/mgmt/transitions.csv
countries/ZZ/activities/mgmt/events.csv
countries/ZZ/activities/nd_nsr/inventory.csv
countries/ZZ/activities/nd_nsr/growth_curves.csv
countries/ZZ/activities/nd_nsr/transitions.csv
countries/ZZ/activities/nd_nsr/events.csv
countries/ZZ/activities/nd_sr/inventory.csv
countries/ZZ/activities/nd_sr/growth_curves.csv
countries/ZZ/activities/nd_sr/transitions.csv
countries/ZZ/activities/nd_sr/events.csv
countries/ZZ/activities/deforestation/inventory.csv
countries/ZZ/activities/deforestation/growth_curves.csv
countries/ZZ/activities/deforestation/transitions.csv
countries/ZZ/activities/deforestation/events.csv
countries/ZZ/activities/afforestation/inventory.csv
countries/ZZ/activities/afforestation/growth_curves.csv
countries/ZZ/activities/afforestation/transitions.csv
countries/ZZ/activities/afforestation/events.csv
countries/ZZ/config/associations.csv
domestic_harvest/reference/fw_harvest.csv
domestic_harvest/reference/irw_harvest.csv"""

for line in files.splitlines():
    orig_file = Path(eu_cbm_data_dir) / line
    dest_file = test_data_dir / line
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(orig_file, dest_file)

