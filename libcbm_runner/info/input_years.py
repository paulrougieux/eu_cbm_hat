#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #
import re

# Third party modules #
import pandas

# First party modules #
from plumbing.cache       import property_cached

# Internal modules #

###############################################################################
class InputYears:
    """
    This class will provide access to the years in all input files used by a runner

    Example use:

        >>> from libcbm_runner.core.continent import continent
        >>> r = continent.combos['special'].runners["LU"][-1]
        >>> print(r.input_years.dict)

    Display the max year for each data set:

        >>> {key: max(value) for key, value in r.input_years.dict.items()}

    Display the maximum year of the shortest time span input data:

        >>> print(r.input_years.last_common())


    """

    def __init__(self, runner):
        # Default attributes #
        self.runner = runner

    @property
    def dict(self):
        """Returns a dictionary with data set name as keys and lists of years as values"""
        # Years in the harvest table
        # Note we wanted to load with this method
        # harvest_cols = self.runner.silv.harvest.df.columns.to_list()
        # But it fails with
        # *** AttributeError: 'DynamicSimulation' object has no attribute 'sit'
        # Because sit doesn't exist when called by
        # libcbm_runner/info/silviculture.py(111)df()
        #     110         # Convert the disturbance IDs to the real internal IDs #
        # --> 111         df = self.conv_dists(df)
        harvest_cols = pandas.read_csv(self.runner.silv.harvest.csv_path).columns
        harvest_years = (re.search(r"value_(\d+)", x) for x in harvest_cols)
        harvest_years = [int(m.group(1)) for m in harvest_years if m]

        # Years in the demand tables
        irw_demand_years = self.runner.demand.irw.year.to_list()
        fw_demand_years = self.runner.demand.fw.year.to_list()
        dict1 = {"harvest_factor": harvest_years,
                 "irw_demand": irw_demand_years,
                 "fw_demand": fw_demand_years}

        # Years as in the combo scenarios
        multi_year_input = ['events_templates',
                            'irw_frac_by_dist',
                            'harvest_factors',
                            #'demand' # Why is it a data frame? The others are dicts
                            # type(self.runner.combo.config["demand"])
                           ]
        combo_config = self.runner.combo.config
        dict2 = {"combo_" + m: list(combo_config[m].keys()) for m in multi_year_input}

        # Merge the two dicts
        dict1.update(dict2)
        return dict1

    def check_all_present(self):
        """Check that the time series are complete for each year in the input datasets.

        If a time series has a year missing, an error should be raised."""

    def last_common(self):
        """Returns the last common year available in all data sets


        """
        # Max value for each input data
        max_years = {key: max(value) for key, value in self.dict.items()}
        return  min(max_years.values())
