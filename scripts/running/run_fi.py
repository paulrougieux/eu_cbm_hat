#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A script to run Finland.

Typically you would run this file from a command line like this:

     ipython3 -i -- ~/repos/eu_cbm/eu_cbm_hat/scripts/running/run_fi.py

"""

from eu_cbm_hat.core.continent import continent
runner = continent.combos['reference'].runners['FI'][-1]
runner.country.base_year = 2021
runner.num_timesteps = 2050 - runner.country.inventory_start_year
runner.run(True, True, True)
