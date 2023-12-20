"""
The purpose of this script is to compute the Net Annual Increment for one country
"""

from functools import cached_property
import numpy as np
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ub


class NAI:
    """Compute the net annual increment$


    Usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]

        >>> runner.post_processor.nai.df
        >>> runner.post_processor.nai.pools_fluxes_morf
        >>> runner.post_processor.nai.df_agg_sf

   NAI per ha by status at country level:

       >>> df = runner.post_processor.nai.df_agg_sf
       >>> df["nai"] = df["nai_ha"] * df["area"]
       >>> df_st = df.groupby(["year", "status"])[["area", "nai"]].agg("sum").reset_index()
       >>> df_st["nai_ha"] = df_st["nai"] / df_st["area"]
       >>> df_st = df_st.pivot(columns="status", index="year", values="nai_ha")
       >>> from matplotlib import pyplot as plt
       >>> df_st.plot(ylabel="NAI m3 / ha")
       >>> plt.show()
       >>> # Plot without NF
       >>> df_st[['AR', 'ForAWS', 'ForNAWS']].plot(ylabel="NAI m3 / ha")
       >>> plt.show()

    Plot NAI per ha by status

        >>> df_st

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
        # Keep only FORAWS
        df = self.parent.pools_fluxes_morf
        # Add wood density information by forest type
        df = df.merge(self.parent.wood_density_bark_frac, on="forest_type")
        # Convert tons of carbon to volume under bark
        df["merch_vol"] = ton_carbon_to_m3_ub(df, "merch")
        df["ag_vol"] = (df["merch"] + df["other"]) / df["wood_density"]
        df["prod_vol"] = ton_carbon_to_m3_ub(df, "merch_prod")
        df["dom_input_vol"] = df["nat_turnover"] / df["wood_density"]
        # Default to zero for disturbance zero
        df["dist_m_input_vol"] = np.where(
            df["disturbance_type"] == 0, 0, df["dist_input"] / df["wood_density"]
        )
        return df

    @cached_property
    def df_agg_sf(self):
        """Net Annual Increment aggregated by status and forest type"""
        df = self.pools_fluxes_morf
        cols = [
            "merch_vol",
            "ag_vol",
            "prod_vol",
            "dom_input_vol",
            "dist_m_input_vol",
        ]
        index = ["status", "forest_type"]
        df_agg = (
            df.groupby(["year"] + index)[["area"] + cols].agg("sum").reset_index()
        )
        df_agg["net_merch"] = df_agg.groupby(index)["merch_vol"].diff()
        for col in cols + ["net_merch"]:
            df_agg[col + "_ha"] = df_agg[col] / df_agg["area"]
        # Note that net_merch_ha and net_merch_ha_2 are different
        df_agg["net_merch_ha_2"] = df_agg.groupby(index)["merch_vol_ha"].diff()
        df_agg["nai_ha"] = df_agg[["net_merch_ha_2", "prod_vol_ha", "dist_m_input_vol_ha"]].sum(axis=1)
        df_agg["gai_ha"] = df_agg["nai_ha"] + df_agg["dom_input_vol_ha"]
        return df_agg

