"""Modify the growth multiplier for the purses of taking climate differences into account

TODO:

    - load the input file in a dedicated place of the runner similar to what's
    done for the events_template in info/silviculture.py

    - 

Example usage: run LU

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['reference'].runners['LU'][-1]
    >>> runner.num_timesteps = 2070 - runner.country.inventory_start_year
    >>> output = runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

"""


class Growth_Modifier:
    """Modify the growth multiplier for the purses of taking climate
    differences into account.
    """


    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name

    def update_state(self, timestep, cbm_vars):
        """Update the state data frame with a new growth multiplier"""
        state_df = cbm_vars.state.to_pandas()
        breakpoint()
        state_df["growth_multiplier"] = update_state_growth_multiplier(cbm_vars, timestep)
        cbm_vars.state =  dataframe.from_pandas(state_df)
        return cbm_vars



