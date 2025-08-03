"""
The purpose of this script is to compute the Net Annual Increment for one country
"""

from functools import cached_property
from typing import Union, List
import warnings
import pandas

import numpy as np

from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ob

POOLS_COLS = ["merch_stock_vol", "agb_stock_vol"]
FLUXES_COLS = [
    "merch_prod_vol",
    "other_prod_vol",
    "turnover_merch_input_vol",
    "turnover_oth_input_vol",
    "dist_merch_input_vol",
    "dist_oth_input_vol",
    "merch_air_vol",
    "oth_air_vol",
]
NAI_AGG_COLS = ["area"] + POOLS_COLS + FLUXES_COLS


def compute_nai_gai(df: pandas.DataFrame, groupby: Union[List[str], str]):
    """Compute the Net Annual Increment and Gross Annual Increment

    Based on stock change and movements to the product pools as well as
    turnover and mouvements to air.

    Before using this function, make sure you aggregate along the groupby
    variables and year first. Then the year should not be present on the
    groupby variable. For example:

        >>> from eu_cbm_hat.core.continent import continent
        >>> from eu_cbm_hat.post_processor.nai import NAI_AGG_COLS
        >>> from eu_cbm_hat.post_processor.nai import compute_nai_gai
        >>> runner = continent.combos['reference'].runners['ZZ'][-1]
        >>> index = ["status"]
        >>> nai_st = runner.post_processor.nai.df_agg(index)
        >>> nai_st_2  = nai_st.groupby(["year"] + index, observed=True)[NAI_AGG_COLS].agg("sum").reset_index()
        >>> nai_st_2 = compute_nai_gai(nai_st_2, groupby=index)
        >>> cols = ["year", "status", "nai_merch", "nai_agb"]
        >>> nai_st_2.query("status == 'ForAWS'")[cols].tail().round()
            year  status  nai_merch    nai_agb
        35  2025  ForAWS   741289.0  1040573.0
        38  2026  ForAWS   741157.0  1042235.0
        41  2027  ForAWS   733556.0  1001680.0
        44  2028  ForAWS   729052.0  1010633.0
        47  2029  ForAWS   726057.0   997929.0

    """
    if isinstance(groupby, str):
        groupby = [groupby]

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
        >>> runner = continent.combos['reference'].runners['ZZ'][-1]
        >>> pfv = runner.post_processor.nai.pools_fluxes_vol
        >>> pfv[["year", "disturbance_type", "merch_stock_vol", "agb_stock_vol"]].round()
             year  disturbance_type  merch_stock_vol  agb_stock_vol
        0    1999                 0         910610.0      1192798.0
        1    1999                 0        1126951.0      1476133.0
        2    2000                 0         925037.0      1211039.0
        3    2000                 0        1144770.0      1498664.0
        4    2001                 0         939214.0      1228955.0
        ..    ...               ...              ...            ...
        765  2028                 0        1026355.0      1399375.0
        766  2029                 0        6931140.0      9711487.0
        767  2029                 0        1299132.0      1814424.0
        768  2029                 0        5503622.0      7509163.0
        769  2029                 0        1038402.0      1415584.0
        <BLANKLINE>
        [770 rows x 4 columns]

        >>> # Net Annual Increment of the merchantable pool (nai_merch) and of
        >>> # all the above ground biomass (nai_agb) by status
        >>> nai_st = runner.post_processor.nai.df_agg(["status"])
        >>> selector = nai_st["status"] == 'ForAWS'
        >>> nai_st.loc[selector, ["year", "status", "area", "nai_merch", "nai_agb"]].head()
           year  status      area      nai_merch        nai_agb
        0  1999  ForAWS  190511.0       0.000000       0.000000
        1  2000  ForAWS  190511.0  728968.599620  953551.543839
        2  2001  ForAWS  190511.0  729099.275544  728706.869910
        3  2002  ForAWS  190511.0  731377.641584  734923.265648
        4  2003  ForAWS  190511.0  734402.356549  745183.482842


        >>> # TODO fix this example
        >>> # NAI per ha by status and forest type at country level
        >>> # See message below on KeyError: 'forest_type'
        >>> # when merging back the movements of the NF pools to products.
        >>> runner.post_processor.nai.df_agg(["status", "forest_type"]) # doctest: +SKIP

        >>> df = runner.post_processor.nai.df_agg(["status"])
        >>> df["nai_merch"] = df["nai_merch_ha"] * df["area"]
        >>> df_st = df.groupby(["year", "status"])[["area", "nai_merch"]].agg("sum").reset_index()
        >>> df_st["nai_merch_ha"] = df_st["nai_merch"] / df_st["area"]
        >>> df_st.tail()
            year  status           area      nai_merch  nai_merch_ha
        44  2028  ForAWS  190431.000498  729052.322451      3.828433
        45  2028      NF      80.000000    4286.556122     53.581952
        46  2029      AR      90.000000      16.971735      0.188575
        47  2029  ForAWS  190421.000047  726056.898576      3.812904
        48  2029      NF      90.000000    4304.132653     47.823696

        >>> # Plot NAI per ha by status (remove NF)
        >>> df_st = runner.post_processor.nai.df_agg(["status"])
        >>> selector = df_st["status"] != 'NF'
        >>> df_st = df_st.loc[selector].pivot(columns="status", index="year", values="nai_merch_ha")
        >>> from matplotlib import pyplot as plt
        >>> df_st.plot(ylabel="nai_merch m3 / ha") # doctest: +SKIP
        >>> plt.show()  # doctest: +SKIP

        Note in terms of ecosystem indicators, foliage should be there in the NAI
        increment computation.
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
            >>> runner = continent.combos['reference'].runners['ZZ'][-1]
            >>> # Net Annual Increment of the merchantable pool (nai_merch) and of
            >>> # all the above ground biomass (nai_agb) by status
            >>> nai_st = runner.post_processor.nai.df_agg(["status"])
            >>> selector = nai_st["status"] == 'ForAWS'
            >>> nai_st.loc[selector, ["year", "status", "area", "nai_merch", "nai_agb"]].head()
               year  status      area      nai_merch        nai_agb
            0  1999  ForAWS  190511.0       0.000000       0.000000
            1  2000  ForAWS  190511.0  728968.599620  953551.543839
            2  2001  ForAWS  190511.0  729099.275544  728706.869910
            3  2002  ForAWS  190511.0  731377.641584  734923.265648
            4  2003  ForAWS  190511.0  734402.356549  745183.482842

        """
        if isinstance(groupby, str):
            groupby = [groupby]
        if groupby != ["status"]:
            warnings.warn("This method was written for a group by status.")
        df = self.pools_fluxes_vol

        # Aggregate the sum of selected columns
        df_agg = (
            df.groupby(["year"] + groupby)[NAI_AGG_COLS].agg("sum").reset_index()
        )

        print(df_agg.columns)
        
        # Add NF movements to products back to ForAWS
        # Note this is a problem when we use grouping variables other than
        # "status" alone For example if groupby = ["status", "forest_type"]
        # the merge below generates the KeyError: 'forest_type'
        selector = df_agg["status"] == "NF"
        df_agg_nf = df_agg.loc[selector, ["year", "status"] + FLUXES_COLS].copy()
        df_agg_nf["status"] = "ForAWS"
        df_agg_nf.columns = df_agg_nf.columns.str.replace("_vol", "_vol_nf")
        df_agg = df_agg.merge(df_agg_nf, on=["year"] + groupby, how="left")
        fluxes_cols_nf = [x + "_nf" for x in FLUXES_COLS]
        df_agg[fluxes_cols_nf] = df_agg[fluxes_cols_nf].fillna(0)
        # Add the nf fluxes to the fluxes in ForAWS
        for col1, col2 in zip(FLUXES_COLS, fluxes_cols_nf):
            df_agg[col1] += df_agg[col2]

        # Compute NAI and GAI
        df_out = compute_nai_gai(df_agg, groupby=groupby)
        return df_out


    def df_agg_con_broad(self, groupby: Union[List[str], str]):
        """Net Annual Increment aggregated by status and con_broad. It WILL NOT work properly when there are transitions from con to broad and viceversa.
        Usage:
            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['ZZ'][-1]
            >>> # Net Annual Increment of the merchantable pool (nai_merch) and of
            >>> # all the above ground biomass (nai_agb) by status
            >>> nai_st = runner.post_processor.nai.df_agg_con_broad(["status", "con_broad"])
       
        """
        if isinstance(groupby, str):
            groupby = [groupby]
        if groupby != ["status", "con_broad"]:
            warnings.warn("This method was written for a group by status.")
        df = self.pools_fluxes_vol

        # Aggregate the sum of selected columns
        df_agg = (
            df.groupby(["year"] + groupby)[NAI_AGG_COLS].agg("sum").reset_index()
        )
        # Add NF movements to products back to ForAWS
        # Note this is a problem when we use grouping variables other than
        # "status" alone For example if groupby = ["status", "forest_type"]
        # the merge below generates the KeyError: 'forest_type'
        selector = df_agg["status"] == "NF"
        df_agg_nf = df_agg.loc[selector, ["year", "status", "con_broad"] + FLUXES_COLS].copy()
        df_agg_nf["status"] = "ForAWS"
        df_agg_nf.columns = df_agg_nf.columns.str.replace("_vol", "_vol_nf")
        df_agg = df_agg.merge(df_agg_nf, on=["year", "con_broad"] + groupby, how="left")
        fluxes_cols_nf = [x + "_nf" for x in FLUXES_COLS]
        df_agg[fluxes_cols_nf] = df_agg[fluxes_cols_nf].fillna(0)
        # Add the nf fluxes to the fluxes in ForAWS
        for col1, col2 in zip(FLUXES_COLS, fluxes_cols_nf):
            df_agg[col1] += df_agg[col2]
        # Compute NAI and GAI
        df_out_con_broad = compute_nai_gai(df_agg, groupby=groupby)
        df_out_con_broad = df_out_con_broad[df_out_con_broad["status"] != "NF"]
        return df_out_con_broad

    def df_agg_con_broad_climate(self, groupby: Union[List[str], str]):
        """Net Annual Increment aggregated by status and con_broad. It WILL NOT work properly when there are transitions from con to broad and viceversa.
        Usage:
            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['ZZ'][-1]
            >>> # Net Annual Increment of the merchantable pool (nai_merch) and of
            >>> # all the above ground biomass (nai_agb) by status
            >>> nai_st = runner.post_processor.nai.df_agg_con_broad(["status", "con_broad", "climate"])
       
        """
        if isinstance(groupby, str):
            groupby = [groupby]
        if groupby != ["status", "con_broad", "climate"]:
            warnings.warn("This method was written for a group by status.")
        df = self.pools_fluxes_vol

        # Aggregate the sum of selected columns
        df_agg = (
            df.groupby(["year"] + groupby)[NAI_AGG_COLS].agg("sum").reset_index()
        )
        # Add NF movements to products back to ForAWS
        # Note this is a problem when we use grouping variables other than
        # "status" alone For example if groupby = ["status", "forest_type"]
        # the merge below generates the KeyError: 'forest_type'
        selector = df_agg["status"] == "NF"
        df_agg_nf = df_agg.loc[selector, ["year", "status", "con_broad", "climate"] + FLUXES_COLS].copy()
        df_agg_nf["status"] = "ForAWS"
        df_agg_nf.columns = df_agg_nf.columns.str.replace("_vol", "_vol_nf")
        df_agg = df_agg.merge(df_agg_nf, on=["year", "con_broad", "climate"] + groupby, how="left")
        fluxes_cols_nf = [x + "_nf" for x in FLUXES_COLS]
        df_agg[fluxes_cols_nf] = df_agg[fluxes_cols_nf].fillna(0)
        # Add the nf fluxes to the fluxes in ForAWS
        for col1, col2 in zip(FLUXES_COLS, fluxes_cols_nf):
            df_agg[col1] += df_agg[col2]
        # Compute NAI and GAI
        df_out_con_broad = compute_nai_gai(df_agg, groupby=groupby)
        df_out_con_broad = df_out_con_broad[(df_out_con_broad["status"] != "NF")&(df_out_con_broad["status"] != "AR")]
        return df_out_con_broad
