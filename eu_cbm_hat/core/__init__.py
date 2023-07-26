"""The core components of the model are: `eu_cbm_hat.core.country`,
`eu_cbm_hat.core.continent` and `eu_cbm_hat.core.runner`. A runner is
associated to one country and runs the model for a specific combination of
input files called a scenario combination. The continent object contains a
dictionary of all scenario combinations documented at  `eu_cbm_hat.combos`. The
continent and scenario combination objects can be used together to create a
runner object for the test country `ZZ` as follows:

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['hat'].runners['ZZ'][-1]

The function below is a convenient function that makes it possible to run all
countries inside a combination of scenarios. If one country fails to run, the
error will be kept in its log files but the other countries will continue to
run.

"""

from p_tqdm import p_umap, t_map
from eu_cbm_hat.core.continent import continent

def run_country(args):
    """Run a single country, only based on the code as input.
    This function should only be used by run_combo()"""
    combo_name, last_year, country_code = args
    runner = continent.combos[combo_name].runners[country_code][-1]
    runner.num_timesteps = last_year - runner.country.inventory_start_year
    print(runner)
    try:
        # The argument interrupt_on_error=False deals with errors happening
        # during the actual libcbm run
        runner.run(verbose=True, interrupt_on_error=False)
    # Catching general exception in case there are other errors in the input
    # data preparation or pre processor
    except Exception as general_error:
        print(general_error)

def run_combo(combo_name:str, last_year:int, countries:list=None, parallel=True):
    """Run a scenario combination
    If the list of countries is not specified, run all countries.

    Usage:

        >>> from eu_cbm_hat.core import run_combo
        >>> # run the selected list of countries
        >>> run_combo('reference', 2050, ['IT','ZZ'])
        >>> # run all countries with parallel cpus
        >>> run_combo('reference', 2070)
        >>> # Run sequentially (not in parallel)
        >>> run_combo('reference', 2070, parallel=False)

    """
    if countries is None:
        countries = continent.combos[combo_name].runners.keys()
    runner_items = [(combo_name, last_year, k) for k in countries]
    if parallel:
        result = p_umap(run_country, runner_items, num_cpus=10)
    else:
        result = t_map(run_country, runner_items)
    return result
