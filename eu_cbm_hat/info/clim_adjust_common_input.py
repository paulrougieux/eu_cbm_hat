"""Common input file used for climate adjustment of growth based on modelled NPP values

Written by Viorel Blujdea and Paul Rougieux.

JRC Biomass Project. Unit D1 Bioeconomy.

- See below for examples of how to load data and compute spatial and temporal
  averages.

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
from eu_cbm_hat.info.input_data     import InputData


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
        >>> climinput = ClimAdjustCommonInput(hist_start_year=2010, hist_end_year=2020)
        >>> df = climinput.mean_npp_by_model_country_clu_con_broad

        >>> spatial_df = climinput.clu_spatial_npp_ratio_to_country_mean
        >>> temporal_df = climinput.clu_temporal_npp_ratio_to_period_mean
    """

    def __init__(self, hist_start_year, hist_end_year):
        self.hist_start_year = hist_start_year
        self.hist_end_year = hist_end_year
        self.input_data = InputData()

    @cached_property
    def mean_npp_by_model_country_clu_con_broad(self):
        """NPP by model country CLU and con broad loaded from the csv input
        file with some modifications.
        """
        return mean_npp_by_model_country_clu_con_broad()

    def mean_npp_per_ha(self, index, variable):
        """Average Net Primary Productivity (NPP) grouped by index variables

        >>> from eu_cbm_hat.info.clim_adjust_common_input import ClimAdjustCommonInput
        >>> climinput= ClimAdjustCommonInput(hist_start_year=2010, hist_end_year=2020)

        Temporal mean by Climatic unit:

        >>> index = ["model", "country", "con_broad", "climate"]
        >>> mean_npp_time = climinput.mean_npp(index=index, variable="hist_mean_npp")

        Spatial mean at country level:

        >>> index = ["model", "country", "con_broad"]
        >>> mean_npp_country = climinput.mean_npp(index=index, variable="country_mean_npp")

        """
        df= self.mean_npp_by_model_country_clu_con_broad
        selector = df["year"] >= self.hist_start_year
        selector &= df["year"] <= self.hist_end_year
        df_mean = (
            (df.loc[selector].groupby(index)["npp"].agg("mean"))
            .reset_index()
            .rename(columns={"npp": variable})
        )
        return df_mean
    
    def npp_per_clu(self, index, variable):
        """
        This would allow for forest area weighted share of increment.
        
        Total Net Primary Productivity (NPP) per clus in the country grouped by index variables
        estimates as 'area' on clus and con_broad from input inventory multiplied with npp_per_ha

        Applied to all models independent of year

        """
        df_npp = self.mean_npp_by_model_country_clu_con_broad
        df_area = self.input_data.inventory  # Access inventory through input_data instance
        df_area = df_area.groupby(['climate', 'con_broad'])['area'].sum().reset_index()
        df = df_npp.merge(df_area, on=['con_broad', 'climate'])
        selector = df["year"] >= self.hist_start_year
        selector &= df["year"] <= self.hist_end_year
        df_mean = (
            (df.loc[selector].groupby(index)["npp"].agg("mean"))
            .reset_index()
            .rename(columns={"npp": variable})
        )
        return df_mean

    @cached_property
    def clu_spatial_npp_ratio_to_country_mean(self):
        """Spatial NPP variations in climatic units relative to the country mean.

        For each model, country, con_broad, and climate, provides the ratio of
        the climatic unit's average NPP over the historical period to the
        country's average NPP over the same period.
        """
        index_t = ["model", "country", "con_broad", "climate"]
        df_mean_temporal = self.npp_per_clu(index=index_t, variable="hist_mean_npp")
        index_s = ["model", "country", "con_broad"]
        df_mean_spatial = self.npp_per_clu(index=index_s, variable="country_mean_npp")
        df = df_mean_temporal.merge(df_mean_spatial, on=index_s)
        df["spatial_ratio"] = df["hist_mean_npp"] / df["country_mean_npp"]
        print(df.head())
        return df

    @cached_property
    def clu_temporal_npp_ratio_to_period_mean(self):
        """Temporal NPP variations relative to the selected period mean.

        For each model, country, con_broad, climate, and year, provides the
        ratio of the yearly NPP to the historical mean NPP for that climatic
        unit over the period self.hist_start_year to self.hist_end_year.
        """
        df = self.mean_npp_by_model_country_clu_con_broad
        index = ["model", "country", "con_broad", "climate"]
        df_mean_temporal = self.mean_npp_per_ha(index=index, variable="hist_mean_npp")
        df = df.merge(df_mean_temporal, on=index, how="left")
        df["temporal_ratio"] = df["npp"] / df["hist_mean_npp"]
        return df
