""" Common input file used for climate adjustment of growth based on modelled NPP values

Written by Viorel Blujdea and Paul Rougieux.

JRC Biomass Project. Unit D1 Bioeconomy.

- See also plots of NPP in `eu_cbm_hat.plot.npp`:

    >>> import matplotlib.pyplot as plt
    >>> from eu_cbm_hat.plot.npp import plot_npp_facet
    >>> from eu_cbm_hat.info.clim_adjust_common_input import mean_npp_by_model_country_clu_con_broad
    >>> df = mean_npp_by_model_country_clu_con_broad(hist_start_year=2010, hist_end_year=2020)
    >>> plot_npp_facet(df, 'Austria')
    >>> plt.show()

"""

import pandas as pd
from eu_cbm_hat.constants import eu_cbm_data_pathlib


def mean_npp_by_model_country_clu_con_broad(hist_start_year, hist_end_year):
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
        >>> df = mean_npp_by_model_country_clu_con_broad(hist_start_year=2010, hist_end_year=2020)

    """
    csv_filename = "mean_npp_by_model_country_clu_con_broad.csv"
    df = pd.read_csv(eu_cbm_data_pathlib / "common" / csv_filename)

    # REMOVE renaming dut to change of column names in the input file. Workflow from TRENDY inputs is a csv chnaged to
    # 'mean_npp_by_model_country_clu_con_broad_original.csv'. The preprocesing with explore/users_tools/npp_input_processing.py adds
    # a 'mix-models' scenario,  a kind of average of all-models
    #col_rename = {
    #       "npp (tC/ha/yr)": "npp",
    #       "forest_type": "con_broad",
    #       "climatic_unit": "climate",
    #   }
    # Check for missing columns before renaming
    #missing_col = set(col_rename.keys()) - set(df.columns)
    #if missing_col: 
    #    msg = "The following columns are supposed to be renamed "
    #    msg += f"but they are missing: {missing_col}"
    #    msg += "\nData frame columns:\n"
    #    msg += f"{df.columns}"
    #    raise ValueError(msg)
    #df.rename(columns=col_rename, inplace=True)
    
    # Convert climate to a character variable for compatibility with CBM classifiers
    df["climate"] = df["climate"].astype(str)
    # Group the data by 'model', 'country', 'forest_type', and 'climatic_unit'
    # and calculate the first year's 'npp' value for each group
    index = ["model", "country", "con_broad", "climate"]
    # Compute the average over the historical period
    selector = df["year"] >= hist_start_year
    selector &= df["year"] <= hist_end_year
    df_hist_mean = (df.loc[selector].groupby(index).agg(hist_mean_npp = ("npp", "mean"))).reset_index()
    # Merge the first year's 'npp' values with the original DataFrame
    df = df.merge(df_hist_mean, on=index)
    # Calculate the ratio of each year's 'npp' value to historical mean npp
    df["ratio"] = df["npp"] / df["hist_mean_npp"]
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
