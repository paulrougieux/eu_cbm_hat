#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair, Paul Rougieux and Viorel Blujdea.

JRC Biomass Project.
Unit D1 Bioeconomy.

A list of all combo classes.

Creating a new scenario combination only requires an update to the input files
and to a yaml file that specifies which scenarios will be used in the combo for
each input file:

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

    - In `eu_cbm_data/combos` Compile a new yaml file with the combination of
    scenarios desired. NB. A yaml file is a configuration file that can be
    edited with a text editor.

[Old instructions before July 2023] Creating a new scenario combination in the
hard coded way is not required anymore. It might still be useful in case you
need a scenario class that modifies the behaviour of the scenario combinations
beyond what the base runner or the dynamic runner can do. In that case, and in
that case only:

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
from eu_cbm_hat.combos.ia_2040 import IA_2040

from eu_cbm_hat import eu_cbm_data_pathlib

# Hard coded combo classes
combo_classes = [Reference,
                 IA_2040,
                ]
combo_classes_dict = dict(zip([s.short_name for s in combo_classes], combo_classes))

