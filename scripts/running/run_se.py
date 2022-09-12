#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A script to run Sweden.

Typically you would run this file from a command line like this:

     ipython3 -i -- ~/deploy/libcbm_runner/scripts/running/run_se.py
"""
from libcbm_runner.core.continent import continent
runner = continent.combos['hat'].runners['SE'][-1]
runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
