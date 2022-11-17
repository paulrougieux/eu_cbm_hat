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

# First party modules #

# Internal modules #

class InputYears:
    """
    This class will provide access to the years in all input files used by a runner

    Create a runner and list years used in its time dependent input data sets:

        >>> from eu_cbm_hat.core.continent import continent
        >>> r = continent.combos['special'].runners["LU"][-1]
        >>> input_years_dict = r.qaqc.input_years.dict
        >>> print(input_years_dict)
        >>> for key, value in input_years_dict.items():
        >>>     print(key, value, "\n")

    Display the max year for each data set:

        >>> {key: max(value) for key, value in input_years_dict.items()}

    Display the last year common to all input datasets:

        >>> print(r.qaqc.input_years.last_common())

    """

    def __init__(self, qaqc):
        # Default attributes #
        self.runner = qaqc.runner

    @property
    def dict(self):
        """Returns a dictionary with data set name as keys and
        lists of years as values.

        The output dictionary includes lists of year contained both
        in the input csv files
        and in the yaml definition of scenario combinations.
        """
        # Years in the harvest factor table
        harvest_cols = self.runner.silv.harvest.raw.columns
        harvest_years = (re.search(r"value_(\d+)", x) for x in harvest_cols)
        harvest_years = [int(m.group(1)) for m in harvest_years if m]

        # Years in the harvest tables
        irw_harvest_years = self.runner.harvest.irw.year.to_list()
        fw_harvest_years = self.runner.harvest.fw.year.to_list()

        # Years in the input events files for all activities combined
        timesteps = (self.runner.input_data["events"]
                     .sort_values(by=["step"])
                     .step.unique())
        events_years = self.runner.country.timestep_to_year(timesteps)

        # Place  the list of years in a dictionary
        dict1 = {"harvest_factor": harvest_years,
                 "irw_harvest": irw_harvest_years,
                 "fw_harvest": fw_harvest_years}

        # Load the lists of years used in the combo scenarios
        multi_year_input = ['events_templates',
                            'irw_frac_by_dist',
                            'harvest_factors',
                           ]
        combo_config = self.runner.combo.config
        dict2 = {"combo_" + m: list(combo_config[m].keys())
                 for m in multi_year_input}

        # Combine the two dictionaries
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
