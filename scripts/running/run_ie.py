"""Run Ireland"""
from eu_cbm_hat.core.continent import continent
runner = continent.combos['reference'].runners['IE'][-1]
runner.num_timesteps = 2050 - runner.country.inventory_start_year
output = runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

