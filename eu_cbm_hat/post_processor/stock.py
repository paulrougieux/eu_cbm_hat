"""Process the stock output from the model"""
from typing import List, Union
from functools import cached_property


class Stock:
    """Compute stock indicators

    Usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.stock.dw_stock_ratio("year")
        >>> runner.post_processor.stock.dw_stock_ratio(["year", "forest_type"])

    """

    def __init__(self, parent):
        self.parent = parent
        self.pools = self.parent.pools

    def dw_stock_ratio(self, groupby: Union[List[str], str] = None):
        """Estimate the mean ratio of standing stocks, dead_wood to merchantable"""
        if isinstance(groupby, str):
            groupby = [groupby]
        df = self.pools
        df["softwood_dw_ratio"] = df["softwood_stem_snag"] / df["softwood_merch"]
        df["hardwood_dw_ratio"] = df["hardwood_stem_snag"] / df["hardwood_merch"]
        # Aggregate separately for softwood and hardwood
        df_agg = df.groupby(groupby).agg(
            softwood_stem_snag=("softwood_stem_snag", "sum"),
            softwood_merch=("softwood_merch", "sum"),
            hardwood_stem_snag=("hardwood_stem_snag", "sum"),
            hardwood_merch=("hardwood_merch", "sum"),
            softwood_dw_ratio_mean=("softwood_dw_ratio", "mean"),
            hardwood_dw_ratio_mean=("hardwood_dw_ratio", "mean"),
        )
        df_agg.reset_index(inplace=True)
        df_agg["softwood_dw_ratio"] = df_agg["softwood_stem_snag"] / df_agg["softwood_merch"]
        df_agg["hardwood_dw_ratio"] = df_agg["hardwood_stem_snag"] / df_agg["hardwood_merch"]
        return df_agg
