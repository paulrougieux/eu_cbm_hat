#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""
import warnings
import pandas
from pandas.errors import EmptyDataError

class ExpectedProvided:
    """
    Check harvest expected versus provided

    Usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['hat'].runners["ZZ"][-1]
        >>> # All events including input events and HAT events
        >>> runner.qaqc.expected_provided.events

    Comparison between harvest expected and provided with
    forest type and disturbance type as grouping variables:

        >>> runner.qaqc.expected_provided.by(index = ["forest_type", "disturbance_type"])

    Example with all classifiers as grouping variables:

        >>> clfrs = list(runner.country.orig_data.classif_list)
        >>> runner.qaqc.expected_provided.by(index = clfrs + ["disturbance_type"])
    """

    def __init__(self, qaqc):
        # Default attributes #
        self.runner = qaqc.runner

    @property
    def events(self):
        """All events including input events mostly natural disturbances and hat events
        """
        # Load input disturbances, available here after a model run
        events_input = self.runner.input_data["events"]
        # Add year
        events_input["year"] = self.runner.country.timestep_to_year(events_input["step"])

        # Note previous approach checked the path to check if there are HAT
        # related events but it doesn't work because if there are no HAT events
        # an empty file is written at that location
        # path_events_hat = self.runner.output.paths["events"]
        # if not path_events_hat.exists:
        try:
            # Load output disturbances related to HAT
            events_hat = self.runner.output["events"]
            events_hat["step"] = self.runner.country.year_to_timestep(events_hat["year"])
        except ValueError:
            path_events_hat = self.runner.output.paths["events"]
            warnings.warn(f"There are no events related to HAT in: \n{path_events_hat}")
            # In the absence of HAT events, return only the events_input
            return events_input

        # Concatenate the events files
        events_cols = ['status', 'forest_type', 'region', 'mgmt_type', 'mgmt_strategy',
                       'climate', 'con_broad', 'site_index', 'growth_period',
                       'using_id', 'sw_start', 'sw_end', 'hw_start', 'hw_end',
                       'min_since_last_dist', 'max_since_last_dist', 'last_dist_id',
                       'amount', 'dist_type_name', 'measurement_type', 'efficiency',
                       'sort_type', 'step', 'year']
        events = pandas.concat([events_input[events_cols], events_hat[events_cols]])
        return events

    def by(self, index):
        """Expected provided by the given classifiers and disturbance id

        :param list classif: list of classifiers to be used as grouping variables

        The diff only makes sense for disturbance of type M, that is why it is call diff_m.
        For disturbances expressed in terms of area, the amount requested is expressed in area
        and the amount provided in terms of tons of carbon to the products pool.

        Example use with only forest type and disturbance type:

            >>> runner.qaqc.expected_provided.by(index = ["forest_type", "disturbance_type"])

        Use all classifiers as grouping variables:

            >>> clfrs = list(runner.country.orig_data.classif_list)
            >>> runner.qaqc.expected_provided.by(index = clfrs + ["disturbance_type"])

        """
        # Load events and pool_flux data
        events = self.events.copy()
        events["disturbance_type"] = events["dist_type_name"]
        pool_flux = self.runner.output.pool_flux

        # Add "year" to the index
        index = index + ["year"]
        # Check that the index is present in both datasets
        missing_events_cols = set(index) - set(events.columns)
        missing_pf_cols = set(index) - set(pool_flux.columns)
        if missing_events_cols:
            msg = "The following columns are not present in the "
            raise ValueError(msg + f"events data \n{missing_events_cols}")
        if missing_pf_cols:
            raise ValueError(msg + f"pool_flux data \n{missing_pf_cols}")

        # Make sure "site_index" is of type character if present
        if "site_index" in index:
            events["site_index"] = events["site_index"].astype(str)

        # Aggregate the events table
        events["measurement_type"] = "amount_" + events["measurement_type"].str.lower()
        events_agg = (events
                      .groupby(index + ["measurement_type"])
                      .agg(amount = ("amount", "sum"))
                      .reset_index()
                      # Reshape measurement type in columns
                      .pivot(index = index, columns="measurement_type", values="amount")
                     )
        # Add start and end age information
        events_agg["sw_start_min"] = events.groupby(index)["sw_start"].agg("min")
        events_agg["sw_end_max"] = events.groupby(index)["sw_end"].agg("max")

        # Make index columns available for merging
        events_agg = events_agg.reset_index()

        # Aggregate the pool_flux table
        product_cols = ['softwood_merch_to_product', 'softwood_other_to_product',
                        'softwood_stem_snag_to_product', 'softwood_branch_snag_to_product',
                        'hardwood_merch_to_product', 'hardwood_other_to_product',
                        'hardwood_stem_snag_to_product', 'hardwood_branch_snag_to_product']
        flux_agg = pool_flux.groupby(index)[product_cols].agg("sum")
        flux_agg["sum_flux_to_product"] = flux_agg.sum(axis=1)
        # Add age information
        flux_agg["age_min"] = pool_flux.groupby(index)["age"].agg("min")
        flux_agg["age_max"] = pool_flux.groupby(index)["age"].agg("max")
        # Add the area
        flux_agg["area"] = pool_flux.groupby(index)["area"].agg("sum")
        flux_agg = flux_agg.reset_index()

        # Assert that there are no repetition in the index columns
        # It could be the case if additional variables have been added to the index
        assert len(events_agg.set_index(index).index.unique()) == len(events_agg)
        assert len(flux_agg.set_index(index).index.unique()) == len(flux_agg)

        # Merge tables on the index
        # Full outer merge so we don't loose lines
        df = events_agg.merge(flux_agg, how="outer", on=index)

        # Compute the diff
        df["diff_m"] = df["amount_m"] - df["sum_flux_to_product"]
        df["diff_a"] = df["amount_a"] - df["area"]

        # Reorder columns
        cols =  events_agg.columns.to_list()
        cols += ['area', 'diff_a', 'sum_flux_to_product', 'diff_m',
                 'age_min', 'age_max',
                 'softwood_merch_to_product',
                 'softwood_other_to_product', 'softwood_stem_snag_to_product',
                 'softwood_branch_snag_to_product', 'hardwood_merch_to_product',
                 'hardwood_other_to_product', 'hardwood_stem_snag_to_product',
                 'hardwood_branch_snag_to_product']
        assert set(df.columns).issubset(cols)

        return df[cols]
