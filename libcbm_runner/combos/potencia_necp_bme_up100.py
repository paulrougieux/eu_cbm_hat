# -*- coding: utf-8 -*-
"""
Created on Mon Jul  4 14:18:06 2022

@author: blujd
"""

# Built-in modules #

# First party modules #
from plumbing.cache import property_cached

# Internal modules #
from libcbm_runner.combos.base_combo import Combination
from libcbm_runner.cbm.dynamic       import DynamicRunner

###############################################################################
class Potencia_necp_bme_up100(Combination):
    """
    A Combination used for the Harvest Allocation Tool (HAT).
    """

    short_name = 'potencia_necp_bme_up100'

    @property_cached
    def runners(self):
        """
        A dictionary of country codes as keys with a list of runners as
        values.
        """
        return {c.iso2_code: [DynamicRunner(self, c, 0)]
                for c in self.continent}