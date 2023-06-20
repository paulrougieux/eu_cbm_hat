#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair, Paul Rougieux and Viorel Blujdea.

JRC Biomass Project.
Unit D1 Bioeconomy.

A list of all combo classes.

Creating a new scenario combination:


- In `eu_cbm_data`

    - Add data specific to the “new_scenario” in each relevant input file. The
    assumptions have to be identified as “new_scenario” on the column
    “scenario” across all files. 

    - For example, in case of a new scenario for afforestation, specific
    records must be added in: events.csv, growth_curves.csv, inventory.csv,
    transitions.csv. in

        ...\eu_cbm_data\countries\ZZ\activities\afforestation.

    - Also, information specific to the new assumptions must be added in the
    following files contained in the other directory (as explained above in
    Lower level of the EU-CBM-HAT: country specific inputs):

        ...\eu_cbm_data\countries\ZZ\common - on the new disturbance
        types;
        ...\eu_cbm_data\countries\ZZ\config - for the changes in the AIDB
        and association file;
        ...\eu_cbm_data\countries\ZZ\silv – description of the silvicultural
        practices and wood use.

    - Add data on IRW and FW demands in the new directory. irw_demand.csv,
    fw_demands.csv, rw_demands.csv in the directory
    ...\eu_cbm_data\demand\new_scenario.

    - In `eu_cbm_data/combos` Compile a new yaml file with the combination of
    scenarios desired. NB. A yaml file is a configuration file that can be
    edited with a text editor.

- In `eu_cbm_hat`

    - Create a new file in ...\eu_cbm_hat\combos: new_scenario.py. Create a new
    class and import the corresponding module in the file __init__.py in
    ...\eu_cbm_hat\combos of the eu_cbm_hat Add the new class
    [...new_scenario...] 

    - and import the new module [...new_...] in __init__.py, by paying
    attention to consistency of names, e.g., class name: “New_scenarios”,
    short_name: “new_scenarios”.

"""

# Built-in modules #

# First party modules #

# Internal modules #
from eu_cbm_hat.combos.reference         import Reference
from eu_cbm_hat.combos.no_market_forcing import NoMarketForcing
from eu_cbm_hat.combos.skewfcth          import Skewfcth
from eu_cbm_hat.combos.reference_crf              import Reference_crf
# from eu_cbm_hat.combos.half_harvest               import Half_harvest
# from eu_cbm_hat.combos.plus_20_harvest            import Plus_20_harvest       
from eu_cbm_hat.combos.potencia_baseline import Potencia_baseline
from eu_cbm_hat.combos.potencia_necp_bme_up100 import Potencia_necp_bme_up100
from eu_cbm_hat.combos.potencia_necp_bme_up200 import Potencia_necp_bme_up200
from eu_cbm_hat.combos.potencia_necp_bms_down50 import Potencia_necp_bms_down50
from eu_cbm_hat.combos.potencia_necp_bms_down90 import Potencia_necp_bms_down90
from eu_cbm_hat.combos.ia_2040 import IA_2040
from eu_cbm_hat.combos.pikbau import PIKBau
from eu_cbm_hat.combos.pikfair import PIKFair

###############################################################################
# List all combo classes to be loaded #
combo_classes = [Reference,
                 NoMarketForcing,
                 Reference_crf,
                 Skewfcth,
                 Potencia_baseline,
#                  Half_harvest,
#                  Plus_20_harvest,
                 Potencia_necp_bme_up100,
                 Potencia_necp_bme_up200,
                 Potencia_necp_bms_down50,
                 Potencia_necp_bms_down90,
                 IA_2040,
                 PIKBau,
                 PIKFair,
                 ]
