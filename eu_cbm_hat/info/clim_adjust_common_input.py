""" Common input file used for climate adjustment of growth based on modelled NPP values
"""

import pandas as pd
from eu_cbm_hat.constants import eu_cbm_data_pathlib


def mean_npp_by_model_country_clu_con_broad(selected_year):
    """Read common input file mean NPP by model country CLU and con_broad

    Usage:

        >>> from eu_cbm_hat.info.clim_adjust_common_input import mean_npp_by_model_country_clu_con_broad
        >>> df = mean_npp_by_model_country_clu_con_broad(selected_year=2001)

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
    df_selected_year = df[df["year"] == selected_year][index + ["npp"]].rename(
        columns={"npp": "npp_selected_year"}
    )
    # Merge the first year's 'npp' values with the original DataFrame
    df = df.merge(df_selected_year, on=index)

    # Calculate the ratio of each year's 'npp' value to the first year's 'npp' value
    df["ratio"] = df["npp"] / df["npp_selected_year"]
    # Rename con broad
    df["con_broad"] = df["con_broad"].replace({"BL": "broad", "NL": "con"})
    # Remove columns
    df.drop(columns=["npp_selected_year"], inplace=True)
    # "default" is a reserved value for the case where there is no climate adjustment
    selector = df["model"] == "default"
    if any(selector):
        msg = "'default' is not allowed as a model name. "
        msg += "It is reserved for the case where no climate model is used\n"
        msg += f"{df.loc[selector]}"
        raise ValueError(msg)
    return df
