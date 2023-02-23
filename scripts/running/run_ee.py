#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A script to run Estonia

Run this file from a command line

     ipython3 -i -- ~/repos/eu_cbm/eu_cbm_hat/scripts/running/run_ee.py

"""

from eu_cbm_hat.core.continent import continent


runner = continent.combos['reference'].runners['EE'][-1]
# Step 11 is 2020, check with
# print(runner.country.year_to_timestep(2020))
runner.num_timesteps = 11
runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
