"""
The purpose of this script is to compute the Net Annual Increment for one country
"""

from typing import Union, List
from functools import cached_property
import numpy as np
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ub


# +
class NAI:
    """Compute the net annual increment$


   Usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.nai.pools_fluxes_morf
        >>> # NAI per ha by status and forest type at country level
        >>> runner.post_processor.nai.df_agg(["status", "forest_type"])
        >>> # NAI per ha by status at country level
        >>> runner.post_processor.nai.df_agg(["status"])

        >>> df = runner.post_processor.nai.df_agg(["status"])
        >>> df["nai_merch"] = df["nai_merch_ha"] * df["area"]
        >>> df_st = df.groupby(["year", "status"])[["area", "nai_merch"]].agg("sum").reset_index()
        >>> df_st["nai_merch_ha"] = df_st["nai_merch"] / df_st["area"]
        >>> # Plot NAI per ha by status
        >>> df_st = df_st.pivot(columns="status", index="year", values="nai_merch_ha")
        >>> from matplotlib import pyplot as plt
        >>> df_st.plot(ylabel="nai_merch m3 / ha")
        >>> plt.show()
        >>> # Plot without NF
        >>> df_st[['AR', 'ForAWS', 'ForNAWS']].plot(ylabel="nai_merch m3 / ha")
        >>> plt.show()

     Roberto's NAI computations
     in ~/downloads/qa_qc_stock_dynamic_rp_AT.md

         1. FT_MS_Increment
             NAI = Net_Merch + Prod_vol_ha + Dist_vol_ha
             GAI = Net_Merch + Prod_vol_ha + DOM_vol_ha
         2. Country_Increment
             NAI = Net_Merch + Prod_vol_ha + Dist_vol_ha
             GAI = Net_Merch + Prod_vol_ha + DOM_vol_ha + Dist_vol_ha
         3. FAWS_Increment
             NAI = Net_Merch+Prod_vol_ha + Dist_vol_ha
             GAI = Net_Merch+Prod_vol_ha + DOM_vol_ha+Dist_vol_ha

    """
    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name

    @cached_property
    def pools_fluxes_morf(self):
        """Merchantable pools and fluxes aggregated at the classifiers level"""
        df = self.parent.pools_fluxes_morf
        # Add wood density information by forest type
        df = df.merge(self.parent.wood_density_bark_frac, on="forest_type")
        # Convert tons of carbon to volume under bark
        df["merch_stock_vol"] = df["merch"] / df["wood_density"]
        df["agb_stock_vol"] = (df["merch"] + df["other"]) / df["wood_density"]

# I raname this pool from "prod_vol" to "merch_prod_vol", so we can get the two fluxes
        df["merch_prod_vol"] = ton_carbon_to_m3_ub(df, "merch_prod")
                                                   
# I add new flux
        df["other_prod_vol"] = ton_carbon_to_m3_ub(df, "oth_prod")
                                                   
# I add these two fluxes which represent the shares of the biomass lost to the air        
        df["merch_air_vol"] = ton_carbon_to_m3_ub(df, "disturbance_merch_to_air")
        df["oth_air_vol"] = ton_carbon_to_m3_ub(df, "disturbance_oth_to_air")
        
        df["turnover_merch_input_vol"] = (
            (df["turnover_merch_litter_input"]) / df["wood_density"]
        )
        df["turnover_oth_input_vol"] = (
            (df["turnover_oth_litter_input"])/ df["wood_density"]
        )
# these filters for "== 0" are not needed as such transfers are zero anyway
        df["dist_merch_input_vol"] = np.where(
            df["disturbance_type"] == 0,
            0,
            df["disturbance_merch_litter_input"] / df["wood_density"],
        )
        df["dist_oth_input_vol"] = np.where(
            df["disturbance_type"] == 0,
            0,
            df["disturbance_oth_litter_input"] / df["wood_density"],
        )
        return df

    def df_agg(self, groupby: Union[List[str], str]):
        """Net Annual Increment aggregated by status and forest type

        Usage:

             >>> from eu_cbm_hat.core.continent import continent
             >>> runner = continent.combos['reference'].runners['LU'][-1]
             >>> nai_st = runner.post_processor.nai.df_agg(["status"])

        Check net merch

            >>> import numpy as np
            >>> np.testing.assert_allclose(nai_st["net_merch_ha_2"],  nai_st["net_merch_ha_2"], rtol=0.01)

        """
        if isinstance(groupby, str):
            groupby = [groupby]
        df = self.pools_fluxes_morf
        cols = [
            "merch_stock_vol",
            "agb_stock_vol",
# I renamed fluxes to allow adding the two oth flux
            #"prod_vol" is converted to: 
            "merch_prod_vol",
            # the new pool addedd
            "other_prod_vol",
# I reorderd            
            "turnover_merch_input_vol",
            "turnover_oth_input_vol",
            "dist_merch_input_vol",
            "dist_oth_input_vol",
# I addedd these two new transfers addedd
            "merch_air_vol",
            "oth_air_vol"
            ]
        df_agg = (
            df.groupby(["year"] + groupby)[["area"] + cols].agg("sum").reset_index()
        )
        df_agg["net_merch"] = df_agg.groupby(groupby)["merch_stock_vol"].diff()
        df_agg["net_agb"] = df_agg.groupby(groupby)["agb_stock_vol"].diff()
        
        
#        for col in cols + ["net_merch", "net_agb"]:
# here we should not average but simply sum the stock chnages
#            df_agg[col + "_ha"] = df_agg[col] / df_agg["area"]
        # Test, compute merch per ha in a different way
        # Note that net_merch_ha and net_merch_ha_2 are different, but not by much
        # TODO move this outside the function, to the example.
#        df_agg["net_merch_ha_2"] = df_agg.groupby(groupby)["merch_vol_ha"].diff()
        
        # Compute NAI for the merchantable pool only
#        df_agg["nai_merch_ha"] = df_agg[
#            ["net_merch_ha", "prod_vol_ha", "dist_merch_input_vol_ha"]
#        ].sum(axis=1)
#        df_agg["gai_merch_ha"] = (
#            df_agg["nai_merch_ha"] + df_agg["turnover_merch_input_vol_ha"]
#        )
        
# NEW, based on stock change only
       
        # Compute NAI for the merchantable pool only
        df_agg["nai_merch"] = df_agg[["net_merch", "merch_prod_vol", 
                                      "dist_merch_input_vol"]].sum(axis=1)
        df_agg["gai_merch"] = df_agg["nai_merch"] + df_agg[["turnover_merch_input_vol", 
                                                            "merch_air_vol"]].sum(axis=1)
        df_agg["nai_merch_ha"] = df_agg["nai_merch"]/df_agg["area"]
        df_agg["gai_merch_ha"] = df_agg["gai_merch"]/df_agg["area"]
        
        #Compute NAI for merchantable and OWC together
        df_agg["nai_agb"] = df_agg [["net_agb", "merch_prod_vol", "other_prod_vol", 
                                     "dist_merch_input_vol","dist_oth_input_vol"]].sum(axis=1)
        df_agg["gai_agb"] = df_agg["nai_merch"] + df_agg[["turnover_merch_input_vol",
                                                            "turnover_oth_input_vol",
                                                            "merch_air_vol","oth_air_vol"]].sum(axis=1)
        df_agg["nai_agb_ha"] = df_agg["nai_merch"]/df_agg["area"]
        df_agg["gai_agb_ha"] = df_agg["gai_merch"]/df_agg["area"]
        
#        df_agg["nai_agb_ha"] = df_agg[
#            [
#                "net_agb_ha",
#                "prod_vol_ha",
#                "dist_merch_input_vol_ha",
#                "dist_oth_input_vol_ha",
#            ]
#        ].sum(axis=1)
#        df_agg["gai_agb_ha"] = df_agg[
#            ["nai_agb_ha", "turnover_merch_input_vol_ha", "turnover_oth_input_vol_ha"]
#        ].sum(axis=1)
        return df_agg
