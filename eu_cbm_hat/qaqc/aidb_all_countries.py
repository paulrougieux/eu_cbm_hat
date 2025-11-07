"""The purpose of this script is to compare AIDB data between countries

The goal is to harmonize AIDB data between countries. To reduce the number of
tables that differ between countries to the necessary minimum. Some
disturbances, soil, climate or other parameters differ between countries and
that is fine. But the differences should be clear by the use of country
specific classifiers. When that is not possible, then the table will be
different for each countries. The number of tables that differ should be
reduced to a minimum. 

Another goal is to run a scenario combination with the yaml file containing a
field common_aidb_all_countries: True which indicates the use of a common AIDB
for all countries. We will compare the output of the reference scenario using a
common AIDB to a scenario using an AIDB specific to one country.

The following script implements methods to:

1. Load a table for all countries, keep the country code in a column as
   identifier. If slow, save this to a parquet or csv file in
   eu_cbm_data/output_agg/aidb_qaqc/ csv file if not too big

2. For a given table in a given country analyse the number of rows it has in
   common with all other countries.

TODO: make a notebook with statistics on tables.

List all tables in the AIDB

>>> from eu_cbm_hat.core.continent import continent
>>> continent.countries["ZZ"].aidb
>>> for country_code, country in continent.countries.items():
>>>     print(country_code, country.aidb)
>>>     df = self.db.read_df(table_name)

Display the number of available tables in all AIDBs in all countries:

>>> from eu_cbm_hat.core.continent import continent
>>> for code, country in continent.countries.items():
>>>     print(code, len(country.aidb.db.tables), "tables.")

Generate a table with the length of all tables in all AIDBs in all countries:

>>> import pandas as pd
>>> from eu_cbm_hat.core.continent import continent
>>> df_all = pd.DataFrame()
>>> for country_code, country in continent.countries.items():
>>>    df = pd.DataFrame({"country":[country_code]})
>>>    for table in continent.countries[country_code].aidb.tables:
>>>        df[table] = len(continent.countries[country_code].aidb.db.read_df(table))
>>>    print(df)
>>>    df_all = pd.concat([df_all, df]).reset_index(drop=True)
>>> print(df_all)
>>> print("Unique values")
>>> for col in df_all.columns:
...     print(col, df_all[col].unique())
>>> df_all.to_csv("/tmp/aidb_table_lengths.csv", index=False)

Display tables that always have the same number of rows:

>>> nrows_per_table = {t: df_all[t].unique() for t in df_all.columns}
>>> for table, nrows in nrows_per_table.items():
>>>     if len(nrows)==1:
>>>         print(table, nrows)

Display tables that have different number of rows:

>>> for table, nrows in nrows_per_table.items():
>>>     if len(nrows)>1:
>>>         print(table, nrows)

Make sure that all AIDBs have the same tables:

>>> from eu_cbm_hat.core.continent import continent
>>> from eu_cbm_hat.qaqc.aidb import AIDB_TABLES
>>> for country_code, country in continent.countries.items():
>>>    tables = continent.countries[country_code].aidb.tables
>>>    msg = f"{country_code} extra tables: {set(tables) - set(AIDB_TABLES)}"
>>>    msg += f" missing tables: {set(AIDB_TABLES) - set(tables)}"
>>>    print(msg)

"""

import pandas
from eu_cbm_hat.core.continent import continent
from eu_cbm_hat.qaqc.aidb import AIDB_TABLES


def read_aidb_table_all_countries(table_name):
    """Read the same AIDB table in all countries

    Concatenate the tables together and add a country column to identify where
    it comes from. Returns a data frame.

    Example use:

    >>> from eu_cbm_hat.qaqc.aidb_all_countries import read_aidb_table_all_countries
    >>> df = read_aidb_table_all_countries("disturbance_matrix_value")

    """
    df_all = pandas.DataFrame()
    print(f"Reading '{table_name}' in: ", end="")
    for country_code, country in continent.countries.items():
        print(f"{country_code} ", end="")
        df = country.aidb.db.read_df(table_name)
        df["country_code"] = country_code
        df_all = pandas.concat([df_all, df])
    print()
    df_all = df_all.reset_index(drop=True)
    return df_all


def count_duplicated_rows(country_code, table_name):
    """Count the number of duplicated rows in a table, then add this number to
    a summary data frame
    """
    
def compare_one_table_in_one_country_to_all_others(country_code, table_name):
    """Compare the number of identical rows in one country to all others

    Example:

    >>> from eu_cbm_hat.qaqc.aidb_all_countries import compare_one_table_in_one_country_to_all_others
    >>> compare_one_table_in_one_country_to_all_others("ZZ", "admin_boundary")
    >>> compare_one_table_in_one_country_to_all_others("ZZ", "disturbance_matrix_value")

    """
    df_all = read_aidb_table_all_countries(table_name)
    df_ref = df_all.loc[df_all["country_code"] == country_code].copy()
    df = pandas.DataFrame({country_code + "_nrow": [len(df_ref)]})
    for this_code in df_all["country_code"].unique():
        selector = df_all["country_code"].isin([country_code, this_code])
        df_comp = df_all.loc[selector].copy()
        df_comp.drop(columns="country_code", inplace=True)
        df[this_code] = df_comp.duplicated().sum()
    return df

def compare_one_country_to_all_others(country_code):
    """Count the number of identical rows between tables of a given country to all other countries

    >>> from eu_cbm_hat.qaqc.aidb_all_countries import compare_one_country_to_all_others
    >>> df_de = compare_one_country_to_all_others("DE")
    >>> df_it = compare_one_country_to_all_others("IT")

    """
    df_all = pandas.DataFrame()
    for table_name in AIDB_TABLES:
        print(table_name)
        df = compare_one_table_in_one_country_to_all_others(country_code, table_name)
        df["table"] = table_name
        cols = list(df.columns)
        cols = cols[-1:] + cols[:-1]
        df = df[cols]
        df_all = pandas.concat([df_all, df])
        print(df)
    return df_all

def compare_one_country_to_all_others_relative(country_code):
    """Provide the number of identical rows between tables of a given country
    to all other countries divided by the number of rows of the table """
    df = compare_one_country_to_all_others(country_code)
    nrow_col = country_code + "_nrow"
    country_cols = [col for col in df.columns if col != nrow_col and col != 'table']
    df[country_cols] = df[country_cols].div(df[nrow_col], axis=0)
    return df





