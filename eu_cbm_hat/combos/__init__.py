#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair, Paul Rougieux and Viorel Blujdea.

JRC Biomass Project.
Unit D1 Bioeconomy.

A list of all combo classes.
"""

# Built-in modules #

# First party modules #

# Internal modules #
from eu_cbm_hat.combos.reference               import Reference
from eu_cbm_hat.combos.hat               import Hat
from eu_cbm_hat.combos.skewccth          import Skewccth
from eu_cbm_hat.combos.special           import Special
from eu_cbm_hat.combos.historical        import Historical
from eu_cbm_hat.combos.harvest_test      import HarvestTest
from eu_cbm_hat.combos.potencia_baseline import Potencia_baseline
from eu_cbm_hat.combos.potencia_necp_bme_up100 import Potencia_necp_bme_up100
from eu_cbm_hat.combos.potencia_necp_bme_up200 import Potencia_necp_bme_up200
from eu_cbm_hat.combos.potencia_necp_bms_down50 import Potencia_necp_bms_down50
from eu_cbm_hat.combos.potencia_necp_bms_down90 import Potencia_necp_bms_down90
from eu_cbm_hat.combos.no_market_forcing import NoMarketForcing

###############################################################################
# List all combo classes to be loaded #
combo_classes = [Reference, 
                 Historical,
                 HarvestTest,
                 Hat,
                 NoMarketForcing,
                 Potencia_baseline,
                 Potencia_necp_bme_up100,
                 Potencia_necp_bme_up200,
                 Potencia_necp_bms_down50,
                 Potencia_necp_bms_down90,
                 Skewccth,
                 Special,
                 ]
