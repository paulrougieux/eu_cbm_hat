#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# Third party modules #
import numpy

# First party modules #

# Internal modules #

def check_question_marks(df, df_name, classifiers):
    """Raise an error if classifiers have a mixture of
    question mark and no question mark"""
    for classif_name in classifiers:
        values = df[classif_name].unique().tolist()
        if len(values) > 1 and "?" in values:
            msg =  "Mixture of question marks and other values "
            msg += f"not allowed in {df_name}.\n"
            msg += f"The unique values of the {classif_name} column are: {values}"
            raise ValueError(msg)

class SilvCheck:
    """
    Check the consistency of silviculture input files

    Whenever possible tests are based on raw input files available before the run
    has started, when SIT is not available yet.

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['special'].runners["ZZ"][-1]

    Check that fuel wood disturbances don't generate industrial roundwood:

        >>> runner.qaqc.silv_check.fw_doesnt_create_irw()

    The check is based on the `events_templates`and `irw_frac_by_dist`

        >>> runner.silv.events.raw
        >>> runner.silv.irw_frac.raw

    List disturbance ids used in the input data "activities" directory and in
    the "silv" events_templates.csv.

        >>> # Fetch the data from the country folder. This call is only
        >>> # necessary in case the runner has not been run yet.
        >>> runner.input_data()
        >>> runner.qaqc.silv_check.dist_ids_activities()
        >>> runner.qaqc.silv_check.dist_ids_silv_events_templates()

    Check classifiers with question marks

        >>> runner.qaqc.silv_check.check_classifier_with_question_marks()

    """
    def __init__(self, qaqc):
        # Default attributes #
        self.runner = qaqc.runner
        # Disturbance mapping
        assoc_df = self.runner.country.associations.df
        self.assoc = assoc_df.loc[assoc_df["category"] == "MapDisturbanceType"]

    def fw_doesnt_create_irw(self):
        """Check that fuel wood only disturbances don't generate industrial roundwood"""
        index = ["disturbance_type", "product_created"]
        prod_by_dist = (self.runner.silv.events.raw
                        .set_index(index).index
                        .unique().to_frame(index=False))
        fw_by_dist = prod_by_dist[prod_by_dist["product_created"] == "fw_only"]

        # Keep industrial roundwood fractions only for the fuel wood disturbances
        df = (self.runner.silv.irw_frac.raw
              .merge(fw_by_dist, on="disturbance_type", how="inner"))

        # Exclude identifier columns to find the name of the value columns
        cols = self.runner.silv.irw_frac.raw
        identifiers =  self.runner.silv.irw_frac.dup_cols
        identifiers += ["dist_type_name"]
        val_cols = list(set(cols) - set(identifiers))
        # assert value columns are zero
        agg_cols = {col: "sum" for col in val_cols}
        df_agg = df.groupby(["disturbance_type", "product_created"])
        df_agg = df_agg.agg(agg_cols)
        if not numpy.allclose(df_agg.sum(), 0):
            msg = "fuel wood only disturbances "
            msg += "should not generate industrial roundwood:\n"
            msg += f"{df_agg}"
            raise ValueError(msg)

    def dist_ids_activities(self):
        """List disturbance ids used in the input data "activities" folder"""
        df = self.runner.input_data["events"]
        df = df.value_counts("dist_type_name")
        df = df.reset_index(name="number_of_rows")
        return df

    def dist_ids_silv_events_templates(self):
        """List disturbance ids used in the "silv" events_templates.csv"""
        df = self.runner.silv.events.raw
        df = df.value_counts(["disturbance_type", "dist_type_name"])
        df = df.reset_index(name="number_of_rows")
        return df

    def check_classifier_with_question_marks(self):
        """Check the input tables for classifiers with question marks"""
        clfrs = list(self.runner.country.orig_data.classif_list)
        irw_frac = self.runner.country.orig_data.load("irw_frac")
        check_question_marks(irw_frac, "irw_frac", clfrs)
        # Do not check the input events
        # input_events = self.runner.input_data["events"]
        # check_question_marks(input_events, "input events from the activities folder", clfrs)

    def cc_th_and_dist_matrix_proportion(self):
        """Check that clear cut disturbances are the ones that remove most of the merch biomass

        Rank fluxes to merchantable pool to check clear cut disturbances
        are actually the ones with the highest proportion in the dist matrix

        ! requires SIT

        Example use :

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['hat'].runners['ZZ'][-1]
            >>> # Run at least one present time step so that SIT is available
            >>> runner.num_timesteps = runner.country.base_year - runner.country.inventory_start_year + 1
            >>> runner.run()
            >>> runner.qaqc.silv_check.cc_th_and_dist_matrix_proportion()

        """
        cols = ['user_name', 'silv_practice', 'hardwood_merch_prod_prop', 'softwood_merch_prod_prop']
        df = self.runner.fluxes.df.sort_values("hardwood_merch_prod_prop", ascending=False)[cols]
        return df

    def check_cc_th_and_dist_matrix_proportion(self, threshold=0.79):
        merch_cols = ['hardwood_merch_prod_prop', 'softwood_merch_prod_prop']
        df = self.runner.cc_th_and_dist_matrix_proportion()
        assert all(df.loc[df["silv_practice"]=="th"][merch_cols] < threshold)
        assert all(df.loc[df["silv_practice"]=="cc"][merch_cols] > threshold)




