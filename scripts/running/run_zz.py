#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.

A script to run the imaginary `ZZ` country to test the pipeline.

Typically you would run this file from a command line like this:

     ipython3 -i -- ~/deploy/libcbm_runner/scripts/running/run_zz.py
"""

# Built-in modules #

# Third party modules #

# First party modules #

# Internal modules #
from libcbm_runner.core.continent import continent

combo  = continent.combos['hat']
runner = combo.runners['ZZ'][-1]
# runner.country.base_year = 2020
runner.num_timesteps = 30
runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

# Input events sent to libcbm
events_input = runner.input_data["events"]
# Events stored in the output
events_output = runner.output.events
output_extras = runner.output.extras



# cols = ['climate', 'con_broad', 'disturbance_type', 'product_created', 'dist_interval_bias']
# cols += ['irw_vol', 'fw_vol', 'irw_pot', 'fw_pot']
# #['irw_norm']
#  df_irw.loc[salv, cols] 
#  salv = df["last_dist_id"] != -1
       

# (Pdb) timestep
# 18
#     climate  con_broad  disturbance_type product_created dist_interval_bias       irw_vol       fw_vol       irw_pot       fw_pot
# 32       23         28                26      irw_and_fw                  1  12969.952174  1441.105797  12969.952174  1441.105797
# 37       25         28                26      irw_and_fw                  1  12967.619034  1440.846559  12967.619034  1440.846559

