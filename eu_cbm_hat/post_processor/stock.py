"""Process the stock output from the model"""
from typing import List, Union
from functools import cached_property
from eu_cbm_hat.post_processor.harvest import ton_carbon_to_m3_ub


class Stock:
    """Compute dw stock indicators

    Usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.stock.dw_stock_ratio("year")
        >>> runner.post_processor.stock.dw_stock_ratio(["year", "forest_type"])

    """

    def __init__(self, parent):
        self.parent = parent
        self.pools = self.parent.pools
        self.fluxes = self.parent.fluxes

    def dw_stock_ratio(self, groupby: Union[List[str], str] = None):
        """Estimate the mean ratio of standing stocks, dead_wood to merchantable"""
        if isinstance(groupby, str):
            groupby = [groupby]
        df = self.pools

        # Aggregate separately for softwood and hardwood
        df_agg = df.groupby(groupby).agg(
            softwood_stem_snag_tc=("softwood_stem_snag", "sum"),
            softwood_merch_tc=("softwood_merch", "sum"),
            hardwood_stem_snag_tc=("hardwood_stem_snag", "sum"),
            hardwood_merch_tc=("hardwood_merch", "sum"),
            area=("area", sum),
            medium_tc=("medium_soil", "sum"),
        )

        df_agg.reset_index(inplace=True)
        df_agg["softwood_standing_dw_ratio"] = (
            df_agg["softwood_stem_snag_tc"] / df_agg["softwood_merch_tc"]
        )
        df_agg["hardwood_standing_dw_ratio"] = (
            df_agg["hardwood_stem_snag_tc"] / df_agg["hardwood_merch_tc"]
        )
        # agregate over con and broad
        df_agg["standing_dw_c_per_ha"] = (
            df_agg["hardwood_stem_snag_tc"] + df_agg["softwood_stem_snag_tc"]
        ) / df_agg["area"]
        df_agg["laying_dw_c_per_ha"] = df_agg["medium_tc"] / df_agg["area"]

        return df_agg

    def dw_contribution_harvest(self, groupby: Union[List[str], str] = None):
        """Estimate the mean ratio of standing stocks, dead_wood to merchantable"""
        if isinstance(groupby, str):
            groupby = [groupby]
        df = self.fluxes
        # Aggregate separately for softwood and hardwood
        df_agg = df.groupby("year").agg(
            softwood_merch_prod=("softwood_merch_to_product", "sum"),
            softwood_snag_prod=("softwood_stem_snag_to_product", "sum"),
            hardwood_merch_prod=("softwood_merch_to_product", "sum"),
            hardwood_snag_prod=("hardwood_stem_snag_to_product", "sum"),
        )
        df_agg["softwood_snag_harv_contrib"] = df_agg["softwood_snag_prod"] / (
            df_agg["softwood_snag_prod"] + df_agg["softwood_merch_prod"]
        )
        df_agg["hardwood_snag_harv_contrib"] = df_agg["hardwood_snag_prod"] / (
            df_agg["hardwood_snag_prod"] + df_agg["hardwood_merch_prod"]
        )
        return df_agg
