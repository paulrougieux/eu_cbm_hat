"""Process the stock output from the model"""
from typing import List, Union
from functools import cached_property
from eu_cbm_hat.post_processor.harvest import ton_carbon_to_m3_ub
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ob
import pandas as pd

class Stock:
    """Compute dw stock indicators

    Usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.stock.volume_standing_stocks("year")
        >>> runner.post_processor.stock.volume_standing_stocks(["year", "forest_type"])

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        self.pools = self.parent.pools
        self.fluxes = self.parent.fluxes
        
    def volume_biomass_standing_stocks(self, groupby: Union[List[str], str] = None):
        """Estimate the mean ratio of standing stocks, ONLY merchantable"""
        if isinstance(groupby, str):
            groupby = [groupby]
        df = self.pools
        df = df.merge(self.parent.wood_density_bark_frac, on="forest_type")
        df = df[df ['status'] != 'NF']
        df["broad_standing_vol_ob"] = ton_carbon_to_m3_ob(df, "hardwood_merch")
        df["con_standing_vol_ob"] = ton_carbon_to_m3_ob(df, "softwood_merch")
        # Aggregate separately for softwood and hardwood
        #groupby = ['year','status', 'con_broad']
                  
        # Create a new column to identify the rows to be summed
        df_faws_ar = df[df['status'].isin(['AR', 'ForAWS'])]
        df_fnaws = df[df['status'].isin(['ForNAWS'])]

        cols_hard = ['hardwood_merch', 'hardwood_foliage', 'hardwood_other']

        cols_soft = ['softwood_merch', 'softwood_foliage','softwood_other']
      
        df_faws = df_faws_ar.assign(
                con_standing_biomass=df_faws_ar[cols_soft].sum(axis=1),
                broad_standing_biomass=df_faws_ar[cols_hard].sum(axis=1)
                ).groupby(groupby).agg(
                    con_standing_for_biomass=('con_standing_biomass', 'sum'),
                    broad_standing_for_biomass=("broad_standing_biomass", "sum"),
                    con_standing_for_volume=("con_standing_vol_ob", "sum"),
                    broad_standing_for_volume=("broad_standing_vol_ob", "sum"),
                    area=("area", "sum")
                ).reset_index()
            
        # rename the sum of AR and ForAWS as ForAWS
        df_faws['status'] = 'ForAWS'
        # Group by the new column and the other columns
        df_fnaws = df_fnaws.assign(
                con_standing_biomass=df_fnaws[cols_soft].sum(axis=1),
                broad_standing_biomass=df_fnaws[cols_hard].sum(axis=1)
                ).groupby(groupby).agg(
                    con_standing_for_biomass=('con_standing_biomass', 'sum'),
                    broad_standing_for_biomass=("broad_standing_biomass", "sum"),
                    con_standing_for_volume=("con_standing_vol_ob", "sum"),
                    broad_standing_for_volume=("broad_standing_vol_ob", "sum"),
                    area=("area", "sum")
                ).reset_index()
        df_fnaws['status'] = 'ForNAWS'
        df_for = pd.concat([df_faws, df_fnaws])
        # biomass 
        df_for['standing_stock_biomass'] = df_for['con_standing_for_biomass']+df_for['broad_standing_for_biomass']
        df_for['standing_stock_biomass_ha'] = df_for['standing_stock_biomass']/df_for['area']
        # volume
        df_for['standing_stock_volume'] = df_for['con_standing_for_volume']+df_for['broad_standing_for_volume']
        df_for['standing_stock_volume_ha'] = df_for['standing_stock_volume']/df_for['area']
        df_for["combo_name"] = self.combo_name
        df_for["iso2_code"] = self.runner.country.iso2_code
        df_for["country"] = self.runner.country.country_name
        df_for=df_for.reset_index()
        return df_for
    
    def dw_stock_ratio(self, groupby: Union[List[str], str] = None):
        """Estimate the mean ratio of standing stocks, dead_wood to merchantable
        
        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.stock.dw_stock_ratio("year")
        
        """

        
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

    def df_agg(self, groupby: Union[List[str], str] = None):
        """Aggregated stock data

        Particularly interesting to get information the Dead Organic Matter stock.

        DOM stock distinguished by areas that have been harvested and areas not
        harvested:

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> runner.post_processor.stock.df_agg(["year", "last_disturbance"])

        Check last disturbance type is 1 for rows where the condition is True

            >>> selected_cols = ["timestep", "disturbance_type", "last_disturbance_type", "time_since_last_disturbance"]
            >>> runner.post_processor.pools.query("last_disturbance_type == disturbance_type")[selected_cols]
            >>> #

        """
        if isinstance(groupby, str):
            groupby = [groupby]
        column_dict = {
            "merch": ["softwood_merch", "hardwood_merch"],
            "other": ["softwood_other", "hardwood_other"],
            "roots": [
                "softwood_fine_roots",
                "hardwood_fine_roots",
                "softwood_coarse_roots",
                "hardwood_coarse_roots",
            ],
            "foliage": [
                "softwood_foliage", "hardwood_foliage"
            ],
            
            "litter": [
                "above_ground_very_fast_soil",
                "above_ground_fast_soil",
                "above_ground_slow_soil",
            ],
            "dead_wood": [
                "softwood_stem_snag",
                "softwood_branch_snag",
                "hardwood_branch_snag",
                "hardwood_stem_snag",
                "below_ground_fast_soil",
                "medium_soil",
            ],

            "soil": [
                "below_ground_very_fast_soil",
                "below_ground_slow_soil"
            ]
        }

        
        df = self.parent.pools.copy()
        for key, cols in column_dict.items():
            df[key] = df[cols].sum(axis=1)
        df["dom"] = df["litter"] + df["dead_wood"]
        dist_types = self.parent.harvest.disturbance_types.copy()
        dist_types.rename(
            columns={
                "disturbance_type": "last_disturbance_type",
                "disturbance": "last_disturbance",
            },
            inplace=True,
        )
        df = df.merge(dist_types, on="last_disturbance_type")
        allowed_index = self.parent.classifiers_list
        allowed_index += [
            "year",
            "disturbance_type",
            "last_disturbance_type",
            "last_disturbance",
        ]
        missing_columns = set(groupby) - set(allowed_index)
        if bool(missing_columns):
            raise ValueError(
                f"Columns {missing_columns} are not allowed as groupby variables."
            )
        cols = ["area"] + list(column_dict.keys()) + ["dom"]
        df_agg = df.groupby(groupby)[cols].agg("sum").reset_index()
        return df_agg

    def dw_merch_stock_age_class(self, groupby: Union[List[str], str] = None):
        """Estimate the mean ratio of standing stocks, dead_wood to merchantable
        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.stock.dw_merch_stock_age_class("year")
        """
        if isinstance(groupby, str):
            groupby = [groupby]
        df = self.pools
        df['age_class'] = df.age // 10 + 1
        df['age_class'] = 'AGEID' + df.age_class.astype(str)
        # Aggregate separately for softwood and hardwood
        df_agg = df.groupby(groupby+ ['age_class']).agg(
            softwood_stem_snag_tc=("softwood_stem_snag", "sum"),
            softwood_merch_tc=("softwood_merch", "sum"),
            hardwood_stem_snag_tc=("hardwood_stem_snag", "sum"),
            hardwood_merch_tc=("hardwood_merch", "sum"),
            #area=("area", sum),
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
        #df_agg["standing_dw_c_per_ha"] = (
        #    df_agg["hardwood_stem_snag_tc"] + df_agg["softwood_stem_snag_tc"]
        #) / df_agg["area"]
        #df_agg["laying_dw_c_per_ha"] = df_agg["medium_tc"] / df_agg["area"]
        df_agg=df_agg.query('year == 2025 | year == 2030')
        return df_agg
