#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.

Check the silviculture input tables for inconsistencies

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner  = continent.combos['pikssp2_owc_max'].runners['AT'][-1]
    >>> runner.silv.check()

"""

# Built-in modules #

# Third party modules #
import pandas
import numpy as np

# First party modules #
from plumbing.cache import property_cached

# Internal modules #


def keep_clfrs_without_question_marks(df, classif_list):
    """Check if there are questions mark in a classifier column
    and return a list of index columns that:

    :param (df) data frame of silviculture data
    :param (classif_list) list of classifier columns to check
    :output (list) list of classif_list that don't contain "?"

    The function performs the following:

    - keep a column if it contains no question marks

    - return an error if a column contains a mixture of question marks and
      other values

    - remove the column from output list if there are only question marks in
      that column

    Example use (will only work after simulation start):

        >>> from eu_cbm_hat.info.silviculture import keep_clfrs_without_question_marks
        >>> from eu_cbm_hat.core.continent import continent
        >>> runner  = continent.combos['hat'].runners['ZZ'][-1]
        >>> irw_frac = runner.silv.irw_frac.get_year(2016)
        >>> clfrs = list(runner.country.orig_data.classif_list)
        >>> keep_clfrs_without_question_marks(irw_frac, clfrs)

    """
    # TODO: The error raised when there are a mixture of other values and
    # question marks should be raised in the BaseSilvInfo.conv_clfrs() method.
    # Why is this not the case for irw_frac and the events_template?
    # Answer: because they are converted to NA values
    output_classif_list = []
    for classif_name in classif_list:
        values = df[classif_name].unique()
        has_question_mark = "?" in values
        has_nan = pandas.isna(values).any()
        if len(values) > 1 and (has_question_mark or has_nan):
            # TODO: move this check to a method of base silv info
            # so that we can display self.csv_path in the error message
            # to facilitate locating the file
            msg = "Mixture of question marks (i.e. NA values) and other values"
            msg += f"not allowed in the `{classif_name}` column.\n"
            msg += f"Values: {values} (might be libcbm internal values or user values)"
            msg += f"The data frame contains the following columns:\n{df.columns}."
            raise ValueError(msg)
        # Remove classifiers that contain question marks or NA values only
        if has_question_mark or has_nan:
            continue
        # Add classifiers that don't contain question marks
        output_classif_list.append(classif_name)
    return output_classif_list

def keep_clfrs_without_question_marks_by_dist(df, classif_list):
    """Check if there are questions mark in a classifier column

    This is to by applied on an events table which has a disturbance_type
    column, in particular the events template.

    Similar to keep_clfrs_without_question_marks except that this also adds the
    disturance types in the index and that it returns a data frame. Mixture of
    ? and values in classifier columns is not allowed within the same group of
    rows belonging to the same disturbance.
    """
    # Reshape to long format
    df_long = df.melt(id_vars="disturbance_type",
                             value_vars=classif_list,
                             var_name="classifier",
                             value_name='value')
    # Replace `?` by NA values
    selector = df_long["value"] == "?"
    df_long.loc[selector, "value"] = np.nan
    # Aggregate unique classifier values, count and presence of NA
    df_agg = (
        df_long.groupby(["disturbance_type", "classifier"])
        .agg(
            unique_values=("value", lambda x: ', '.join(map(str, x.unique()))),
            count=("value", lambda x: len(x.unique())),
            has_na=("value", lambda x:  any(x.isna()))
        )
    )
    # Raise an error if there are a mix of classifier and NA values
    selector = (df_agg["count"] > 1) & df_agg["has_na"]
    if any(selector):
        msg = "Mix of NA (or `?`) and values in the following"
        msg += "classifier columns:\n"
        msg += f"{df_agg.loc[selector]}"
        raise ValueError(msg)
    return df_agg.reset_index()


###############################################################################
class Silviculture:
    """
    Access to silvicultural information pertaining to a given country.
    This includes the following files:

    * irw_frac_by_dist.csv
    * vol_to_mass_coefs.csv
    * events_templates.csv
    * harvest_factors.csv

    Each is accessed by its own corresponding attribute:

    * `silv.irw_frac`
    * `silv.coefs`
    * `silv.events`
    * `silv.harvest`

    Loading this information will fail if you call `df` before a simulation is
    launched, because we need the internal SIT classifier and disturbance
    mapping. Before the simulation starts, it is only possible to load the raw
    versions of the input data as such: `silv.harvest.raw`.

    Example usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner  = continent.combos['reference'].runners['LU'][-1]
        >>> runner.silv.harvest.raw
        >>> runner.silv.events.raw

    See also an example of how to get all events templates in all countries in
    post_processor/agg_combos.py 

    """

    def __init__(self, runner):
        # Default attributes #
        self.runner = runner
        # Shortcuts #
        self.country = self.runner.country

    @property_cached
    def irw_frac(self):
        return IRWFractions(self)

    @property_cached
    def dist_matrix_value(self):
        return DistMatrixValue(self)

    @property_cached
    def coefs(self):
        return VolToMassCoefs(self)

    @property_cached
    def events(self):
        return EventsTemplates(self)

    @property_cached
    def harvest(self):
        return HarvestFactors(self)

    def check(self):
        """Check the consistency of silviculture input files"""
        self.events.check()
        self.coefs.check()
        self.harvest.check()
        self.irw_frac.check()
        self.dist_matrix_value.check()


###############################################################################
class BaseSilvInfo:
    """
    A class that contains methods common to all silvicultural information
    files. You should inherit from this class.
    """

    def __init__(self, silv):
        # Default attributes #
        self.silv = silv
        # Shortcuts #
        self.runner = self.silv.runner
        self.country = self.silv.country
        self.combo = self.runner.combo
        self.code = self.country.iso2_code
        self.classif_list = self.country.orig_data.classif_list

    # ----------------------------- Properties --------------------------------#
    @property_cached
    def raw(self):
        """Data frame available in the input data"""
        return pandas.read_csv(self.csv_path, dtype={c: "str" for c in self.cols})

    @property_cached
    def cols(self):
        return self.classif_list + ["disturbance_type"]

    @property_cached
    def dup_cols(self):
        return ["scenario"] + self.cols

    def check(self):
        """Perform various checks on the silviculture input tables"""
        # Make a check of duplicated entries #
        self.duplication_check()
        # Optional extra checks #
        if hasattr(self, "extra_checks"):
            self.extra_checks()
        # Make a consistency check between dist_name and dist_id #
        if "dist_type_name" in self.raw.columns:
            self.consistency_check()

    @property_cached
    def df(self):
        """Data frame with disturbance IDs and classifiers IDs converted to the
        internal IDs

        Notes:

        - The use of `self.conv_dists` here is where the question marks "?" are
          converted to NAN values.

        - Classifier and disturbance values are different between user ids in
          the `raw` data frame and internal simulation ids in the `df` data
          frame. For example for industrial roundwood fractions:
        
        >>> runner.silv.irw_frac.raw["climate"].unique()
        >>> # array(['?', '35'], dtype=object)
        >>> runner.silv.irw_frac.df["climate"].unique()
        >>> # array([nan, 25.])
        >>> runner.silv.irw_frac.raw["forest_type"].unique()
        >>> # array(['DF', 'FS', 'OB', 'OC', 'PA', 'QR'], dtype=object)
        >>> runner.silv.irw_frac.df["forest_type"].unique()
        >>> # array([ 5,  6,  7,  8,  9, 10])
        """
        self.check()
        # Load #
        df = self.raw.copy()
        # Drop the names which are useless #
        if "dist_type_name" in self.raw.columns:
            df = df.drop(columns="dist_type_name")
        # Convert the disturbance IDs to the real internal IDs #
        df = self.conv_dists(df)
        # Convert the classifier IDs to the real internal IDs #
        df = self.conv_clfrs(df)
        # Return #
        return df

    # ------------------------------- Methods ---------------------------------#
    def conv_dists(self, df):
        """
        Convert the disturbance IDs such as `20` and `22` into their
        internal simulation ID numbers that are defined by SIT.
        """
        # Get the conversion mapping and invert it #
        id_to_id = self.runner.simulation.sit.disturbance_id_map
        id_to_id = {v: k for k, v in id_to_id.items()}
        # Check that all IDs can be converted to an internal ID
        cannot_convert = df["disturbance_type"].dropna().map(id_to_id).isna()
        if any(cannot_convert):
            msg = f"In the file {self.csv_path}, the disturbance type(s) "
            msg += f"{df['disturbance_type'][cannot_convert].unique()} "
            msg += "cannot be converted to an internal disturbance id, using the "
            msg += "following mapping dictionary."
            raise ValueError(msg, id_to_id)
        # Apply the mapping to the dataframe #
        df["disturbance_type"] = df["disturbance_type"].map(id_to_id)
        # Return #
        return df

    def conv_clfrs(self, df):
        """
        Convert the classifier values such as `PA` and `QA` into their
        internal simulation ID numbers that are defined by SIT.
        """
        # Get all the conversion mappings, for each classifier #
        all_maps = self.runner.simulation.sit.classifier_value_ids.items()

        # Apply each of them to the dataframe #
        for classif_name, str_to_id in all_maps:
            if classif_name not in df.columns:
                continue

            # Handle question marks
            values = df[classif_name].unique()
            if len(values) == 1 and values[0] == "?":
                continue
            # if len(values) > 1 and "?" in values:
            #     msg = "Mixture of question marks and other values"
            #     msg += f"not allowed in %s, column {classif_name}"
            #     raise ValueError(msg % self)

            # Convert classifiers to their internal id
            df[classif_name] = df[classif_name].map(str_to_id)

        # Return #
        return df

    def consistency_check(self):
        # Get mapping dictionary from ID to full description #
        id_to_name = self.country.orig_data["disturbance_types"]
        id_to_name = dict(
            zip(id_to_name["dist_type_name"], id_to_name["dist_desc_input"])
        )
        # Compare #
        names = self.raw["disturbance_type"].map(id_to_name)
        orig = self.raw["dist_type_name"]
        comp = orig == names
        # Raise exception #
        if not all(comp):
            msg = "Names don't match IDs in '%s'.\n" % self.csv_path
            msg += "Names derived from the IDs:\n"
            msg += str(names[~comp])
            msg += "\n\nNames in the user file:\n"
            msg += str(orig[~comp])
            raise Exception(msg)

    def duplication_check(self):
        # What columns are we going to check duplication on #
        cols = self.dup_cols
        # Get duplicated rows #
        dups = self.raw.duplicated(subset=cols, keep=False)
        # Assert #
        if any(dups):
            msg = "There are duplicated entries in the file '%s'."
            msg += "\nThe duplicated rows are shown below:\n\n"
            msg += str(self.raw.loc[dups, cols])
            raise Exception(msg % self.csv_path)

    def get_year(self, year):
        # Case number 1: there is only a single scenario specified #
        if isinstance(self.choices, str):
            scenario = self.choices
        # Case number 2: the scenarios picked vary according to the year #
        else:
            scenario = self.choices[year]
        # Retrieve by query #
        df = self.df.query("scenario == '%s'" % scenario)
        # Drop the scenario column #
        df = df.drop(columns="scenario")
        # Check there is data left #
        assert not df.empty
        # Return #
        return df


###############################################################################
class IRWFractions(BaseSilvInfo):
    """
    Gives access the industrial roundwood fractions, per disturbance type,
    for the current simulation run.
    """

    # TODO: add a property that provides the merge index to be used with
    # irw_frac depending on which columns are returned by Note that
    # self.runner.silv.irw_frac.raw has a scenario column And that we want to
    # perform the check for one scenario only. As different scenarios might
    # heve different ways to deal with the classifiers. We could use
    # runner.silv.irw_frac.df for the check but it then would not be available
    # for the post_processor which also requires irw_frac.
    #
    # For lack of a better way, We can add a scenario specific
    # irw_frac.raw_df_scenario Which can then be used to return the merge index
    # to be used with irw_frac for that particular scenario and that mere_index
    # would be available both for users of irw_frac.df and irw_frac.raw

    @property
    def choices(self):
        """Choices made for `irw` fraction in the current combo."""
        return self.combo.config["irw_frac_by_dist"]

    @property
    def csv_path(self):
        return self.country.orig_data.paths.irw_csv


###############################################################################
class VolToMassCoefs(BaseSilvInfo):
    """
    Gives access to the coefficients that enable the conversion from
    wood volume to wood mass.
    """

    @property
    def csv_path(self):
        return self.country.orig_data.paths.vol_to_mass_csv

    @property
    def cols(self):
        return ["forest_type"]

    @property
    def dup_cols(self):
        return self.cols

    @property_cached
    def df(self):
        # Make a check of duplicated entries #
        self.duplication_check()
        # Load #
        df = self.raw.copy()
        # Convert the classifier IDs to the real internal IDs #
        df = self.conv_clfrs(df)
        # Return #
        return df


###############################################################################
class EventsTemplates(BaseSilvInfo):
    """
    Gives access to the dynamic events that have to be generated to
    satisfy the harvest.
    """

    @property
    def choices(self):
        """Choices made for the events templates in the current combo."""
        return self.combo.config["events_templates"]

    @property
    def csv_path(self):
        return self.country.orig_data.paths.events_templates

    @property
    def dup_cols(self):
        return (
        list(self.country.orig_data.classif_list)
            + ["scenario", "sw_start", "sw_end", "hw_start", "hw_end"]
            + ["last_dist_id"]
        )

    def extra_checks(self):
        # Guarantee no difference between sw_start and hw_start #
        assert all(self.raw["sw_start"] == self.raw["hw_start"])
        # Guarantee no difference between sw_end and hw_end #
        assert all(self.raw["sw_end"] == self.raw["hw_end"])
        # Guarantee we don't use max_since_last_dist #
        assert all(self.raw["max_since_last_dist"] == -1)


###############################################################################
class HarvestFactors(BaseSilvInfo):
    """
    Gives access to the data in the file `harvest_factors.csv`.
    """

    @property
    def choices(self):
        """Choices made for the harvest factors in the current combo."""
        return self.combo.config["harvest_factors"]

    @property
    def csv_path(self):
        return self.country.orig_data.paths.harvest_factors

    @property
    def cols(self):
        cols = ["forest_type", "mgmt_type", "disturbance_type", "con_broad"]
        cols = cols + ["product_created", "silv_practice"]
        return cols

    @property
    def join_cols(self):
        """Keep only columns that are not empty as join columns"""
        join_cols = []
        for col in self.cols:
            if not any(self.df[col].isna()):
                join_cols.append(col)
        return join_cols

    def extra_checks(self):
        """Check the raw data for empty columns, proportions that sum to one.

        Check the raw data frame so it an be checked at the beginning of the simulation.
        """
        index = ["scenario", "product_created"]
        cols = list(set(self.cols) - set(["product_created"]))
        df_check = self.raw.groupby(index)[cols].agg(lambda x: len(x.isna().unique()))
        for col in cols:
            if any(df_check[col] > 1):
                df_wrong = df_check[df_check[col] > 1]
                msg = "For a given scenario and a given product, "
                msg += "A join column can either be completely empty or full, "
                msg += "but it cannot be incomplete i.e. "
                msg += "with some missing values and some values."
                msg += f"Check column: {col} in scenario {df_wrong.index.to_list()}"
                raise ValueError(msg)
        # Check that the skew factors sum to one by scenario and product group
        df_long = self.raw.melt(id_vars=self.cols + ["scenario"])
        index = ["scenario", "product_created", "variable"]
        df_long["value_sum"] = df_long.groupby(index)["value"].transform("sum")
        df_long_irw = df_long.query("product_created=='irw_and_fw'")
        selector = np.isclose(df_long_irw["value_sum"], 1, atol=1e-08)
        if not all(selector):
            msg = "The following skew factors do not sum to one"
            raise ValueError(msg, df_long_irw.query("value_sum !=1"))


class DistMatrixValue(BaseSilvInfo):
    """
    Gives access the disturbance matrix value table if defined
    """

    @property
    def choices(self):
        """Choices made for in the current combo."""
        return self.combo.config["disturbance_matrix_value"]

    @property
    def csv_path(self):
        return self.country.orig_data.paths.disturbance_matrix_value

    @property_cached
    def use_default_aidb(self):
        """Check whether the default aidb should be used or not"""
        # Cases in which the default AIDB will be used
        # If a disturbance matrix is not defined in the yaml file, use the default AIDB
        if "disturbance_matrix_value" not in self.runner.combo.config.keys():
            return True
        # If it's defined as "default_aidb", use the default AIDB
        if self.runner.combo.config["disturbance_matrix_value"] == "default_aidb":
            return True
        return False

    @property_cached
    def df(self):
        """Disturbance matrix values"""
        df = self.raw.copy()
        df = df.loc[df["scenario"] == self.choices]
        df.drop(columns="scenario", inplace=True)
        return df

    def check(self):
        """Check sink pools sum to one"""
        # Don't perform the test if not required by the scenario combo
        if self.use_default_aidb:
            return
        index = ["disturbance_matrix_id", "source_pool_id"]
        prop_sum = self.df.groupby(index)["proportion"].agg("sum")
        if not all(np.isclose(prop_sum, 1)):
            check_df = prop_sum.reset_index()
            check_df = check_df.query("proportion<1-1e-6 or proportion>1+1e-6")
            msg = "Some of the sink pool id do not sum to one "
            msg += "in the disturbance matrix update file \n"
            msg += f"{self.csv_path}\n:"
            msg += f"{check_df}"
            raise ValueError(msg)
