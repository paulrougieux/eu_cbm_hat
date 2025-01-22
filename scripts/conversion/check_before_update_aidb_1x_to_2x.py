"""before the update the AIDB from libcbm version 1 to libcbm version 2, 
check if there are mismatches between genus and forest typesin species table
"""

import pathlib
import shutil
import pandas
from cbm_defaults.update import db_updater
from eu_cbm_hat import eu_cbm_aidb_dir


from plumbing.databases.sqlite_database import SQLiteDatabase


countries_dir = pathlib.Path(eu_cbm_aidb_dir) / "countries"


def display_mismatch_forest_type_genus_type(db_path, table, columns):
    """
    >>> import sys
    >>> import pathlib
    >>> sys.path.append(str(pathlib.Path.home() /  "eu_cbm/eu_cbm_hat/scripts/conversion/libcbmv2/"))
    >>> from check_before_update_aidb_1x_to_2x import display_mismatch_forest_type_genus_type
    >>> from check_before_update_aidb_1x_to_2x import countries_dir
    >>> display_mismatch_forest_type_genus_type(countries_dir /"FI/aidb.db", table = "species", columns = ['genus_id','forest_type_id'])
    """
    db = SQLiteDatabase(str(db_path))
    df = db.read_df(table)
    
    # Group by genus_id and check if forest_type_id is unique
    unique_forest_types = df.groupby('genus_id')['forest_type_id'].nunique() > 1
    
    # Filter the data to show only the subsets where forest_type_id is not unique
    result = df[df['genus_id'].isin(unique_forest_types[unique_forest_types].index)]
    
    # Print the result
    return(result)


def display_duplicates_in_v1(db_path, table, columns):
    """
    Display duplications in a table based on specified columns.

    Args:
        db_path (pathlib.Path): The path to the database file.
        table (str): The name of the table to check for duplications.
        columns (list): A list of column names to consider for duplications.

    Returns:
        pd.DataFrame: A DataFrame containing the duplicate rows.
    """

    # Connect to the database and read the table into a DataFrame
    db = SQLiteDatabase(str(db_path))
    df = db.read_df(table)

    # Check if the columns exist in the DataFrame
    if not all(col in df.columns for col in columns):
        raise ValueError(f"One or more columns {columns} do not exist in the DataFrame.")

    # Find duplicates
    duplicates = df[df.duplicated(subset=columns, keep=False)]

    # Print the result
    print(f"Duplications in {table} based on {columns}:")
    print(duplicates)

    return duplicates


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
