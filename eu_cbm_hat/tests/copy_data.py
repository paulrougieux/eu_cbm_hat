"""Copy package internal test data to the eu_cbm_data folder

Usage:

    from eu_cbm_hat.tests.copy_data import copy_test_data
    copy_test_data()

"""
import shutil
from pathlib import Path
from eu_cbm_hat.constants import module_dir, eu_cbm_data_dir

def copy_test_data():
    """Copy tests data from the package internal test folder
    to the eu_cbm_data folder"""
    orig_path = Path(module_dir) / "tests/eu_cbm_data"
    dest_path = Path(eu_cbm_data_dir)
    # Create the data folder if it doesn't exist
    # dest_path.mkdir(exist_ok=True, parents=True)
    # Copy ZZ test data to the eu_cbm_data directory
    # msg = f"\nIf the {dest_path} contains data already, "
    # msg += "this command will erase and replace the data :\n - "
    # if input(msg + "\nPlease confirm [y/n]:") != "y":
    #     print("Cancelled.")
    # else:
    shutil.copytree(orig_path, dest_path, dirs_exist_ok=False)
