import pandas
from libcbm.model.cbm.cbm_variables import CBMVariables

def cbm_vars_to_df(cbmvariables: CBMVariables, df_name:str) -> pandas.DataFrame:
    """Extract a data frame from cbm_vars and rename columns if it's the inventory"""
    df = getattr(cbmvariables, df_name).to_pandas()
    # The age and land_class columns appears twice, rename those in the inventory
    if df_name == "inventory":
        df.rename(columns = {'age':        'inv_start_age',
                             'land_class': 'inv_start_land_class'}, inplace=True)
    return df
