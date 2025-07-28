"""
The purpose of this script is to compute the sink for one country
"""

from typing import List, Union
from functools import cached_property
import re
import numpy as np
import pandas


POOLS_DICT = {
    "living_biomass": [
        "softwood_merch",
        "softwood_other",
        "softwood_foliage",
        "softwood_coarse_roots",
        "softwood_fine_roots",
        "hardwood_merch",
        "hardwood_foliage",
        "hardwood_other",
        "hardwood_coarse_roots",
        "hardwood_fine_roots",
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
        "below_ground_slow_soil",
    ],
}

FLUXES_DICT = {
    "loss_from_living_biomass": [
        # transfers to products
        "softwood_merch_to_product",
        "softwood_other_to_product",
        "hardwood_merch_to_product",
        "hardwood_other_to_product",
        # any direct flux to air
        "disturbance_merch_to_air",
        "disturbance_fol_to_air",
        "disturbance_oth_to_air",
        "disturbance_coarse_to_air",
        "disturbance_fine_to_air",
    ],
    "loss_from_litter": [
        "decay_v_fast_ag_to_air",
        "decay_fast_ag_to_air",
        "decay_slow_ag_to_air",
    ],
    "loss_from_dead_wood": [
        "softwood_stem_snag_to_product",
        "softwood_branch_snag_to_product",
        "hardwood_stem_snag_to_product",
        "hardwood_branch_snag_to_product",
        "decay_sw_stem_snag_to_air",
        "decay_sw_branch_snag_to_air",
        "decay_hw_stem_snag_to_air",
        "decay_hw_branch_snag_to_air",
        "decay_fast_bg_to_air",
        "decay_medium_to_air",
    ],
    "loss_from_soil": [
        "decay_v_fast_bg_to_air",
        "decay_slow_bg_to_air",
    ],
    "loss_from_non_co2_emissions": [
        "disturbance_bio_ch4_emission",
        "disturbance_bio_co_emission",
        "disturbance_domch4_emission",
        "disturbance_domco_emission",
    ],
}


def generate_all_combinations_and_fill_na(df, groupby):
    """Generate a DataFrame with all combinations of year, status, region, and
    climate.
    """
    groupby_area_diff = groupby.copy()
    # Prepare all combinations of groupby variables except year
    groupby_area_diff.remove("year")
    all_groups = df[groupby_area_diff].drop_duplicates()
    years = list(df["year"].unique())
    combi_dict = {
        "year": [y for y in years for _ in range(len(all_groups))],
    }
    for var in groupby_area_diff:
        combi_dict[var] = all_groups[var].tolist() * len(years)
    all_combinations = pandas.DataFrame(combi_dict)
    # Do a full join to make NA values apparent in order to compute the diff in
    # area or stock later
    df = df.merge(all_combinations, how="outer", on=["year"] + groupby_area_diff)
    df.fillna(0, inplace=True)
    df.sort_values(groupby_area_diff + ["year"], inplace=True)
    # Compute the area diff and check the diff sums to zero
    df["area_diff"] = df.groupby(groupby_area_diff)["area"].transform(
        lambda x: x.diff()
    )
    diff_sum = abs(df.groupby("year")["area_diff"].sum())
    assert all(diff_sum < 100)
    return df


class Sink:
    """Compute the forest carbon sink in living biomass, dead organic matter
    and soil pools

    Here are the methods to load intermediate data frames used in the
    computation of the sink

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]

        >>> runner.post_processor.sink.pools
        >>> runner.post_processor.sink.fluxes
        >>> runner.post_processor.sink.nf_soil_stock
        >>> groupby_sink = ["year", "region", "climate", "status"]
        >>> runner.post_processor.sink.emissions_from_deforestation(groupby=groupby_sink)
        >>> runner.post_processor.sink.emissions_from_deforestation(groupby=["year"])
        >>> runner.post_processor.sink.deforestation_deduction
        >>> runner.post_processor.sink.df
        >>> runner.post_processor.sink.df_agg("year")
        >>> runner.post_processor.sink.df_long

    Display the number of rows going through land class changes and disturbances

        >>> pools = runner.post_processor.sink.pools.copy()
        >>> selector = pools["time_since_land_class_change"] > 1
        >>> pools["time_since_land_class_change"] = pools["time_since_land_class_change"].astype(str)
        >>> pools.loc[selector, "time_since_land_class_change"] = "greater than one"
        >>> selector = pools["time_since_last_disturbance"] > 1
        >>> pools["time_since_last_disturbance"] = pools["time_since_last_disturbance"].astype(str)
        >>> pools.loc[selector, "time_since_last_disturbance"] = "greater than one"
        >>> selected_cols = ["time_since_land_class_change", "status", "land_class", "time_since_last_disturbance"]
        >>> print(pools.value_counts(selected_cols, sort=False))
        >>> print("\\nOnly stands affected by deforestation disturbances")
        >>> print(pools.query("last_disturbance_type==7").value_counts(selected_cols, sort=False))

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.pools = self.parent.pools
        self.fluxes = self.parent.fluxes
        # Pools and fluxes aggregation parameters
        self.pools_dict = POOLS_DICT.copy()
        self.pools_list = list(
            {item for sublist in self.pools_dict.values() for item in sublist}
        )
        self.fluxes_dict = FLUXES_DICT.copy()
        self.groupby_sink = ["year", "region", "climate", "status"]

    def __repr__(self):
        return '%s object code "%s"' % (self.__class__, self.runner.short_name)

    @cached_property
    def nf_soil_stock(self):
        """Get the slow soil pool content per hectare of non forested stands.

        Used to compute the sink of afforested land in the first year of
        afforestation. Keep only stands that have never been disturbed in the
        simulation (time_since_land_class_change == -1), exclude NF stands that
        are the result of deforestation during the simulation period.
        """
        df = self.pools
        selector = df["status"].str.contains("NF")
        selector &= df["time_since_land_class_change"] == -1
        nf_soil = df.loc[selector].copy()
        nf_soil["nf_slow_soil_per_ha"] = (
            nf_soil["below_ground_slow_soil"] / nf_soil["area"]
        )
        # Group by region and climate and calculate the standard deviation
        groupby_soil = ["region", "climate"]
        nf_soil["std_dev"] = nf_soil.groupby(groupby_soil)[
            "nf_slow_soil_per_ha"
        ].transform("std")
        # Check that nf_slow_soil_per_ha always have the same value across grouping
        # variables
        selector = nf_soil["std_dev"] > 1e-2
        if any(selector):
            msg = "The NF non forested soil pool content per hectare"
            msg += " is not homogeneous for some region and climate groups."
            cols_to_show = ["year", "status", "region", "climate"]
            cols_to_show += [
                "time_since_land_class_change",
                "nf_slow_soil_per_ha",
                "std_dev",
            ]
            msg += f"{nf_soil[cols_to_show]}"
            raise ValueError(msg)
        # Aggregate smaller data frame with columns necessary for the join
        nf_soil_agg = nf_soil.groupby(groupby_soil)["nf_slow_soil_per_ha"].agg("mean")
        nf_soil_agg = nf_soil_agg.reset_index()
        return nf_soil_agg

    def emissions_from_deforestation(
        self,
        groupby: Union[List[str], str],
        fluxes_dict: dict = None,
        current_year_only: bool = False,
    ):
        """Emissions from deforested areas moving from forested to NF

        Deforestation emissions are only reported for the year when event happens.
        Indeed, a small amount of legacy emissions occur, as reflected by
        "decay_domco2_emission"evolution after deforestation for any identifier We
        considered it as nonrelevant, anyway atributable to post-deforestation land
        use. Deforestation emissions can be identified by dist_type = 7, OR,
        "status = "NF" and "time_since_land_class_change > 0" land transfers from
        occur ForAWS/NAWS, or even AR, to NF. join this df to sink df_all.

        Example use:

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> runner.post_processor.sink.emissions_from_deforestation(groupby=["year"])
            >>> runner.post_processor.sink.emissions_from_deforestation(groupby=["year", "region"])

            >>> # TODO update this example
            >>> def_em_y = apply_to_all_countries(emissions_from_deforestation, combo_name="reference", groupby="year")

        """
        if fluxes_dict is None:
            fluxes_dict = self.fluxes_dict.copy()
        df = self.fluxes.copy()
        # Keep only deforestation events
        selector = df["time_since_land_class_change"] > 0
        selector &= df["last_disturbance_type"] == 7
        # Used to compute the deforestation deduction for the current year only
        # when computing the sink
        if current_year_only:
            selector &= df["time_since_last_disturbance"] == 1
            df = df.loc[selector]

        for key in fluxes_dict:
            # Aggregate all pool columns to one pool value for this key
            df[key] = df[fluxes_dict[key]].sum(axis=1)

        cols = list(fluxes_dict.keys())
        # Aggregate
        df_agg = df.groupby(groupby)[cols].agg("sum").reset_index()

        return df_agg

    @cached_property
    def deforestation_deduction(self):
        """Pool content and fluxes from the area subject to deforestation Prepare a
        data frame to deduce carbon related to deforestation"""
        # Aggregate by the classifier for which it is possible to compute a
        # difference in pools.
        df = self.pools
        selector = df["last_disturbance_type"] == 7
        selector &= df["time_since_last_disturbance"] == 1
        df7 = df.loc[selector].copy()
        df7["area_deforested_current_year"] = df["area"]
        selected_columns = self.pools_list + ["area_deforested_current_year"]
        df7_agg = df7.groupby(self.groupby_sink)[selected_columns].sum().reset_index()
        def_em = self.emissions_from_deforestation(
            groupby=self.groupby_sink, fluxes_dict=FLUXES_DICT, current_year_only=True
        )
        deforest = df7_agg.merge(def_em, on=self.groupby_sink, how="outer")
        if deforest.status.unique() != "NF":
            msg = "After deforestation the status should be NF only. "
            msg += f"but it is {deforest.status.unique()}"
            raise ValueError(msg)
        status_foraws = "ForAWS"
        if status_foraws not in df["status"].unique():
            msg = f"{status_foraws} not in df['status']: {df['status'].unique()}"
            raise ValueError(msg)
        # Replace status NF by ForAWS
        deforest["status"] = status_foraws
        # Compute the deforestation deduction
        for key, pools in POOLS_DICT.items():
            deforest[key + "_stock"] = deforest[pools].sum(axis=1)
            col_name = deforest.columns[deforest.columns.str.contains("_from_" + key)][
                0
            ]
            deforest[key + "_deforest_deduct"] = (
                deforest[key + "_stock"] + deforest[col_name]
            )
        
        return deforest

    @cached_property
    def df(self):
        """Compute the stock change and the sink (in tons of CO2 eq.)

        Aggregate by the classifier for which it is possible to compute a
        difference in pools. During land use transition implementing afforestation
        and deforestation, some classifier sets may change, while other classifiers
        such as region and climate remain constant. It is only possible to compute
        the stock change along classifiers that remain constant.

        Normalise the sink by the area. For example in case of afforestation the
        stock change should take into account the change of area from t-1 to t.
        Steps to correct for the area change:

            - Group by ["year", "region", "climate", "status",
                        "afforestation_in_current_year"] and sum pools
            - Aggregate all pool columns to one pool value for each key in the
              pools_dict dictionary
            - Compute the stock change per hectare
                S{t}/A{t} - S{t-1}/A{t-1}
            - Deduce NF soil pool when there is afforestation in the first year
            - Compute the CO2 eq. sink per hectare
            - Multiply the sink by the area at time t
            - Remove non forested land
            - Group by final grouping variables given in the groupby argument.

        See usage example in the function sink_one_country.

        Investigate issues with area changes

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> df = runner.post_processor.sink.df
            >>> df["area_diff"] = df["area"] - df["area_tm1"]
            >>> cols = df.columns[df.columns.str.contains("area")].to_list()
            >>> cols += ["year", "region", "climate", "status"]
            >>> df[cols].to_csv("/tmp/lu_area.csv")

        """
        groupby_sink = self.groupby_sink.copy()
        # Aggregate by the classifier for which it is possible to compute a
        # difference in pools.
        selected_columns = self.pools_list.copy()
        selected_columns += [
            "area",
            "area_afforested_current_year",
            "area_deforested_current_year",
        ]
        df = self.pools.groupby(groupby_sink)[selected_columns].sum().reset_index()
        # Add the soil stock in NF stands (that have not been deforested in the
        # simulation)
        df = df.merge(self.nf_soil_stock, on=["region", "climate"], how="left")
        # Aggregate on the groupby_sink columns and fill na before computing the diff
        df = generate_all_combinations_and_fill_na(df, groupby=groupby_sink)

        # Join deforestation deductions to the main sink data frame
        deforest = self.deforestation_deduction
        selected_cols = deforest.columns[
            deforest.columns.str.contains("_deduct")
        ].to_list()
        df = df.merge(
            deforest[groupby_sink + selected_cols], on=groupby_sink, how="left"
        )
        df[selected_cols] = df[selected_cols].fillna(0)

       # Remove year from the grouping variables to compute the diff over years
        groupby_sink.remove("year")

        # Arrange by group variables with year last to prepare for diff() and shift()
        df.sort_values(groupby_sink + ["year"], inplace=True)
        # Add area at {t-1} to compare with area at t
        df["area_tm1"] = df.groupby(groupby_sink)["area"].transform(lambda x: x.shift())
        # Check that the total area didn't change between t-1 and t
        # Note: the status can change but the total area should remain constant
        df_check = df.groupby("year")[["area", "area_tm1"]].agg("sum")
        df_check = df_check[df_check.index > df_check.index.min()]
        try:
            np.testing.assert_allclose(df_check["area_tm1"], df_check["area"], atol=100)
        except AssertionError as error:
            msg = "The total area changed between t-1 and t"
            raise AssertionError(msg) from error

        for key in self.pools_dict:
            # Aggregate all pool columns to one pool value for this key
            df[key + "_stock"] = df[self.pools_dict[key]].sum(axis=1)

            # Keep stock at {t-1} for debugging purposes
            df[key + "_stock_tm1"] = df.groupby(groupby_sink)[key + "_stock"].transform(
                lambda x: x.shift()
            )

            # Compute the stock change per hectare
            # TODO: change the computation of the stock change so that
            # It becomes possible to analyse stock_t, stock_{t-1}
            df[key + "_stk_ch"] = df.groupby(groupby_sink)[key + "_stock"].transform(
                lambda x: x.diff()
            )

            # Remove the NF soil pool content for the area afforested in current year
            if "soil" in key:
                nf_slow_soil = (
                    df["nf_slow_soil_per_ha"] * df["area_afforested_current_year"]
                )
                df[key + "_stk_ch"] = df[key + "_stk_ch"] - nf_slow_soil

            # Remove the deforestation stock and emissions
            df[key + "_stk_ch"] += df[key + "_deforest_deduct"]

            # Compute the CO2 eq. Sink
            df[key + "_sink"] = df[key + "_stk_ch"] * -44 / 12
            # remove NF which is the land in the inventory.csv available for afforestation,but keep deforested land which is also NF
            df.loc[df['status'] == 'NF', ['area', 'area_tm1']] = 0

        # Remove non forested land
        #selector = df["status"].str.contains("NF")
        #df = df.loc[~selector]
        return df

    def df_agg(self, groupby: Union[List[str], str] = None):
        """Aggregated sink data frame"""
        if isinstance(groupby, str):
            groupby = [groupby]
        if groupby is None:
            groupby = self.groupby_sink.copy()
        if not set(groupby).issubset(self.groupby_sink):
            msg = f"Can only group by {self.groupby_sink}. "
            msg += f"{set(groupby) - set(self.groupby_sink)}"
            msg += " not allowed as a groupby value."
            raise ValueError(msg)

        # Keep the area, pool and sink information
        cols = self.df.columns
        selected_cols = [
            "area",
            "area_afforested_current_year",
            "area_deforested_current_year",
        ]
        selected_cols += cols[cols.str.contains("stock")].to_list()
        selected_cols += cols[cols.str.contains("sink$")].to_list()
        selected_cols += cols[cols.str.contains("deforest_deduct")].to_list()
        # Aggregate selected columns by the final grouping variables
        df_agg = self.df.groupby(groupby)[selected_cols].agg("sum").reset_index()
        return df_agg

    @cached_property
    def df_long(self):
        """Sink and stock in long format for plotting


        This data frame contains a sink and a stock column that can be used for
        plotting faceted plots, using for example facets along classifiers and
        line colours for the different pools.

        Units:
            - The sink is in tons of CO2 eq.
            - The stock is in tons of carbon
            - The data frame also contains sink and stock values per hectare
              for comparison purposes.
        """
        df = self.df.copy()
        index = self.groupby_sink.copy()
        sink_cols = df.columns[df.columns.str.contains("sink")].to_list()
        stock_cols = [re.sub("sink", "stock", x) for x in sink_cols]
        combined_cols = sink_cols + stock_cols
        # Melt sink and stock columns to long format
        df_long = df.melt(
            id_vars=index + ["area"],
            value_vars=combined_cols,
            var_name="variable",
            value_name="value"
        )
        df_long["pool"] = df_long["variable"].str.replace("_sink|_stock", "", regex=True)
        df_long["metric"] = df_long["variable"].str.extract("(sink|stock)")
        # Pivot sink and stock as columns
        result = df_long.pivot_table(
            index=index + ["area", "pool"],
            columns="metric",
            values="value",
            aggfunc="first"
        ).reset_index()
        result["sink_per_ha"] = result["sink"] / result["area"]
        result["stock_per_ha"] = result["stock"] / result["area"]
        # Remove the multi-level column index name
        result.columns.name = None
        return result

