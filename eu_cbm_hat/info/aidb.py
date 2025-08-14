#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #
import shutil

# First party modules #
from autopaths.dir_path   import DirectoryPath
from autopaths.auto_paths import AutoPaths
from plumbing.cache       import property_cached

# Internal modules #
from eu_cbm_hat.constants import eu_cbm_aidb_dir


###############################################################################
class AIDB(object):
    """
    This class will provide access to the archive index database
    also called 'cbm_defaults' in libcbm.
    It is an SQLite3 database that weighs approx 18 MiB.

    To symlink the single test database to all countries do the following:

        >>> from eu_cbm_hat.core.continent import continent
        >>> for country in continent: country.aidb.symlink_single_aidb()

    To symlink every AIDB from every countries do the following:

        >>> from eu_cbm_hat.core.continent import continent
        >>> for country in continent: country.aidb.symlink_all_aidb()

    Display the name of available tables in the AIDB for a given country

        >>> from eu_cbm_hat.core.continent import continent
        >>> continent.countries["LU"].aidb.db.tables

    Display the length of each table in a given country as a data frame:

        >>> import pandas as pd
        >>> from eu_cbm_hat.core.continent import continent
        >>> country_code = "LU"
        >>> for table in continent.countries[country_code].aidb.db.tables:
        >>>     table = str(table).replace("b'","").replace("'","")
        >>>     print(table, len(continent.countries[country_code].aidb.db.read_df(table)))

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
        >>>    for table in continent.countries[country_code].aidb.db.tables:
        >>>        table = str(table).replace("b'","").replace("'","")
        >>>        df[table] = len(continent.countries[country_code].aidb.db.read_df(table))
        >>>    print(df)
        >>>    df_all = pd.concat([df_all, df]).reset_index(drop=True)
        >>> print(df_all)
        >>> print("Unique values")
        >>> for col in df_all.columns:
        ...     print(col, df_all[col].unique())
        >>> df_all.to_csv("/tmp/aidb_table_lengths.csv")

    """

    all_paths = """
    /config/aidb.db
    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        # Directories #
        self.paths = AutoPaths(self.parent.data_dir, self.all_paths)
        # Keep the default paths in this argument
        self.default_aidb_path = self.paths.aidb
        # The AIDB path may be changed in some scenario combinations
        # Path to the database in a separate repository #
        self.repo_file = eu_cbm_aidb_dir + 'countries/' + self.parent.iso2_code \
                         + '/aidb.db'

    def __bool__(self):
        return bool(self.paths.aidb)

    #----------------------------- Properties --------------------------------#
    @property_cached
    def db(self):
        """
        Returns a `plumbing.databases.sqlite_database.SQLiteDatabase` object
        useful for reading and modifying entries and tables.

        In addition one can also read/write to the AIDB files easily:

            >>> df = country.aidb.db.read_df('species')

        To overwrite a table with a df:

            >>> country.aidb.db.write_df(df, 'species', index=False)
            >>> country.aidb.db.write_df(df, 'species')

        List all tables:

            db.tables

        Read a table:

            db.read_df("disturbance_matrix_value")

        """
        from plumbing.databases.sqlite_database import SQLiteDatabase
        return SQLiteDatabase(self.paths.aidb)

    @property
    def vol_conv_to_biomass(self):
        """Volume to biomass conversion factors

        Example:

            >>>> from eu_cbm_hat.core.continent import continent
            >>>> r = continent.combos['hat'].runners['ZZ'][-1]
            >>>> r.country.aidb.vol_conv_to_biomass

        """
        #load table with factors
        vol_to_biomass_factors = (self.db.read_df('vol_to_bio_factor')
                                  .drop_duplicates(subset=['a', 'b'], keep='last'))
        #load the parameteres a and b for species from aidb
        vol_to_bio_f = vol_to_biomass_factors.rename(columns = {'id':'vol_to_bio_factor_id'})
        vol_to_bio_sp = (self.db.read_df('vol_to_bio_species')
                         .drop_duplicates(subset=['species_id'], keep='last')
                        )
        # add species ids to a and b values
        vol_to_bio_sp_f = vol_to_bio_sp.merge(vol_to_bio_f, how = 'inner')
        species_name = self.db.read_df('species_tr')
        sp_name = species_name.rename(columns = {'name': 'cbm_forest_name'})
        # get the final database on spatial_units_ids and species or forest types
        vol_to_bio_species_factors = (vol_to_bio_sp_f
                                      .merge(sp_name, how = 'inner', on = 'species_id')
                                      .drop(columns = 'vol_to_bio_factor_id')
                                      .rename(columns = {'species_name':'forest_type'})                                                                )
        #select only the relevant columns
        colns = ['cbm_forest_name','spatial_unit_id', 'species_id', 'a', 'b']
        cbm_biom = vol_to_bio_species_factors[colns]
        return cbm_biom


    #------------------------------- Methods ---------------------------------#
    def symlink_single_aidb(self):
        """
        During development, and for testing purposes we have a single AIDB
        that all countries can share and that is found in another repository.
        """
        # The path to the SQLite3 file #
        source = DirectoryPath(eu_cbm_aidb_dir + 'aidb.db')
        # Check it exists #
        try:
            assert source
        except AssertionError:
            msg = "The sqlite3 database at '%s' does not seems to exist."
            raise AssertionError(msg % source)
        # Symlink #
        destin = self.paths.aidb
        source.link_to(destin)

    def symlink_all_aidb(self):
        """In production, every country has its own AIDB."""
        # Check the AIDB exists #
        try:
            assert self.repo_file
        except AssertionError:
            msg = "The sqlite3 database at '%s' does not seems to exist."
            raise AssertionError(msg % self.repo_file)
        # The destination #
        destin = self.paths.aidb
        # Remove destination if it already exists #
        destin.remove()
        # Symlink #
        self.repo_file.link_to(destin)
        # Return #
        return 'Symlink success for ' + self.parent.iso2_code + '.'

    def change_path(self, combo_name):
        """Change the path to the AIDB

        pump/pre_preocessor can copy a database in order to change some
        parameters (such as disturbance matrix values) while keeping the
        reference database unchanged. The copy happens in a scenario
        combination, therefore the copied AIDB gets the combo_name appended to
        its name.
        """
        self.all_paths = f"/config/aidb_{combo_name}.db"
        self.paths = AutoPaths(self.parent.data_dir, self.all_paths)
