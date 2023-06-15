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
from eu_cbm_hat.combos.reference         import Reference
from eu_cbm_hat.combos.no_market_forcing import NoMarketForcing
from eu_cbm_hat.combos.skewfcth          import Skewfcth
from eu_cbm_hat.combos.reference_crf              import Reference_crf
from eu_cbm_hat.combos.half_harvest               import Half_harvest
from eu_cbm_hat.combos.plus_20_harvest            import Plus_20_harvest       
from eu_cbm_hat.combos.potencia_baseline import Potencia_baseline
from eu_cbm_hat.combos.potencia_necp_bme_up100 import Potencia_necp_bme_up100
from eu_cbm_hat.combos.potencia_necp_bme_up200 import Potencia_necp_bme_up200
from eu_cbm_hat.combos.potencia_necp_bms_down50 import Potencia_necp_bms_down50
from eu_cbm_hat.combos.potencia_necp_bms_down90 import Potencia_necp_bms_down90
from eu_cbm_hat.combos.ia_2040 import IA_2040

###############################################################################
# List all combo classes to be loaded #
combo_classes = [Reference,
                 NoMarketForcing,
                 Reference_crf,
                 Skewfcth,
                 Potencia_baseline,
                 Half_harvest,
                 Plus_20_harvest,
                 Potencia_necp_bme_up100,
                 Potencia_necp_bme_up200,
                 Potencia_necp_bms_down50,
                 Potencia_necp_bms_down90,
                 IA_2040
                 ]
