#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A script to run Sweden.

Typically you would run this file from a command line like this:

     ipython3 -i -- ~/deploy/eu_cbm/eu_cbm_hat/scripts/running/run_se.py
"""

from eu_cbm_hat.core.continent import continent
runner = continent.combos['reference'].runners['SE'][-1]
runner.num_timesteps = 50

# Run the model
runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

# Check expected provided
runner.qaqc.expected_provided.by(index=["forest_type", "disturbance_type"])
