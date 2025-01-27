#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A script to run a country based on the ISO2 code.

Typically you would run this file from a command line like this:

     ipython3 -i -- ~/repos/eu_cbm/eu_cbm_hat/scripts/running/run_country.py COMBO_NAME ISO2_CODE [FINAL_YEAR]

Where:
- COMBO_NAME is the name of the combo in continent.combos.
- ISO2_CODE is the ISO 3166-1 alpha-2 country code.
- FINAL_YEAR is the optional final year to run until, default is 2050.

Example:

    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference AT 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference BE 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference BG 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference CZ 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference DE 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference DK 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference EE 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference ES 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference FI 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference FR 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference GR 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference HR 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference HU 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference IE 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference IT 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference LT 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference LU 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference LV 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference NL 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference PL 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference PT 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference RO 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference SE 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference SI 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference SK 2035
    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference ZZ 2035

The final year parameter is optional. It will default to 2050, so you can use :

    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/running/run_country.py reference AT

"""

import sys

from eu_cbm_hat.core.continent import continent

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) < 3:
        print("Usage: run_country.py <COMBO_NAME> <ISO2_COUNTRY_CODE> [FINAL_YEAR]")
        sys.exit(1)
    
    combo_name = sys.argv[1]
    iso2_code = sys.argv[2].upper()  # Convert to uppercase for consistency
    
    # Default final year is 2050 unless specified
    final_year = 2050
    if len(sys.argv) > 3:
        try:
            final_year = int(sys.argv[3])
        except ValueError:
            print("Error: Final year must be an integer.")
            sys.exit(1)

    # Retrieve the runner for the specified country
    try:
        runner = continent.combos[combo_name].runners[iso2_code][-1]
    except KeyError as e:
        if 'combo_name' in str(e):
            print(f"Error: '{combo_name}' is not a valid or supported combo name.")
        else:
            print(f"Error: '{iso2_code}' is not a valid or supported ISO2 country code for combo '{combo_name}'.")
        sys.exit(1)

    # Set up the runner
    runner.country.base_year = 2021
    runner.num_timesteps = final_year - runner.country.inventory_start_year
    
    # Run the simulation
    runner.run(True, True, True)

