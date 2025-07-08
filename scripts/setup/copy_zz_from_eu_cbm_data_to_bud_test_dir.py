""" The purpose of this script is to copy data necessary to test the bud object.

Usage:

    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/setup/copy_zz_from_eu_cbm_data_to_bud_test_dir.py

It has to be run on a machine that has the eu_cbm_data repository and the
output of a ZZ model run. i.e. run ZZ first with:

     ipython3 -i -- ~/repos/eu_cbm/eu_cbm_hat/scripts/running/run_zz.py

"""

import shutil
from eu_cbm_hat import eu_cbm_data_pathlib
from eu_cbm_hat import module_dir_pathlib

# Path to copy data from
zz_associations_path = eu_cbm_data_pathlib / "countries/ZZ/config/associations.csv"
zz_reference_output_dir = eu_cbm_data_pathlib / "output/reference/ZZ/0"
if not zz_reference_output_dir.exists():
    msg = "Run the model first with:\n"
    msg += "ipython -i -- ~/repos/eu_cbm/eu_cbm_hat/scripts/running/run_zz.py"
    raise ValueError(msg)

# Path to copy data to
test_data_dir = module_dir_pathlib / "tests/bud_data"
if not test_data_dir.exists():
    test_data_dir.mkdir(parents=True)

associations_path = test_data_dir / "input/csv/associations.csv"
print(f"\nCopy {zz_associations_path}")
print(f"to {associations_path}")
shutil.copy(zz_associations_path, associations_path)

# libcbm input file paths to copy data from
# I copied the output of the bash command
# cd ~/eu_cbm/eu_cbm_data/output/reference/ZZ/0/
# find input -type f
files = """input/csv/inventory.csv
input/csv/disturbance_types.csv
input/csv/growth_curves.csv
input/csv/transitions.csv
input/csv/classifiers.csv
input/csv/events.csv
input/csv/age_classes.csv
"""

print(f"\nCopy\n{files}")
print(f"from \n {zz_reference_output_dir}\nto\n {test_data_dir}")
for line in files.splitlines():
    orig_file = zz_reference_output_dir / line
    dest_file = test_data_dir / line
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(orig_file, dest_file)

