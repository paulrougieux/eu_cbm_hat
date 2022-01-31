#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.

A script to run Luxembourg.

Typically you would run this file from a command line like this:

     ipython3 -i -- ~/deploy/libcbm_runner/scripts/running/run_lu.py

"""

from libcbm_runner.core.continent import continent


#############################################
# Declare which scenario combination to run #
#############################################
# Scenario combination defined in the yaml file 
# `~/repos/libcbm_data/combos/harvest_test.yaml`
# Scenario itself is defined as code in 
# `~/repos/libcbm_runner/libcbm_runner/combos/harvest_test.py`
combo   = continent.combos['hat']
runner  = combo.runners['LU'][-1]
runner.num_timesteps = 25

# Run the model
output = runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

# Input events sent to libcbm
events_input = runner.input_data["events"]
# Events stored in the output
events_output = runner.output.events
output_extras = runner.output.extras


