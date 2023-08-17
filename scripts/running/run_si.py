#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A script to run Slovenia

Typically you would run this file from a command line like this:

     ipython3 -i -- ~/repos/eu_cbm/eu_cbm_hat/scripts/running/run_si.py

"""

from eu_cbm_hat.core.continent import continent


#############################################
# Declare which scenario combination to run #
#############################################
runner  = continent.combos['reference'].runners['SI'][-1]
runner.num_timesteps = 50

# Run the model
output = runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)



