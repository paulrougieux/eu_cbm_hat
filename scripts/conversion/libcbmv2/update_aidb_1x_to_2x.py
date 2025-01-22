"""Update the AIDB from libcbm version 1 to libcbm version 2

Use the path to the AIDB repo defined in `eu_cbm_aidb_dir` so that we modify
those files directly.


Usage convert the AIDB from V1 to V2 in all countries:

    # Checkout branch "2.x" of cbm_defaults
    cd ~/eu_cbm/cbm_defaults/
    git checkout 2.x
    # Convert the AIDBs from version 1 to version 2
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/conversion/libcbmv2/update_aidb_1x_to_2x.py

Usage on one country only for debugging purposes to reproduce errors in a
specific country:

    >>> import sys
    >>> import pathlib
    >>> sys.path.append(str(pathlib.Path.home() /  "eu_cbm/eu_cbm_hat/scripts/conversion/libcbmv2/"))
    >>> from update_aidb_1x_to_2x import convert_aidb_to_v2
    >>> from update_aidb_1x_to_2x import countries_dir
    >>> convert_aidb_to_v2(countries_dir / "SI/aidb.db")
    >>> convert_aidb_to_v2(countries_dir / "IE/aidb.db")
    >>> convert_aidb_to_v2(countries_dir / "PL/aidb.db")

Display issues with unique constraints

    >>> from update_aidb_1x_to_2x import display_unique_constraint_issue
    >>> display_unique_constraint_issue(db_path = countries_dir / "PL/aidb.db",
    ...                                 table = "disturbance_matrix_value",
    ...                                 columns = ["disturbance_matrix_id",
    ...                                            "source_pool_id",
    ...                                            "sink_pool_id"])

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


from plumbing.databases.sqlite_database import SQLiteDatabase


countries_dir = pathlib.Path(eu_cbm_aidb_dir) / "countries"


def convert_aidb_to_v2(db_path):
    """Convert the aidb at the given path from V1 to V2"""
    if not db_path.exists():
        raise ValueError(f"There is no AIDB at {db_path}")
    # If it's already a version 2 table, do nothing
    df = pandas.read_sql_table("land_class", "sqlite:///" + str(db_path))
    if "land_type_id_1" in df.columns:
        msg = f"\n\n{db_path} is already a version 2 table because "
        msg += "the land_class table contains the land_type_id_1 column. "
        msg += "skip conversion."
        print(msg)
        return
    db_path_v1 = db_path.parent / "aidb_v1.db"
    db_path_v2 = db_path.parent / "aidb_v2.db"
    # Rename the old AIDB to v1
    shutil.copy(db_path, db_path_v1)
    # Remove the "index" column in the disturbance_matrix_value table.
    # This was introduced by mistake and shouldn't be there.
    db_v1 = SQLiteDatabase(str(db_path_v1))
    dm_values = db_v1.read_df("disturbance_matrix_value")
    dm_values = pandas.read_sql_table(
        "disturbance_matrix_value", "sqlite:///" + str(db_path_v1)
    )
    if "index" in dm_values.columns:
        dm_values.drop(columns="index", inplace=True)
        dm_values.to_sql(
            "disturbance_matrix_value",
            con="sqlite:///" + str(db_path_v1),
            index=False,
            if_exists="replace",
        )
    # Remove the V2 DB if already present
    if db_path_v2.exists():
        db_path_v2.unlink()
    # Update the AIDB from V1 to V2
    db_updater.update("1x_to_2x", db_path_v1, db_path_v2)
    # Make v2 the main table
    shutil.copy(db_path_v2, db_path)
    print(f"\n{db_path} updated to V2\n\n")

def display_unique_constraint_issue(db_path, table, columns):
    """Return rows that don't respect the unique constraint in the given table and column

    Example use:
        
        >>> # See above on how to add this script to your path if needed
        >>> from update_aidb_1x_to_2x import display_unique_constraint_issue
        >>> from update_aidb_1x_to_2x import countries_dir
        >>> db_path = countries_dir / "PL/aidb.db"
        >>> table = "disturbance_matrix_value"
        >>> columns = ["disturbance_matrix_id", "source_pool_id", "sink_pool_id"]
        >>> display_unique_constraint_issue(db_path, table, columns)

    """
    db = SQLiteDatabase(str(db_path))
    df = db.read_df(table)
    df[columns].duplicated()
    dup = df[columns].duplicated(keep=False)
    return df[dup]


if __name__ == "__main__":
    aidbs = countries_dir.glob("**/aidb.db")
    for this_db in aidbs:
        # this_db = countries_dir / "ZZ" / "aidb.db"
        try:
            convert_aidb_to_v2(this_db)
        # Catch all errors. This can be restricted to fewer errors.
        # Generally observed errors are:
        # - sqlite3.OperationalError table disturbance_matrix_value has no
        #   column named index
        # - sqlite3.IntegrityError UNIQUE constraint failed:
        #   vol_to_bio_factor.id
        except Exception as e:
            print(f"Error {this_db}")
            print(e)
            print("\n\n")
