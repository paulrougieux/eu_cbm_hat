"""Modify the growth multiplier for the purses of taking climate differences into account

TODO:

    - load the input file in a dedicated place of the runner similar to what's
    done for the events_template in info/silviculture.py

    - 

Example usage: run LU

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['rcp6'].runners['LU'][-1]
    >>> runner.num_timesteps = 2070 - runner.country.inventory_start_year
    >>> # Check availability of the raw growth multiplier table
    >>> runner.silv.growth_multiplier.raw
    >>> output = runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
    



Inside libcbm's C++ code from the `libcbm_c` repository, we can see where the
growth multiplier is applied inside `src/cbm/cbmbiomassdynamics.cpp`.

There are two multiplications by growth multipliers:

1. one multiplication in GetTotalBiomassIncrement
    - total_increment.SWM = SWM_inc * sw_multiplier;
    - total_increment.HWM = HWM_inc * hw_multiplier;

2. another multiplication in GetGrowthMatrix

```
Biomass inc = GetTotalBiomassIncrement(biomass,
    agBiomassIncrement,
    growthMult.SoftwoodMultiplier * growth_multiplier,
    growthMult.HardwoodMultiplier * growth_multiplier);
```

What is the difference between `growthMult.SoftwoodMultiplier`,
`growth_multiplier` and `sw_multiplier` ?

1. growthMult.SoftwoodMultiplier is a Species and disturbance-specific
adjustment factor retrieved from parameter tables via
`_Parameters.GetGrowthMultipliers(lastDisturbancetype,
growth_multiplier_step)`. It is based on `lastDisturbancetype (e.g., fire,
harvest, insect damage)` and `growth_multiplier_step (likely time since
disturbance)`. It represents how the specific disturbance history affects
softwood growth rates.

2. `growth_multiplier` is an overall growth scaling factor (for climate/site
productivity) passed as a parameter through the cbm_vars.state data frame. It represents
broad environmental conditions affecting all growth such as Climate conditions
(temperature, precipitation), Site quality, CO₂ fertilization effects.

3. `sw_multiplier` is calculated as the product of the above two.
`sw_multiplier = growthMult.SoftwoodMultiplier * growth_multiplier`. It
represents the Total growth adjustment combining both disturbance effects AND
environmental conditions.

"""
from eu_cbm_hat.cbm.cbm_vars_to_df import cbm_vars_to_df

class Growth_Modifier:
    """Modify the growth multiplier for the purses of taking climate
    differences into account.
    """


    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name

    def growth_multiplier_table(self):
        """Growth multiplier table scenario defined in the combo field
        growth_multiplier
        """
        df = self.runner.silv.growth_multiplier.df

    def update_state(self, timestep, cbm_vars):
        """Update the cbm_vars.state with new growth multiplier values

        This method updates the state data frame of cbm vars at the **beginning
        of the time step**, before growth and disturbances are applied.

        The CBM variables used here are based on cbm_vars before the time step.
        This is in contrast to the CBM variables used in `dynamics_func` of
        cbm/dynamic.py. The `stands` data frame in `dynamics_func` is a
        concatenation of the classifiers, parameters, inventory, state, flux
        and pools data frames from `end_vars` which is a simulated result
        of the stand state at the **end of the time step**.
        """
        # TODO: check if there are growth multipliers value for this time step
        # If not skip and return cbm_vars as is.
        cbm_vars_classif_df = cbm_vars_to_df(cbm_vars,"classifiers")
        cbm_vars_state_df = cbm_vars_to_df(cbm_vars,"state")
        state = pandas.concat([cbm_vars_classif_df, cbm_vars_state_df], axis=1)
        breakpoint()
        # state_df["growth_multiplier"] = update_state_growth_multiplier(cbm_vars, timestep)
        # Keep only the columns in state df
        cbm_vars.state =  dataframe.from_pandas(state_df)
        return cbm_vars

