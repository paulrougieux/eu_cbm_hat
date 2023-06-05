#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.

A script to run Austria.

Typically you would run this file from a command line like this:

     ipython3 -i -- ~/deploy/eu_cbm/eu_cbm_hat/scripts/running/run_fr.py

"""

from eu_cbm_hat.core.continent import continent
runner  = continent.combos['reference'].runners['FR'][-1]
runner.num_timesteps = 25

# Run the model
output = runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)





