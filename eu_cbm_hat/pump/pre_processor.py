#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #
import shutil
import tempfile

# Third party modules #
import pandas

# First party modules #
from plumbing.databases.sqlite_database import SQLiteDatabase

# Internal modules #
from eu_cbm_hat.pump.long_or_wide import events_wide_to_long


###############################################################################
class PreProcessor(object):
    """
    This class will update the input data of a runner based on a set of rules.

    - Load the modified disturbance matrix from
      `eu_cbm/eu_cbm_data/countries/AT/silv/` for the scenario defined in
      pikssp2_owc_max and change the AIDB for the given disturbance matrix
      rows:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner  = continent.combos['pikssp2_owc_max'].runners['AT'][-1]
        >>> runner.silv.check()
        >>> runner.silv.dist_matrix_value.df
        >>> runner.pre_processor.copy_and_change_aidb()

    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        self.runner = parent
        self.country = parent.country
        # Shortcuts #
        self.input = self.runner.input_data

    def __repr__(self):
        return '%s object code "%s"' % (self.__class__, self.runner.short_name)

    # --------------------------- Special Methods -----------------------------#
    def __call__(self):
        # Message #
        self.parent.log.info("Pre-processing input data.")
        # Check empty lines in all CSV inputs #
        for csv_path in self.all_csv:
            self.raise_empty_lines(csv_path)
        # Reshape the events file #
        self.reshape_events()
        # Check there are no negative timesteps #
        self.raise_bad_timestep()
        # Copy the AIDB
        # In case the scenario combination changes the disturbance matrix
        self.copy_and_change_aidb()

    # ----------------------------- Properties --------------------------------#
    @property
    def all_csv(self):
        """Get all CSV inputs in a list."""
        return [
            item.path_obj
            for item in self.input.paths._paths
            if item.path_obj.extension == "csv"
        ]

    # ------------------------------- Methods ---------------------------------#
    @staticmethod
    def raise_empty_lines(csv_path):
        """
        Loads one CSV files and raise an exception if there are any empty
        lines.
        """
        # Load from disk #
        try:
            df = pandas.read_csv(str(csv_path))
        # If the file is empty we can skip it #
        except pandas.errors.EmptyDataError:
            return
        # Get empty lines #
        empty_lines = df.isnull().all(1)
        # Check if there are any #
        if not any(empty_lines):
            return
        # Warn #
        msg = "The file '%s' has %i empty lines."
        raise Exception(msg % (csv_path, empty_lines.sum()))

    def reshape_events(self, debug=False):
        """Reshape the events file from the wide to the long format."""
        # The events file #
        path = self.input.paths.events
        # Optionally make a copy #
        if debug:
            path.copy(path.prefix_path + "_wide.csv")
        # Load it as a dataframe #
        wide = pandas.read_csv(str(path))
        # Reshape it #
        long = events_wide_to_long(self.country, wide)
        # Write to disk #
        long.to_csv(str(path), index=False)

    def raise_bad_timestep(self):
        """
        Raise an Exception if there are timesteps with a value below zero.
        """
        # Path to the file we want to check #
        path = str(self.input.paths.events)
        # Load from disk #
        try:
            df = pandas.read_csv(path)
        # If the file is empty we can skip it #
        except pandas.errors.EmptyDataError:
            return
        # Get negative values #
        negative_values = df["step"] < 0
        # Check if there are any #
        if not any(negative_values):
            return
        # Message #
        msg = (
            "The file '%s' has %i negative values for the timestep column."
            " This means you are attempting to apply disturbances to a"
            " year that is anterior to the inventory start year configured."
        )
        # Raise #
        raise Exception(msg % (path, negative_values.sum()))

    def copy_and_change_aidb(self):
        """Copy the AIDB and modify the disturbance matrix

        We deliberately keep both the copy and change operations in the same
        method. Because we want to be sure that the change happens only on a
        copied AIDB. Not on the reference one.
        """
        # Cases for which the default AIDB should be used
        if self.runner.silv.dist_matrix_value.use_default_aidb:
            return

        # If a disturbance matrix is defined in the yaml file
        # Check that the chosen scenario exists in disturbance_matrix_value.csv
        # Raise an error if not


        # Load the reference disturbance matrix values and the new values
        dist_matrix_table_name = "disturbance_matrix_value"
        dm = self.runner.country.aidb.db.read_df(dist_matrix_table_name)
        dm_new = self.runner.silv.dist_matrix_value.df

        # Find matching rows in the default AIDB
        ids = ["disturbance_matrix_id", "source_pool_id", "sink_pool_id"]
        df_match = dm.merge(dm_new[ids + ["proportion"]], on=ids, how="right")

        # Remove those combinations of disturbance_matrix_id and source_pool_id
        # from the table
        df_match_id = df_match.value_counts(
            ["disturbance_matrix_id", "source_pool_id"]
        ).reset_index()
        df = dm.merge(df_match_id, how="left", indicator=True)
        # Check the indicator name didn't change
        assert any(df["_merge"].str.contains("left_only"))
        selector = df["_merge"] == "left_only"
        df = df.loc[selector].copy()
        df = df[ids + ["proportion"]]

        # Add the updated disturbance matrix values and reorder
        df = pandas.concat([df, dm_new[ids + ["proportion"]]])
        df = df.sort_values(ids)
        # Drop the first index because it contains ids from both
        # the old and new data frame
        df.reset_index(drop=True, inplace=True)
        df.reset_index(inplace=True)

        # Copy the default AIDB to a temporary location. This has been added
        # because the /eos large file system Doesn't handle database writes
        # very well on JRC's BDAP computing cluster.
        combo_name = self.runner.combo.short_name
        orig_file = self.runner.country.aidb.default_aidb_path
        self.parent.log.info("AIDB %s" % orig_file)
        aidb_file_name = f"aidb_{combo_name}.db"
        with tempfile.TemporaryDirectory() as tmpdirname:
            temp_file = tmpdirname + "/" + aidb_file_name
            self.parent.log.info("Temporarily copied to %s" % temp_file)
            shutil.copy(orig_file, temp_file)
            temp_db = SQLiteDatabase(temp_file)
            # Write to the temporary AIDB
            temp_db.write_df(df, dist_matrix_table_name)
            # Change path to the modified AIDB
            self.runner.country.aidb.change_path(combo_name=combo_name)
            # Copy the temporary AIDB to the new path
            dest_file = self.runner.country.aidb.paths.aidb
            shutil.copy(temp_file, dest_file)
            self.parent.log.info("Copied to new AIDB %s" % dest_file)

        msg = "The disturbance matrix has been changed according to "
        msg += "silv/disturbance_matrix_value.csv"
        self.parent.log.info(msg)
