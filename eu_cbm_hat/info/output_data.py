#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #
import pickle

# Third party modules #
import pandas
from pyarrow import csv

# First party modules #
from autopaths.auto_paths import AutoPaths
from plumbing.cache import property_cached

# Internal modules #
from eu_cbm_hat.info.internal_data import InternalData

###############################################################################
class OutputData(InternalData):
    """
    This class will provide access to the output data of a Runner
    as several pandas data frames.

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos["reference"].runners["PL"][-1]
        >>> # Read the compressed csv file into a data frame
        >>> runner.output["pools"]
        >>> # Wall time: 3.38 s measured with %time
        >>> # Use the load() method to get classifiers and year columns
        >>> runner.output.load("pools")
        >>> # Wall time: 8.92 s
        >>> runner.output["flux"]
        >>> runner.output.load("flux"))
    """

    # The file "results.parquet" is called "results" because
    # calling it flux_pool.parquet would return an auto_paths error:
    #   Exception: Found several paths matching 'flux'
    # We want to avoid this error so that existing notebooks remain compatible.
    all_paths = """
    /output/csv/
    /output/csv/values.pickle
    /output/csv/area.csv.gz
    /output/csv/classifiers.csv.gz
    /output/csv/flux.csv.gz
    /output/csv/parameters.csv.gz
    /output/csv/pools.csv.gz
    /output/csv/state.csv.gz
    /output/csv/extras.csv.gz
    /output/csv/events.csv.gz
    /output/csv/results.parquet
    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        self.runner = parent
        self.sim    = self.runner.simulation
        # Directories #
        self.paths = AutoPaths(self.parent.data_dir, self.all_paths)

    #----------------------------- Properties --------------------------------#
    @property_cached
    def extras(self):
        """
        This is a dataframe that will contain custom reporting information
        that is filled in by the `dynamics_fun` of a running simulation.
        It has one row for each year of the simulation run and contains
        information about harvest volumes.
        """
        return pandas.DataFrame()

    @property_cached
    def events(self):
        """
        This is a dataframe that will contain custom reporting information
        that is filled in by the `dynamics_fun` of a running simulation.
        It contains the dynamic events generated by H.A.T. for every timestep
        of a simulation.
        """
        return pandas.DataFrame()

    #--------------------------- Special Methods -----------------------------#
    def __getitem__(self, item):
        """Read any CSV or pickle file with the passed name."""
        # Find the path #
        path = self.paths[item]
        # If it is a CSV #
        if '.csv' in path.name:
            return csv.read_csv(str(path)).to_pandas()
        # If it is a python pickle file #
        with path.open('rb') as handle: return pickle.load(handle)

    def __setitem__(self, item, df):
        """
        Record a dataframe or python object to disk using the file with the
        passed name.
        """
        # Find the path #
        path = self.paths[item]
        # If it is a DataFrame #
        if isinstance(df, pandas.DataFrame):
            # Convert disturbance ids from the model internal id to the input id
            dist_map = self.sim.sit.disturbance_id_map
            dist_map[0] = "0" # Keep the non disturbance fluxes
            for dist_col in ["disturbance_type", "last_disturbance_type"]:
                if dist_col in df.columns:
                    df[dist_col] = df[dist_col].map(dist_map)
            return df.to_csv(str(path),
                             index        = False,
                             float_format = '%g',
                             compression  = 'gzip')
        # If it is a python object #
        with path.open('wb') as handle: return pickle.dump(df, handle)

    #------------------------------- Methods ---------------------------------#
    def save(self, verbose=False):
        """
        Save all the information of interest from the simulation to disk before
        the whole cbm object is removed from memory.
        """
        # Message #
        self.parent.log.info("Saving final simulations results to disk.")
        # The classifier values #
        self['values']      = self.sim.sit.classifier_value_ids
        # All the tables that are within the SimpleNamespace of `sim.results` #
        tables = ['area', 'classifiers', 'flux', 'parameters',
                  'pools', 'state']
        # Loop and save them #
        for table in tables:
            if verbose:
                self.parent.log.info("Writing and compressing `%s`." % table)
            self[table] = self.runner.internal[table]
            if verbose:
                self.parent.timer.print_elapsed()
        # Save extra information to csv files using the above __setitem__() method
        self['extras']      = self.extras.reset_index()
        self['events']      = self.events
        # Merge all pools and fluxes and save them to a parquet file
        result = self.runner.internal
        classifiers = self.classif_df
        classifiers["year"] = self.runner.country.timestep_to_year(classifiers["timestep"])
        index = ['identifier', 'timestep']
        df = (result['parameters']
              .merge(result['flux'], 'left', on = index)
              .merge(result['state'], 'left', on = index)
              .merge(result['pools'], 'left', on = index)
              .merge(classifiers, 'left', on = index)
             )
        # Keep the internal id for debugging purposes
        df["disturbance_type_internal"] = df["disturbance_type"]
        # Convert the disturbance IDs from their internal simulation IDs that
        # are defined by SIT into the user defined equivalent string.
        id_to_id = self.runner.simulation.sit.disturbance_id_map
        df["disturbance_type"] = df["disturbance_type"].map(id_to_id)
        df["disturbance_type"] = df["disturbance_type"].astype(int)
        # Add age class information
        df['age_class'] = df.age // 10 + 1
        df['age_class'] = 'AGEID' + df.age_class.astype(str)
        # Write to a parquet file
        df.to_parquet(self.paths["results"])
        # Timer #
        self.parent.timer.print_elapsed()

    @property_cached
    def pool_flux(self):
        """Load the main result data frame where the following tables have been
        merged: area, params, flux, state, pools

        Example usage:

            from eu_cbm_hat.core.continent import continent
            runner = continent.combos['hat'].runners['ZZ'][-1]
            pool_flux = runner.output.pool_flux

        This loads faster than the following equivalent code

            params = runner.output.load('parameters', with_clfrs=False)
            flux = runner.output.load('flux', with_clfrs=False)
            state = runner.output.load('state', with_clfrs=False)
            pools = runner.output.load('pools', with_clfrs=False)
            classifiers = runner.output.classif_df
            classifiers["year"] = runner.output.runner.country.timestep_to_year(classifiers["timestep"])
            index = ['identifier', 'year']
            df = (params
                  .merge(flux, 'left', on = index)
                  .merge(state, 'left', on = index)
                  .merge(classifiers, 'left', on = index)
                  .merge(pools, 'left', on = index)
                 )
            df.equals(pool_flux)

        """
        return pandas.read_parquet(self.paths["results"])
