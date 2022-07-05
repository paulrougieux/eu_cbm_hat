#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.

A list of all combo classes.
"""

# Built-in modules #

# First party modules #

# Internal modules #
from libcbm_runner.combos.hat               import Hat
from libcbm_runner.combos.special           import Special
from libcbm_runner.combos.historical        import Historical
from libcbm_runner.combos.harvest_test      import HarvestTest
from libcbm_runner.combos.potencia_baseline import Potencia_baseline
from libcbm_runner.combos.potencia_necp_bme_up100 import Potencia_necp_bme_up100
from libcbm_runner.combos.potencia_necp_bme_up200 import Potencia_necp_bme_up200
from libcbm_runner.combos.potencia_necp_bms_down50 import Potencia_necp_bms_down50
from libcbm_runner.combos.potencia_necp_bms_down90 import Potencia_necp_bms_down90

###############################################################################
# List all combo classes to be loaded #
combo_classes = [Historical, Special, HarvestTest, Hat, 
                 Potencia_baseline, 
                 Potencia_necp_bme_up100,
                 Potencia_necp_bme_up200,
                 Potencia_necp_bms_down50,
                 Potencia_necp_bms_down90
                 ]
