"""Common input file used for climate adjustment of growth based on modelled NPP values

Written by Viorel Blujdea and Paul Rougieux.

JRC Biomass Project. Unit D1 Bioeconomy.

- See also plots of NPP in `eu_cbm_hat.plot.npp`:

    >>> import matplotlib.pyplot as plt
    >>> from eu_cbm_hat.plot.npp import plot_npp_facet
    >>> from eu_cbm_hat.info.clim_adjust_common_input import mean_npp_by_model_country_clu_con_broad
    >>> df = mean_npp_by_model_country_clu_con_broad()
    >>> plot_npp_facet(df, 'Austria')
    >>> plt.show()

"""

from functools import cached_property
import pandas as pd
from eu_cbm_hat.constants import eu_cbm_data_pathlib


def mean_npp_by_model_country_clu_con_broad():
    """Read common input file mean NPP by model country CLU and con_broad

    The growth curves is based on a NAI value from the NFI which already
    includes the impact of droughts or other events so we cannot modify it too
    much. For the future, we need to capture both extreme values and the trend.

    A given stand can only have one growth curve calibrated over the historical
    period. We therefore need our growth modifier value to have an average
    value of 1 over the historical period. We compute the average historical
    NPP over the period for which the growth curve is valid. For example, if
    our reference period is 2010-2020. That means we take the average NPP over
    2010-2020 and we use this as the denominator to compute a NPP ratio. Then
    we divide each years's NPP through the average to obtain the growth
    modifier value.

    Usage:

        >>> from eu_cbm_hat.info.clim_adjust_common_input import mean_npp_by_model_country_clu_con_broad
        >>> df = mean_npp_by_model_country_clu_con_broad()

    """
    csv_filename = "mean_npp_by_model_country_clu_con_broad.csv"
    df = pd.read_csv(eu_cbm_data_pathlib / "common" / csv_filename)
    # Convert climate to a character variable for compatibility with CBM classifiers
    df["climate"] = df["climate"].astype(str)
    # Rename con broad
    df["con_broad"] = df["con_broad"].replace({"BL": "broad", "NL": "con"})
    # "default" is a reserved value for the case where there is no climate adjustment
    selector = df["model"] == "default"
    if any(selector):
        msg = "'default' is not allowed as a model name. "
        msg += "It is reserved for the case where no climate model is used\n"
        msg += f"{df.loc[selector]}"
        raise ValueError(msg)
    return df


class ClimAdjustCommonInput:
    """Input data for climate adjustment

    Input increment is a value representing average conditions at national scale.
    Having NPPs on CLUs within the country, we break down the increment/growth
    on CLUs. This would be applied for each model.

    Example use:

        >>> from eu_cbm_hat.info.clim_adjust_common_input import ClimAdjustCommonInput
        >>> climinput= ClimAdjustCommonInput(hist_start_year=2010, hist_end_year=2020)
        >>> df = climinput.mean_npp_by_model_country_clu_con_broad

        >>> spatial_df = climinput.clu_spatial_variation_to_country_mean
        >>> temporal_df = climinput.clu_temporal_variation_to_period_mean
    """

    def __init__(self, hist_start_year, hist_end_year):
        self.hist_start_year = hist_start_year
        self.hist_end_year = hist_end_year

    @cached_property
    def mean_npp_by_model_country_clu_con_broad(self):
        """Cached DataFrame from mean_npp_by_model_country_clu_con_broad with
        default historical period."""
        return mean_npp_by_model_country_clu_con_broad()

    def mean_npp(self, index, variable):
        """NPP mean by index variables        TODO: make index and variable an argument, such that
        variable="hist_mean_npp"

        >>> from eu_cbm_hat.info.clim_adjust_common_input import ClimAdjustCommonInput
        >>> climinput= ClimAdjustCommonInput(hist_start_year=2010, hist_end_year=2020)

        Temporal mean by Climatic unit:

        >>> index = ["model", "country", "con_broad", "climate"]
        >>> mean_npp_time = climinput.mean_npp(index=index, variable="hist_mean_npp")

        Spatial mean at country level:

        >>> index = ["model", "country", "con_broad"]
        >>> mean_npp_country = climinput.mean_npp(index=index, variable="country_mean_npp")

        """
        df = self.mean_npp_by_model_country_clu_con_broad
        selector = df["year"] >= self.hist_start_year
        selector &= df["year"] <= self.hist_end_year
        df_mean = (
            (df.loc[selector].groupby(index)["npp"].agg("mean"))
            .reset_index()
            .rename(columns={"npp": variable})
        )
        return df_mean

    @cached_property
    def clu_spatial_variation_to_country_mean(self):
        """DataFrame describing spatial NPP variations in climatic units
        relative to country mean.

        For each model, country, con_broad, and climate, provides the ratio of
        the climatic unit's average NPP over the historical period to the
        country's average NPP over the same period."""
        df = self.mean_npp_by_model_country_clu_con_broad
        selector = df["year"] >= self.hist_start_year
        selector &= df["year"] <= self.hist_end_year
        index = ["model", "country", "con_broad"]
        df = self.mean_npp_by_model_country_clu_con_broad
        self.hist_mean_by_clu
        country_mean = (
            df.loc[selector]
            .groupby(index)
            .agg(country_mean_npp=("hist_mean_npp", "mean"))
            .reset_index()
        )

        df = df.merge(country_mean, on=["model", "country", "con_broad"])
        df["spatial_ratio"] = df["hist_mean_npp"] / df["country_mean_npp"]
        return df[["model", "country", "con_broad", "climate", "spatial_ratio"]]

    @cached_property
    def clu_temporal_variation_to_period_mean(self):
        """DataFrame describing temporal NPP variations in climatic units
        relative to period mean.

        For each model, country, con_broad, climate, and year, provides the
        ratio of the yearly NPP to the historical mean NPP for that climatic
        unit.

        2. Merge with the original DataFrame
        3. Calculate the ratio of each year's 'npp' value to historical mean npp

        """
        df = self.mean_npp_by_model_country_clu_con_broad
        index = ["model", "country", "con_broad", "climate"]
        df = df.merge(self.hist_mean_by_clu, on=index)
        df["temporal_ratio"] = df["npp"] / df["hist_mean_npp"]
        return df
