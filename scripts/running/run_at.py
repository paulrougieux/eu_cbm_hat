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
combo   = continent.combos['historical']
runner  = combo.runners['AT'][-1]
country = runner.country

# Run the model
output = runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
# Input events sent to libcbm
events_input = runner.input_data["events"]
# Events stored in the output
events_output = runner.output.events
output_extras = runner.output.extras




