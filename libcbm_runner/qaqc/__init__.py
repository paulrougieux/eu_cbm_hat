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
from libcbm_runner.qaqc.input_years import InputYears
from libcbm_runner.qaqc.silviculture import SilvCheck
from libcbm_runner.qaqc.expected_provided import ExpectedProvided


class Qaqc:
    """
    Quality Assurance and Quality Control methods attached to a runner
    """

    def __init__(self, runner):
        # Default attributes #
        self.runner = runner

    @property
    def input_years(self):
        """Check input years"""
        return InputYears(self)

    @property
    def silv_check(self):
        """Check the consistency of silviculture input files"""
        return SilvCheck(self)

    @property
    def expected_provided(self):
        """Check harvest expected versus provided"""
        return ExpectedProvided(self)
