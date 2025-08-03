"""
The purpose of this script is to compute the NPP coresponding to cbm's runs
"""

from functools import cached_property
from typing import Union, List
import warnings
import pandas
import numpy as np

def npp_components(df: pandas.DataFrame, groupby: Union[List[str], str]):
    """Compute the Net Annual Increment and Gross Annual Increment on climates, for npp-nai analysis

    Based on stock change and movements to the product pools as well as
    turnover and mouvements to air.

   
        >>> from eu_cbm_hat.core.continent import continent
        >>> from eu_cbm_hat.post_processor.nai import NAI_AGG_COLS
        >>> from eu_cbm_hat.post_processor.nai import compute_nai_gai
        >>> runner = continent.combos['reference'].runners['ZZ'][-1]
        >>> index = ["status"]
        >>> nai_st = runner.post_processor.nai.df_agg(index)


    """

    print(groupby)

    
    if isinstance(groupby, str):
        groupby = [groupby]

    if "year" in groupby:
        msg = " This functions computes the difference in stock across groups "
        msg += "through time so 'year' should not be in the group variables:\n"
        msg += f"{groupby}"
        raise ValueError(msg)

    # Order by groupby variables, then years
    df.sort_values(groupby + ["year"], inplace=True)

    #print(df.head(2))

    
    # Check that there are no duplications over the groupby variables plus year
    #selector = df[["year"] + groupby].duplicated(keep=False)
    #if any(selector):
    #    msg = "The following rows have duplications along the groupby variables.\n"
    #    msg += f"{df.loc[selector, ['year'] + groupby ]}"
    #    msg += "\nPlease aggregate first along the groupby variables and year:\n"
    #    msg += f"{['year'] + groupby }\n Then run this function.\n"
    #    raise ValueError(msg)

    # Compute the difference in stock for the total standing biomass
    # Use Observed = True to avoid the warning when using categorical variables
    df["agb"] = df["merch"] + df["other"]+ df["foliage"]+ df["roots"]
    df["net_agb"] = df.groupby(groupby, observed=True)["agb"].diff()
   
    # Compute NAI for the merchantable pool
    df["npp"] = df[["net_agb",
                    # biomass to production
                    "merch_prod", 
                    "oth_prod",
                    # transfers to non living pools through disturbances
                    'disturbance_merch_litter_input',
                    'disturbance_oth_litter_input',
                    'disturbance_fol_litter_input',
                    'disturbance_coarse_litter_input',
                    'disturbance_fine_litter_input',        
                    'disturbance_merch_to_air',
                    'disturbance_oth_to_air',
                    'disturbance_fol_to_air',
                    'disturbance_coarse_to_air',
                    'disturbance_fine_to_air',
                    # transfers to non living pools through natural decay
                    'turnover_merch_litter_input',
                    'turnover_oth_litter_input',
                    'turnover_fol_litter_input',
                    'turnover_coarse_litter_input',
                    'turnover_fine_litter_input']].sum(axis=1)

    # Compute per hectare values
    #df["nai_merch_ha"] = df["nai_merch"] / df["area"]
    #df["gai_merch_ha"] = df["gai_merch"] / df["area"]
    #df["nai_agb_ha"] = df["nai_agb"] / df["area"]
    #df["gai_agb_ha"] = df["gai_agb"] / df["area"]
    return df


class NPP:
    """Compute the net growth
    Usage:

        >>> # Net Annual Increment of the merchantable pool (nai_merch) and of
        >>> # all the above ground biomass (nai_agb) by status
        >>> nai_st = runner.post_processor.nai.df_agg(["status"])
        >>> selector = nai_st["status"] == 'ForAWS'
        >>> nai_st.loc[selector, ["year", "status", "area", "nai_merch", "nai_agb"]].head()
     
        """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name

    @cached_property
    def compute_npp(self):
        """Merchantable pools and fluxes aggregated at the classifiers level"""
        df = self.parent.pools_fluxes_morf
        print(df.columns)
        df_out = npp_components(df, groupby= ['status','climate', 'con_broad'])
        return df_out
