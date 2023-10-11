""" Run the EU_CBM_HAT scenario combinations

Usage:

    cd ~/repos/eu_cbm/eu_cbm_hat/scripts/running/
    # or on BDAP
    cd $HOME/eu_cbm/eu_cbm_hat/scripts/running/
    ipython -i run_scenario_combo.py -- --combo_name reference --last_year 2050
    ipython -i run_scenario_combo.py -- --combo_name pikssp2 --last_year 2070
    ipython -i run_scenario_combo.py -- --combo_name pikfair --last_year 2070
    ipython -i run_scenario_combo.py -- --combo_name pikssp2_fel1 --last_year 2070
    ipython -i run_scenario_combo.py -- --combo_name pikfair_fel1 --last_year 2070
    # Only run a few countries
    ipython -i run_scenario_combo.py -- --combo_name pikssp2 --last_year 2070 --countries LU CZ
    ipython -i run_scenario_combo.py -- --combo_name pikssp2 --last_year 2070 --countries IT

The version of p_umap in eu_cbm_hat/combos/base_combo.py Combination.__call__()
method was using a function that takes a list of runner objects as one its
argument. The problem was that `p_umap(run_country, runner_items, num_cpus=4)`
lead to `TypeError: cannot pickle 'sqlite3.Connection' object`. This is because
SQLite connections cannot be pickled and sent to subprocesses. Instead of
passing a runner as a function argument, the solution is to pass only the
country code as a function argument and have the function create the runner
object inside the sub-process directly.

"""

import argparse
from p_tqdm import p_umap
from eu_cbm_hat.core.continent import continent


def run_country(args):
    """Run a single country, only based on the code as input"""
    combo_name, last_year, country_code = args
    runner = continent.combos[combo_name].runners[country_code][-1]
    runner.num_timesteps = last_year - runner.country.inventory_start_year
    try:
        runner.run()
    except Exception as e:
        print(e)


parser = argparse.ArgumentParser(description="Run the EU_CBM_HAT scenario combinations")
parser.add_argument(
    "--combo_name", type=str, help="Name of the scenario combo to be run"
)
parser.add_argument("--last_year", type=int, help="Last year to be simulated")
parser.add_argument(
    "--countries", nargs="+", default=None, help="List of country ISO2 codes"
)

shell_args = parser.parse_args()

LAST_YEAR = shell_args.last_year
COMBO_NAME = shell_args.combo_name
COUNTRIES = shell_args.countries

# If no countries are specified, run for all countries
if COUNTRIES is None:
    COUNTRIES = list(continent.combos[COMBO_NAME].runners.keys())

runner_items = [(COMBO_NAME, LAST_YEAR, k) for k in COUNTRIES]
result = p_umap(run_country, runner_items, num_cpus=4)
