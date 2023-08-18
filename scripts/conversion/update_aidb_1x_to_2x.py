"""Update the AIDB from libcbm version 1 to libcbm version 2

Use path to the AIDB repo defined in
So that we modify those files directly

See also:

    - The documentation on how to migrate from libcbm version 1 to libcbm
    version 2
    https://github.com/cat-cfs/cbm_defaults#migrating-database-version

    - An issue encountered when trying to use libcbm 2
    https://github.com/cat-cfs/libcbm_py/issues/58

"""

import pathlib
import shutil
import pandas
from cbm_defaults.update import db_updater
from eu_cbm_hat import eu_cbm_aidb_dir

countries_dir = pathlib.Path(eu_cbm_aidb_dir) / "countries"
aidbs = countries_dir.glob("**/aidb.db")

for db_path in aidbs:
    # db_path = countries_dir / "ZZ" / "aidb.db"
    assert db_path.exists()
    # If it's already a version 2 table, do nothing
    df = pandas.read_sql_table("land_class", "sqlite:///" + str(db_path))
    if "land_type_id_1" in df.columns:
        msg = f"\n\n{db_path} is already a version 2 table because the land_class table "
        msg += "contains the land_type_id_1 column."
        msg += "skip conversion."
        print(msg)
        continue
    db_path_v1 = db_path.parent / "aidb_v1.db"
    db_path_v2 = db_path.parent / "aidb_v2.db"
    # Rename the old table to v1
    shutil.copy(db_path, db_path_v1)
    # Remove V2 if present
    if db_path_v2.exists():
        db_path_v2.unlink()
    try:
        # Update the AIDB from V1 to V2
        db_updater.update("1x_to_2x", db_path_v1, db_path_v2)
        # Make v2 the main table
        shutil.copy(db_path_v2, db_path)
        print(f"\n\n{db_path} updated to V2")
    except Exception as e:
        print(f"\n\nError {db_path}")
        print(e)
