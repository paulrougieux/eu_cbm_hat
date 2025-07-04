"""Copy test input to a temporary directory

"""

import tempfile
import shutil
from pathlib import Path
from eu_cbm_hat.constants import module_dir_pathlib

DATA_DIR = module_dir_pathlib / "tests/bud_data"

def copy_input_to_temp_dir() -> Path:
    """
    Copies the input data directory to a new temporary directory.
    Returns the Path to the temporary directory.
    """
    tmpdir = Path(tempfile.mkdtemp())
    temp_data_dir = tmpdir / DATA_DIR.name
    shutil.copytree(DATA_DIR, temp_data_dir)
    print(f"Temporary directory created at: {temp_data_dir}")
    return temp_data_dir

