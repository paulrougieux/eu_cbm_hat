#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

import pandas

class ExpectedProvided:
    """
    Check harvest expected versus provided

    Usage:

        >>> from libcbm_runner.core.continent import continent
        >>> runner = continent.combos['hat'].runners["ZZ"][-1]
        >>> # All events including input events and HAT events
        >>> runner.qaqc.expected_provided.events

    Comparison between harvest expected and provided by dist id

        >>> runner.qaqc.expected_provided.by_ft_dist
        >>> # TODO: Comparison between harvest expected and provided
        >>> # by all classifiers

    """

    def __init__(self, qaqc):
        # Default attributes #
        self.runner = qaqc.runner

    @property
    def events(self):
        """All events including input events mostly natural disturbances and hat events
        """
        # After a model run input disturbances
        events_input = self.runner.input_data["events"]
        # Add year
        events_input["year"] = self.runner.country.timestep_to_year(events_input["step"])

        # Output disturbances related to HAT
        events_hat = self.runner.output["events"]
        events_hat["step"] = self.runner.country.year_to_timestep(events_hat["year"])

        # Concatenate the events files
        events_cols = ['status', 'forest_type', 'region', 'mgmt_type', 'mgmt_strategy',
                       'climate', 'con_broad', 'site_index', 'growth_period',
                       'using_id', 'sw_start', 'sw_end', 'hw_start', 'hw_end',
                       'min_since_last_dist', 'max_since_last_dist', 'last_dist_id',
                       'amount', 'dist_type_name', 'efficiency', 'sort_type',
                       'step', 'year']
        events = pandas.concat([events_input[events_cols], events_hat[events_cols]])
        return events

    @property
    def by_ft_and_dist(self):
        """Expected provided by disturbance id

        """
        events = self.events
        events["disturbance_type"] = events["dist_type_name"]
        pool_flux = self.runner.output.pool_flux
        #########################
        # Aggregate both tables #
        #########################
        index = ["forest_type", "dist_type_name", "year"]
        # Todo keep age range in the events side
        # Aggregate min age max age on the pool_flux side
        events_agg = events.groupby(index + ["sw_start","sw_end"])

        # Sum all these columns with movements to the product pool
#            softwood_merch_to_product	softwood_other_to_product	softwood_stem_snag_to_product	softwood_branch_snag_to_product	hardwood_merch_to_product	hardwood_other_to_product	hardwood_stem_snag_to_product	hardwood_branch_snag_to_product

        # Merge tables on the index

        # Compute the diff

        # Full merge require so we don't loose lines



