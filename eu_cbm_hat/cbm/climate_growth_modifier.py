"""Modify the growth multiplier for the purpose of taking climate differences into account

Example usage:

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['reference_cable_pop'].runners['EE'][-1]
    >>> runner.num_timesteps = 2070 - runner.country.inventory_start_year
    >>> # Check availability of the raw growth multiplier table
    >>> runner.clim_adjust.df
    >>> output = runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['reference'].runners['LU'][-1]
    >>> runner.num_timesteps = 2070 - runner.country.inventory_start_year
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

Source of the growth modifier inside libcbm_c/src/cbm/cbmdefaultparameters.cpp

            int disturbanceType = t.GetValue(row, "disturbance_type_id");
            int forest_type_id = t.GetValue(row, "forest_type_id");
            int time_step = t.GetValue(row, "time_step");

"""

import warnings
import pandas
from eu_cbm_hat.cbm.cbm_vars_to_df import cbm_vars_to_df
from libcbm.storage import dataframe


class GrowthModifier:
    """Modify the growth multiplier for the purses of taking climate
    differences into account.
    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name

    def update_state(self, year, cbm_vars):
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
        # Get growth multiplier input data
        clim_adjust_df = self.runner.clim_adjust.df
        # Check if there are growth multipliers values for this year.
        # If not skip and return cbm_vars as is.
        if year not in clim_adjust_df["year"].unique():
            return cbm_vars
        cbm_vars_classif_df = cbm_vars_to_df(cbm_vars, "classifiers")
        cbm_vars_state_df = cbm_vars_to_df(cbm_vars, "state")
        state = pandas.concat([cbm_vars_classif_df, cbm_vars_state_df], axis=1)
        # Keep only the current year
        index = ["climate", "con_broad"]
        selector = clim_adjust_df["year"] == year
        df = clim_adjust_df.loc[selector, index + ["ratio"]].copy()
        # Rename ratio to growth_multiplier
        df.rename(columns={"ratio": "growth_multiplier"}, inplace=True)
        # Convert classifiers IDs from the SIT standard to the user standard
        state = self.parent.conv_clfrs(state)

        # Merge climate adjustment with state keep old columns as "old" and new
        # column as growth_multiplier
        state = state.merge(df, on=index, suffixes=("_old", ""), how="left")

        # Debug message with the new and old values
        msg = "Old growth multiplier values from CBM"
        msg += f"{state['growth_multiplier_old'].unique()}"
        self.runner.log.debug(msg)
        msg = "New growth multiplier values from runner.clim_adjust.df"
        msg += f"{state['growth_multiplier'].unique()}"
        self.runner.log.debug(msg)

        # Check that the combination of Climate units and con_broad present in
        # CBM are alsoe present in the NPP input file. If not raise a warning
        # and keep growth_multiplier unchanged.
        selector = state["growth_multiplier"].isna()
        if any(selector):
            df_missing = state.loc[
                selector, index + ["growth_multiplier"]
            ].value_counts()
            msg = "Some combinations of climate units and con_broad "
            msg += "are note present int he NPP climate modification "
            msg += "input file:\n"
            msg += f"{df_missing}"
            warnings.warn(msg)

        # Keep only the columns in cbm_vars_state_df
        cols_to_keep = cbm_vars_state_df.columns.to_list()
        state_updated = state[cols_to_keep].copy()

        # Check state_updated and original cbm_vars_state_df are the same
        # except for the change in growth multiplier i.e. no reordering of rows.
        state_updated_check = state_updated.copy()
        state_updated_check["growth_multiplier"] = state['growth_multiplier_old']
        if not cbm_vars_state_df.equals(state_updated_check):
            msg = "State and state updated do not have the same values. Differences:\n"
            diff = state_updated_check - state_updated
            msg += f"{diff}"
            raise ValueError(msg)

        # Write the state back into cbm_vars
        cbm_vars.state = dataframe.from_pandas(state_updated)
        return cbm_vars
