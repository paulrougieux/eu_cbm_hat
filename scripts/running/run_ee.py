#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A script to run Estonia

Typically you would run this file from a command line like this:

     ipython3 -i -- ~/repos/eu_cbm/eu_cbm_hat/scripts/running/run_ee.py

"""

from eu_cbm_hat.core.continent import continent


#############################################
# Declare which scenario combination to run #
#############################################
combo   = continent.combos['reference']
runner  = combo.runners['EE'][-1]
runner.num_timesteps = 2050 -  runner.country.inventory_start_year

# Run the model
output = runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)



