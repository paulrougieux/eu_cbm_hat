"""Copy package internal test data to the libcbm_data folder

Usage:

    from libcbm_runner.tests.copy_data import copy_test_data
    copy_test_data()

"""
import shutil
from pathlib import Path
from libcbm_runner import module_dir, libcbm_data_dir

def copy_test_data():
    """Copy tests data from the package internal test folder
    to the libcbm_data folder"""
    orig_path = Path(module_dir) / "tests/libcbm_data"
    dest_path = Path(libcbm_data_dir)
    # Create the data folder if it doesn't exist
    dest_path.mkdir(exist_ok=True, parents=True)
    # Copy ZZ test data to the libcbm_data directory
    # msg = f"\nIf the {dest_path} contains data already, "
    # msg += "this command will erase and replace the data :\n - "
    # if input(msg + "\nPlease confirm [y/n]:") != "y":
    #     print("Cancelled.")
    # else:
    shutil.copytree(orig_path, dest_path)