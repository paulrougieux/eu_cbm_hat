""" Run the PIK FAIR scenario output of the GFPMX economic model"""

from p_tqdm import p_umap
from eu_cbm_hat.core.continent import continent

def run_country(args):
    """Run a single country, only based on the code as input"""
    country_code, last_year, combo_name = args
    runner = continent.combos[combo_name].runners[country_code][-1]
    runner.num_timesteps = last_year - runner.country.inventory_start_year
    try:
        runner.run()
    except Exception as e:
        print(e)

LAST_YEAR = 2070
COMBO_NAME = "pikfair"
# Select all countries
list_of_countries = list(continent.combos[COMBO_NAME].runners.keys())
# Select only some countries if needed
# list_of_countries = list(continent.combos[combo_name].runners.keys())[16:-1]
runner_items = [(k, LAST_YEAR, COMBO_NAME) for k in list_of_countries]
result = p_umap(run_country, runner_items, num_cpus=4)
