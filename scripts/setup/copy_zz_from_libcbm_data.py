""" This script copies the ZZ data from the libcbm_data repository

It has to be run on a machine that has the libcbm_data repository. ZZ data is
treated in an identical manner to any other country and remains under version
control in the libcbm_data repository. However, for users who do not have
access to the private libcbm_data repository, we disseminate this data as part
of the libcbm_runner package. The purpose of this script is to copy data
necessary to run ZZ from the libcbm_data folder to a folder inside this package
libcbm_runner/tests/libcbm_data
"""

from pathlib import Path
import shutil
from libcbm_runner import libcbm_data_dir
from libcbm_runner import module_dir

# Path to copy data to
test_data_dir = Path(module_dir) / "tests/libcbm_data"
if not test_data_dir.exists():
    test_data_dir.mkdir(parents=True)

# File paths to copy data from
# After deleting all files not necessary to run ZZ
# from the libcbm_data repository
# I copied the output of the bash command
#     cd ~/rp/libcbm_data
#     find  combos/ common/ countries/ demand/ -type f
# To obtain the following lines of files necessary to run ZZ
files = """combos/hat.yaml
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
demand/reference/fw_demand.csv
demand/reference/irw_demand.csv"""

for line in files.splitlines():
    orig_file = Path(libcbm_data_dir) / line
    dest_file = test_data_dir / line
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(orig_file, dest_file)

