"""Climate adjustment variables based on modelled NPP values

Written by Viorel Blujdea and Paul Rougieux.

JRC Biomass Project. Unit D1 Bioeconomy.

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
from eu_cbm_hat.info.clim_adjust_common_input import ClimAdjustCommonInput

class ClimAdjust:
    """Climate adjustment variables based on modelled NPP values

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['reference_cable_pop'].runners['EE'][-1]
    >>> # All model inputs for the given country
    >>> runner.clim_adjust.df_all

    Scenario attributes define in the combo yaml file

    >>> print(runner.clim_adjust.model)
    >>> print(runner.clim_adjust.clu_spatial_growth)

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
        # Default values for the climate modification
        self.default_config = {
            "model": "default",
            "hist_start_year": None,
            "hist_end_year": None,
            "clu_spatial_growth": False
        }
        for attr_name, default in self.default_config.items():
            setattr(self,
                    attr_name,
                    self.combo_config.get("climate_adjustment", {}).get(attr_name, default))
        # NPP input data
        self.common_input = ClimAdjustCommonInput(hist_start_year=2010, hist_end_year=2020)

    @cached_property
    def df_all(self):
        """NPP values in all climate models for the given country"""
        country_name = self.runner.country.country_name
        temporal_df = self.common_input.clu_temporal_npp_ratio_to_period_mean
        spatial_df = self.common_input.clu_spatial_npp_ratio_to_country_mean.copy()
        spatial_df = spatial_df.drop(columns="hist_mean_npp")
        index = ["model", "country", "con_broad", "climate"]
        df = temporal_df.merge(spatial_df, on=index, how="left")
        selector = df["country"] == country_name
        return df.loc[selector].copy()

    @cached_property
    def df(self):
        """Climate model NPP inputs for the selected model in the given country

        Ignore the upper-case or lower-case in the model name selection.
        Depending on how the clu_spatial_growth scenario argument is defined,
        provide the ratio to the temporal mean only, or the ration to both
        temporal and spatial mean.
        """
        df = self.df_all
        # Implement the scenario with or without spatial variation
        if self.clu_spatial_growth:
            df["ratio"] = df["temporal_ratio"] * df["spatial_ratio"]
        else:
            df["ratio"] = df["temporal_ratio"]
        # Select the model, ignore the case
        selector = df["model"].str.lower() == self.model.lower()
        # Keep only those column
        cols = ["model", "country", "con_broad", "climate", "year", "npp", "ratio"]
        return df.loc[selector, cols].copy()
