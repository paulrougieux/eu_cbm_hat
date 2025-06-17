"""Climate adjustment variables based on modelled NPP values


The growth multiplier can have different meanings:

combined_multiplier = growth_multiplier_disturbance  X  climate_adjustement

| combined_multiplier | growth_multiplier_disturbance | climate_adjustement |
|-------------------  |-------------------------------|---------------------|
| =1.1 x 0.6          | 1.1                           | 0.6                 |
| =1.05 x 0.7         | 1.05                          | 0.7                 |
| =1.1 x 0.8          | 1.1                           | 0.8                 |
| =1 x 0.9            | 1                             | 0.9                 |
| =1 x 0.95           | 1                             | 0.95                |


According to libcbm_c source code's internal processing what is called
climate_adjustement is the growth_multiplier below:

    sw_multiplier = growthMult.SoftwoodMultiplier * growth_multiplier

"""

from functools import cached_property
from eu_cbm_hat.info.clim_adjust_common_input import mean_npp_by_model_country_clu_con_broad



class ClimAdjust:
    """Climate adjustment variables based on modelled NPP values

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference_cable_pop'].runners['EE'][-1]
        >>> # All model inputs for the given country
        >>> runner.clim_adjust.df_all

        >>> # Model input for the selected scenario and model as defined in the
        >>> # combo yaml file
        >>> runner.clim_adjust.df

        This data frame is used by cbm/climate_growth_modifier.py to feed
        growth multiplier to cbm within the time step.

    """

    def __init__(self, parent):
        self.runner = parent
        self.combo_name = self.runner.combo.short_name
        self.combo_config = self.runner.combo.config
        if "climate_adjustment_selected_year" not in self.combo_config.keys():
            self.selected_year = None
        else:
            self.selected_year = self.combo_config["climate_adjustment_selected_year"]
        if "climate_adjustment_model" not in self.combo_config.keys():
            self.model = "default"
        else:
            self.model = self.combo_config["climate_adjustment_model"]

    @cached_property
    def df_all(self):
        """NPP values in all climate models for the given country"""
        country_name = self.runner.country.country_name
        df = mean_npp_by_model_country_clu_con_broad(selected_year=self.selected_year)
        selector = df["country"] == country_name
        return df.loc[selector].copy()

    @cached_property
    def df(self):
        """Climate model NPP inputs for the selected model in the given country

        Ignore the upper-case or lower-case in the model name selection.
        """
        df = self.df_all
        # Select the model, ignore the case
        selector = df["model"].str.lower() == self.model.lower()
        # Keep only those column
        cols = ["model", "country", "con_broad", "climate", "year", "npp", "ratio"]
        return df.loc[selector, cols].copy()

