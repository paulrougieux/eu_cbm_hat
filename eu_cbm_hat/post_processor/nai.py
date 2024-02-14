"""
The purpose of this script is to compute the Net Annual Increment for one country
"""

from functools import cached_property
from typing import Union, List
import warnings
import pandas

import numpy as np

from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ob
from eu_cbm_hat import CARBON_FRACTION_OF_BIOMASS


def compute_nai_gai(df: pandas.DataFrame, groupby: Union[List[str], str]):
    """Compute the Net Annual Increment and Gross Annual Increment

    Based on stock change and movements to the product pools as well as
    turnover and mouvements to air.

    """
    if "year" in groupby:
        msg = " This functions computes the difference in stock across groups "
        msg += "through time so 'year' should not be in the group by variables:\n"
        msg += f"{groupby}"
        raise ValueError(msg)

    # Order by groupby variables, then years
    df.sort_values(groupby + ["year"], inplace=True)
    # Check that there are no duplications over the groupby variables plus year
    selector = df[["year"] + groupby].duplicated(keep=False)
    if any(selector):
        msg = "The following rows have duplications along the groupby variables.\n"
        msg += f"{df.loc[selector, ['year'] + groupby ]}"
        msg += "\nPlease aggregate first along the groupby variables and year:\n"
        msg += f"{['year'] + groupby }\n Then run this function.\n"
        raise ValueError(msg)

    # Compute the difference in stock for the standing biomass
    # Use Observed = True to avoid the warning when using categorical variables
    df["net_merch"] = df.groupby(groupby, observed=True)["merch_stock_vol"].diff()
    df["net_agb"] = df.groupby(groupby, observed=True)["agb_stock_vol"].diff()

    # Compute NAI for the merchantable pool
    df["nai_merch"] = df[["net_merch", "merch_prod_vol", "dist_merch_input_vol"]].sum(
        axis=1
    )
    df["gai_merch"] = df["nai_merch"] + df[
        ["turnover_merch_input_vol", "merch_air_vol"]
    ].sum(axis=1)

    # Compute NAI for the merchantable pool and OWC pool together
    df["nai_agb"] = df[
        [
            "net_agb",
            "merch_prod_vol",
            "other_prod_vol",
            "dist_merch_input_vol",
            "dist_oth_input_vol",
        ]
    ].sum(axis=1)
    df["gai_agb"] = df["nai_agb"] + df[
        [
            "turnover_merch_input_vol",
            "turnover_oth_input_vol",
            "merch_air_vol",
            "oth_air_vol",
        ]
    ].sum(axis=1)
    # Compute per hectare values
    df["nai_merch_ha"] = df["nai_merch"] / df["area"]
    df["gai_merch_ha"] = df["gai_merch"] / df["area"]
    df["nai_agb_ha"] = df["nai_agb"] / df["area"]
    df["gai_agb_ha"] = df["gai_agb"] / df["area"]
    return df


class NAI:
    """Compute the net annual increment$

    Usage:

         >>> from eu_cbm_hat.core.continent import continent
         >>> runner = continent.combos['reference'].runners['LU'][-1]
         >>> runner.post_processor.nai.pools_fluxes_vol
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
    def pools_fluxes_vol(self):
        """Merchantable pools and fluxes aggregated at the classifiers level"""
        df = self.parent.pools_fluxes_morf
        # Add wood density information by forest type
        df = df.merge(self.parent.wood_density_bark_frac, on="forest_type")

        # Convert tons of carbon to volume over bark
        df["merch_stock_vol"] = ton_carbon_to_m3_ob(df, "merch")
        df["agb"] = df["merch"] + df["other"]
        df["agb_stock_vol"] = ton_carbon_to_m3_ob(df, "agb")

        # Fluxes to products
        df["merch_prod_vol"] = ton_carbon_to_m3_ob(df, "merch_prod")
        df["other_prod_vol"] = ton_carbon_to_m3_ob(df, "oth_prod")

        # Fluxes which represent the biomass lost to the air
        df["merch_air_vol"] = ton_carbon_to_m3_ob(df, "disturbance_merch_to_air")
        df["oth_air_vol"] = ton_carbon_to_m3_ob(df, "disturbance_oth_to_air")

        df["turnover_merch_input_vol"] = ton_carbon_to_m3_ob(
            df, "turnover_merch_litter_input"
        )
        df["turnover_oth_input_vol"] = ton_carbon_to_m3_ob(
            df, "turnover_oth_litter_input"
        )

        # these filters for "== 0" are not needed as such transfers are zero anyway
        df["dist_merch_input_vol"] = np.where(
            df["disturbance_type"] == 0,
            0,
            ton_carbon_to_m3_ob(df, "disturbance_merch_litter_input"),
        )
        df["dist_oth_input_vol"] = np.where(
            df["disturbance_type"] == 0,
            0,
            ton_carbon_to_m3_ob(df, "disturbance_oth_litter_input"),
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
        if groupby != ["status"]:
            warnings.warn("This method was written for a group by status.")
        df = self.pools_fluxes_vol
        pools_cols = ["merch_stock_vol", "agb_stock_vol"]
        fluxes_cols = [
            "merch_prod_vol",
            "other_prod_vol",
            "turnover_merch_input_vol",
            "turnover_oth_input_vol",
            "dist_merch_input_vol",
            "dist_oth_input_vol",
            "merch_air_vol",
            "oth_air_vol",
        ]

        # Aggregate the sum of selected columns
        cols = pools_cols + fluxes_cols
        df_agg = (
            df.groupby(["year"] + groupby)[["area"] + cols].agg("sum").reset_index()
        )

        # Add NF movements to products back to ForAWS
        selector = df_agg["status"] == "NF"
        df_agg_nf = df_agg.loc[selector, ["year", "status"] + fluxes_cols].copy()
        df_agg_nf["status"] = "ForAWS"
        df_agg_nf.columns = df_agg_nf.columns.str.replace("_vol", "_vol_nf")
        df_agg = df_agg.merge(df_agg_nf, on=["year"] + groupby, how="left")
        fluxes_cols_nf = [x + "_nf" for x in fluxes_cols]
        df_agg[fluxes_cols_nf] = df_agg[fluxes_cols_nf].fillna(0)
        # Add the nf fluxes to the fluxes in ForAWS
        for col1, col2 in zip(fluxes_cols, fluxes_cols_nf):
            df_agg[col1] += df_agg[col2]

        # Compute NAI and GAI
        df_out = compute_nai_gai(df_agg, groupby=groupby)
        return df_out
