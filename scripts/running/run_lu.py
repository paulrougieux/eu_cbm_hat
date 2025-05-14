#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.

A script to run Luxembourg.

Typically you would run this file from a command line like this:

     ipython3 -i -- ~/eu_cbm/eu_cbm_hat/scripts/running/run_lu.py

"""

from eu_cbm_hat.core.continent import continent

#############################################
# Declare which scenario combination to run #
#############################################
# Scenario combination defined in yaml files
# `~/repos/eu_cbm_data/combos/harvest_test.yaml`
runner = continent.combos['reference'].runners['LU'][-1]
runner.num_timesteps = 2070 - runner.country.inventory_start_year
# Run the model
output = runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

# Input events sent to libcbm
events_input = runner.input_data["events"]
# Events stored in the output
events_output = runner.output.events
output_extras = runner.output.extras


