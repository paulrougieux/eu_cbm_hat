"""Climate adjustment variables based on modelled NPP values
"""

from functools import cached_property
from eu_cbm_hat.info.clim_adjust_common_input import mean_npp_by_model_country_clu_con_broad



class ClimAdjust:
    """Climate adjustment variables based on modelled NPP values

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference_cable_pop'].runners['EE'][-1]
        >>> # All model inputs for the given country
        >>> runner.clim_adjust.df_all

        >>> # Model input for the selected scenario and model
        >>> runner.clim_adjust.df

    """

    def __init__(self, parent):
        self.runner = parent
        self.combo_name = self.runner.combo.short_name
        self.selected_year = self.runner.combo.config["climate_adjustment_selected_year"]
        self.model = self.runner.combo.config["climate_adjustment_model"]

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
        cols = ["model", "country", "con_broad", "climate", "year", "npp", "ratio"]
        return df.loc[selector, cols].copy()

