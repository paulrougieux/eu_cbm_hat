"""

This module computes the Harvested Wood Products sink.

# Context

Regulation (EU) 2018/841 (amended 2023)
[https://eur-lex.europa.eu/eli/reg/2018/841/oj/eng](https://eur-lex.europa.eu/eli/reg/2018/841/oj/eng)
establishes accounting rules for emissions and removals from land use,
including harvested wood products throughout their lifecycle. In particular
paragraph 19:

> "(19) The increased sustainable use of harvested wood products can substantially
> limit emissions by the substitution effect and enhance removals of greenhouse
> gases from the atmosphere. The accounting rules should ensure that Member
> States accurately and transparently reflect in their LULUCF accounts changes
> in the carbon pool of harvested wood products when such changes take place,
> in order to recognise and incentivise the enhanced use of harvested wood
> products with long life-cycles. The Commission should provide guidance on
> issues related to the methodology concerning the accounting for harvested
> wood products."

The EC applies the 2019 Refinement to the 2006 IPCC Guidelines for National
Greenhouse Gas Inventories Volume 4 chapter 12:
https://www.ipcc-nggip.iges.or.jp/public/2019rf/vol4.html

Activity data quantify carbon transfers from harvested forest biomass into
product pools with specific decay rates. When trees are harvested, carbon in
wood products persists for different durations: long-lived products like
structural timber (~35 years half-life), medium-term products like furniture
and paper (2-25 years), or immediate emission when burned for energy. HWP
accounting tracks carbon entering from harvest, allocation to product
categories, decay rates, emissions from combustion/decomposition, and benefits
from recycling and substitution.


# Choosing a scenario to compute the HWP sink using different assumptions

The CBM has to be run first, in order to compute the simulated harvest amounts
moving to the products pool. Harvested Wood Products scenarios are defined as
part of the post processor in a function in
 The
parameters of that function simply modify properties of the HWP class below
(see the init method of the HWP class). You can change these properties
directly yourself as well as illustrated below.

The CBM has to be run first, in order to compute the simulated harvest amounts
moving to the products pool. Harvested Wood Products scenarios are defined as
part of the post processor in a function in
[select_hwp_scenario](eu_cbm_hat/post_processor/select_hwp_scenario.html). The
parameters of that function simply modify properties of the HWP class below
(see the init method of the HWP class). You can change these properties
directly yourself as illustrated in some methods below.


"""

from functools import cached_property
import numpy as np
import re
import warnings
import pandas
from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
from eu_cbm_hat.info.silviculture import keep_clfrs_without_question_marks
from eu_cbm_hat import eu_cbm_data_pathlib


class HWP:
    """Compute the Harvested Wood Products Sink

    Class Properties:

    - n_years_dom_frac: Number of common years used to calculate the fraction
      of domestic semi-finished products.
    - hwp_frac_scenario: Specifies which HWP fraction scenario to apply for
      allocating harvested wood to different product categories.
    - add_recycling: Controls whether recycling information is included in the
      HWP accounting calculations.
    - no_export_no_import: When False, export-import flows are accounted for
      (default option). When set to True, export-import is not accounted and
      factors are set to 1.
    - n_years_window_flux_by_grade: Window size in years for smoothing peaks in
      the flux_by_grade data.
    - n_peaks_to_remove_flux_by_grade: Number of peaks to remove when smoothing
      the flux_by_grade data.
    - year_start_smoothing_flux_by_grade: Starting year for applying smoothing
      to flux_by_grade, calculated as base_year minus 3 years.

    The class property hwp_frac_scenario can have different meanings:

        1. "default" reuses historical fractions from the the last n reported
           years
        2. <hwp scenario name> uses fraction specified in
           hwp_fraction_semifinished_scenario.csv
        3. "expected" use absolute production of semi finished products.
            These are exogenous values from a projection of an economic model.

    Example usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.irw_frac
        >>> runner.post_processor.hwp.fluxes_to_products
        >>> runner.post_processor.hwp.fluxes_to_irw
        >>> runner.post_processor.hwp.fluxes_by_age_to_dbh
        >>> runner.post_processor.hwp.fluxes_by_grade_dbh
        >>> runner.post_processor.hwp.fluxes_by_grade
        >>> runner.post_processor.hwp.build_hwp_stock
        >>> print(runner.post_processor.hwp.stock_sink_results)

    Compute results for the default scenario and for another hwp scenario

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> hwp = runner.post_processor.hwp
        >>> print("Fractions before modification, in the default scenario")
        >>> print(hwp.fraction_semifinished_n_years_mean)
        >>> print(hwp.fraction_semifinished)
        >>> print(hwp.prod_from_dom_harv_sim)
        >>> print(hwp.stock_sink_results)

    Change the fraction semi finished products

        >>> runner.post_processor.hwp.hwp_frac_scenario = "more_sw"
        >>> print("Fractions in the scenario")
        >>> print(hwp.fraction_semifinished)
        >>> # Display the effect on the production from domestic harvest
        >>> print(hwp.prod_from_dom_harv_sim)
        >>> # Display the effect on the final results
        >>> print(hwp.stock_sink_results)

    Set export import factors to one. In other words, assume that all secondary
    products production is made from domestic industrial roundwood harvest.

        >>> hwp = runner.post_processor.hwp
        >>> print("no_export_no_import:", hwp.no_export_no_import)
        >>> hwp.no_export_no_import = False
        >>> print(hwp.prod_from_dom_harv_stat)
        >>> print(hwp.stock_sink_results)
        >>> # Change the export import factors to one
        >>> hwp.no_export_no_import = True
        >>> print(hwp.prod_from_dom_harv_stat)
        >>> print(hwp.stock_sink_results)

    Switch to fraction when the hwp semi finished products scenario is not defined in combos

        from eu_cbm_hat.core.continent import continent
        runner = continent.combos['pikfair'].runners['LU'][-1]
        print(runner.post_processor.hwp.semifinished_prod_scenario)
        runner = continent.combos['reference'].runners['LU'][-1]
        print(runner.post_processor.hwp.semifinished_prod_scenario)

    TODO:

        - Illustrate change of number of years used to compute domestic factors
          self.n_years_dom_frac = 10

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        self.classif_list = self.parent.classifiers_list
        self.base_year = self.runner.country.base_year
        # Semifinished products
        self.semifinished_products = ["sw_broad", "sw_con", "pp", "wp"]
        # IRW fractions
        self.irw_frac = self.parent.irw_frac
        # Use pool fluxes to get area and age class as well
        self.pools_fluxes = self.runner.output.pool_flux
        # Number of common years to be used to compute the
        # Fraction domestic semi finished products
        self.n_years_dom_frac = 3
        # Define how we compute semifinished production from domestic harvest
        # 1. "default" reuses historical fractions from the last n reported
        #    years
        # 2. <hwp scenario name> uses fraction specified in
        #    hwp_fraction_semifinished_scenario.csv
        self.hwp_frac_scenario = "default"
        # 3. "expected" use absolute production of semi finished products from
        #    an economic model. These are exogenous values from a projection of an
        #    economic model.
        try:
            self.semifinished_prod_scenario = self.runner.combo.config[
                "semi_finished_production"
            ]
        except KeyError:
            self.semifinished_prod_scenario = "fraction"
        # Add recycling information or not
        self.add_recycling = True
        # Set export import factors to 1, namely FALSE (for which export-import
        # is accounted, the default option). When set to TRUE,
        # the export-import is not accounted.
        self.no_export_no_import = False
        # Number of years to compute the ratio between historical and simulation
        # sawlogs and pulpwood amounts
        self.n_years_fluxes_by_grade_mean = 3

    def __repr__(self):
        return '%s object code "%s"' % (self.__class__, self.runner.short_name)

    @property
    def prod_from_dom_harv_stat(self) -> pandas.DataFrame:
        """Production from domestic harvest statistiscs from hwp_common_input"""
        hwp_common_input.no_export_no_import = self.no_export_no_import
        return hwp_common_input.prod_from_dom_harv_stat

    @cached_property
    def fluxes_to_products(self) -> pandas.DataFrame:
        """Fluxes to products retain from the cbm output the all transfers to
        products pool Remove lines where there are no fluxes to products. Keep
        only lines with positive flues.

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> runner.post_processor.hwp.fluxes_to_products
        """
        index_cols = ["year", "area", "disturbance_type", "age_class"]
        fluxes_cols = [
            "softwood_merch_to_product",
            "softwood_other_to_product",
            "softwood_stem_snag_to_product",
            "softwood_branch_snag_to_product",
            "hardwood_merch_to_product",
            "hardwood_other_to_product",
            "hardwood_stem_snag_to_product",
            "hardwood_branch_snag_to_product",
        ]
        cols_of_interest = self.classif_list + index_cols + fluxes_cols
        df = self.pools_fluxes[cols_of_interest]
        # Keep only lines where there are fluxes to products.
        selector = df[fluxes_cols].sum(axis=1) > 0
        df = df.loc[selector].reset_index(drop=True)
        # Merge with IRW fractions
        clfrs_noq = keep_clfrs_without_question_marks(self.irw_frac, self.classif_list)
        df = df.merge(
            self.irw_frac,
            how="left",
            on=clfrs_noq + ["disturbance_type", "year"],
            suffixes=("", "_irw_frac_1"),
        )
        return df

    @cached_property
    def fluxes_to_irw(self) -> pandas.DataFrame:
        """Fluxes to Industrial Roundwood Aggregated by index Extract the IRW
        only, e.g. separate the df as IRW ub exclude bark, because cbm output
        includes the barkand add it to FW. E.g., "df ['softwood_merch']" is the
        IRW fraction.
        """
        df = self.fluxes_to_products
        # Add bark fraction
        df = df.merge(self.parent.wood_density_bark_frac, on="forest_type", how="left")

        # fmt: off
        # Keep only the IRW fraction by multiplying with the fractions coming from self.irw_frac
        df["tc_soft_irw_merch"] = (df["softwood_merch_to_product"] * df["softwood_merch_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_soft_irw_other"] = (df["softwood_other_to_product"] * df["softwood_other_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_soft_irw_stem_snag"] = (df["softwood_stem_snag_to_product"] * df["softwood_stem_snag_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_soft_irw_branch_snag"] = (df["softwood_branch_snag_to_product"] * df["softwood_branch_snag_irw_frac"] * (1 - df["bark_frac"]))

        df["tc_hard_irw_merch"] = (df["hardwood_merch_to_product"] * df["hardwood_merch_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_hard_irw_other"] = (df["hardwood_other_to_product"] * df["hardwood_other_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_hard_irw_stem_snag"] = (df["hardwood_stem_snag_to_product"] * df["hardwood_stem_snag_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_hard_irw_branch_snag"] = (df["hardwood_branch_snag_to_product"] * df["hardwood_branch_snag_irw_frac"] * (1 - df["bark_frac"]))
        # fmt: on

        # Aggregate
        index = [
            "year",
            "forest_type",
            "mgmt_type",
            "mgmt_strategy",
            "con_broad",
            "age_class",
        ]
        tc_cols = df.columns[df.columns.str.contains("tc_")]
        # Aggregate over the index
        df_agg = df.groupby(index)[tc_cols].agg("sum")
        # Sum fluxes columns together into one tc_irw column
        df_agg = df_agg[tc_cols].sum(axis=1).reset_index()
        df_agg.rename(columns={0: "tc_irw"}, inplace=True)
        return df_agg

    @cached_property
    def fluxes_by_age_to_dbh(self) -> pandas.DataFrame:
        """Allocate fluxes by age to a dbh_alloc distrubution

        dbh_allo is the allocation data frame. We merge it with the fluxes to irw.
        """
        # Select data for one country only
        dbh_alloc = hwp_common_input.irw_allocation_by_dbh
        selector = dbh_alloc["country"] == self.runner.country.iso2_code
        dbh_alloc = dbh_alloc.loc[selector]
        # Merge with fluxes
        index = ["mgmt_type", "mgmt_strategy", "age_class", "forest_type"]
        df = self.fluxes_to_irw.merge(dbh_alloc, on=index, how="left")
        # Multiply old tc_irw with the fraction
        df["tc_irw"] = df["tc_irw"] * df["fraction_theoretical_volume"]
        # Reaggregate and check that values didn't change
        index = [
            "year",
            "forest_type",
            "mgmt_type",
            "mgmt_strategy",
            "con_broad",
            "age_class",
        ]
        df_agg = df.groupby(index)["tc_irw"].agg("sum")
        df_comp = self.fluxes_to_irw.merge(
            df_agg, on=index, how="left", suffixes=("_before", "_after")
        )
        selector = (df_comp["year"] > 2020) & (
            ~np.isclose(df_comp["tc_irw_before"], df_comp["tc_irw_after"])
        )
        if any(selector):
            msg = f"\n For post-2020, the following tc_irw values don't match between "
            msg += "input before and after dbh allocation\n"
            msg += f"i.e., allocation on the specified age_class missing because incomplete input in irw_allocation_by_dbh.csv\n"
            msg += f" {df_comp.loc[selector]}"
            warnings.warn(msg)
        return df

    @cached_property
    def fluxes_by_grade_dbh(self) -> pandas.DataFrame:
        """Allocate fluxes by age to a dbh_alloc distribution

        Returns a proportion by species, grade and db_class and also tc_irw.
        """
        # Select the country for nb grading
        nb_grading = hwp_common_input.nb_grading
        selector = nb_grading["country"] == self.runner.country.iso2_code
        nb_grading = nb_grading.loc[selector]
        # Aggregate previous data frame by genus
        df = self.fluxes_by_age_to_dbh
        index = [
            "country",
            "year",
            "genus",
            "mgmt_type",
            "mgmt_strategy",
            "con_broad",
            "dbh_class",
        ]
        df_agg = df.groupby(index)["tc_irw"].agg("sum").reset_index()
        # Merge with grading information
        index = ["country", "genus", "mgmt_type", "mgmt_strategy", "dbh_class"]
        df2 = df_agg.merge(nb_grading, on=index, how="left")
        # Compute the allocation
        df2["tc_irw"] = df2["tc_irw"] * df2["proportion"]
        # Check that values didn't change before and after the allocation
        index = [
            "country",
            "year",
            "genus",
            "mgmt_type",
            "mgmt_strategy",
            "con_broad",
            "dbh_class",
        ]
        df_agg2 = df2.groupby(index).agg(
            tc_irw=("tc_irw", "sum"), proportion=("proportion", "sum")
        )
        df_comp = df_agg.merge(
            df_agg2, on=index, how="left", suffixes=("_before", "_after")
        )
        selector = (df_comp["year"] > 2020) & (
            ~np.isclose(df_comp["tc_irw_before"], df_comp["tc_irw_after"])
        )
        if any(selector):
            msg = f"For post-2020, the following tc_irw values don't match between "
            msg += "input before and after NB grading allocation\n"
            msg = f"For post-2020, fractions for allocation on saw and pulplogs are missing for specified dbh_class"
            msg += f"{df_comp.loc[selector]}"
            warnings.warn(msg)
        return df2



    @cached_property
    def fluxes_by_grade_pulpwood_sawlogs(self) -> pandas.DataFrame:
        """Fluxes of roundwood products by grade saw logs and pulp logs
        coniferous and broadleaves.
        """
        index = ["year", "grade", "con_broad"]
        df_long = (
            self.fluxes_by_grade_dbh.groupby(index)["tc_irw"].agg("sum").reset_index()
        )
        # Glue columns grade and con_broad together
        df_long["grade2"] = df_long["grade"] + "_" + df_long["con_broad"]
        df = df_long.pivot(
            columns="grade2", index=["year"], values="tc_irw"
        ).reset_index()
        return df
    
    
    @cached_property
    def fluxes_by_grade(self) -> pandas.DataFrame:
        """Fluxes of roundwood products with spike smoothing and correction factors.
    
        Includes logic for:
        - Smoothing data spikes after the base year
        - Calculating pre- and post-base year averages
        - Applying correction factors to maintain consistency
        """
        df = self.fluxes_by_grade_pulpwood_sawlogs.copy()
    
        # Function to replace spikes starting from end of calibration
        def replace_spikes(df, column):
            for i in range(1, len(df)):
                if df.at[i, "year"] >= self.base_year - 3:  # Only start replacing from end of calibration
                    prev_value = df.at[i - 1, column]
                    current_value = df.at[i, column]
                    upper_bound = prev_value * 1.05
                    lower_bound = prev_value * 0.95
                    # Ensure current value is within ±5% of the previous year's value
                    if current_value > upper_bound:
                        df.at[i, column] = upper_bound
                    elif current_value < lower_bound:
                        df.at[i, column] = lower_bound
    
        # Apply the function to each column (except 'year')
        columns_to_check = df.columns[1:]  # Exclude 'year' column
        for column in columns_to_check:
            replace_spikes(df, column)
    
        # Calculate average values pre- and post-base_year
        n_years = 10  # Number of years before and after base_year to include in the average, to offset salvage years
    
        # Calculate averages with NaN handling
        avg_post_base_year = (
            df.loc[
                (df["year"] >= self.base_year)
                & (df["year"] < self.base_year + n_years),
                df.columns[1:],
            ]
            .mean()
            .fillna(0)
        )  # Replace NaN with 0 after calculating mean
    
        avg_pre_base_year = (
            df.loc[
                (df["year"] > self.base_year - n_years)
                & (df["year"] <= self.base_year),
                df.columns[1:],
            ]
            .mean()
            .fillna(0)
        )
    
        # Calculate correction factor with NaN/inf handling
        correction_factor = avg_pre_base_year / avg_post_base_year
        correction_factor = correction_factor.replace([np.inf, -np.inf], 0)
    
        # Apply correction factor before handling NaNs
        df.loc[df["year"] >= self.base_year, df.columns[1:]] *= correction_factor.values
    
        # Replace remaining NaNs in the entire DataFrame before saving
        df = df.fillna(0)
    
        # Create new columns with NaN handling
        df["pulpwood"] = df["pulpwood_con"].fillna(0) + df["pulpwood_broad"].fillna(0)
        df["sawlogs"] = df["sawlogs_con"].fillna(0) + df["sawlogs_broad"].fillna(0)
    
        return df

    @property  # Don't cache, in case we change the number of years
    def fraction_semifinished_n_years_mean(self) -> pandas.DataFrame:
        """Compute the fraction of semi finished products as the average of the
        n years defined as in the n_years_dom_frac property

        Also compute the average of the absolute amounts of recycled wood
        entering in wood panels and the amount of recycled paper entering in
        paper production. So that we don't overestimate the contribution of
        fresh forest fibre from domestic production.

        Merge country statistics on domestic harvest and
        CBM output for n common years.

        Check if available raw material is sufficient to produce the amount of
        semi finished products reported by countries.

        param n: Number of years to keep from domestic harvest

        Example use using 3 or 4 years:

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> runner.post_processor.hwp.n_years_dom_frac = 3
            >>> print(runner.post_processor.hwp.fraction_semifinished_n_years_mean)
            >>> runner.post_processor.hwp.n_years_dom_frac = 4
            >>> print(runner.post_processor.hwp.fraction_semifinished_n_years_mean)

        Export to csv for checking

            >>> from eu_cbm_hat import eu_cbm_data_pathlib
            >>> eu_cbm_data_pathlib / "file.csv"
            >>> df.to_csv(
            ...     continent.base_dir + "/quick_results/" + "mean_n_years.csv",
            ...     mode="a",
            ...     header=True,
            ... )


        """
        # Country statistics on domestic harvest
        dstat = self.prod_from_dom_harv_stat
        # CBM output
        df_out = self.fluxes_by_grade
        index = ["area", "year"]
        cols = [
            "sw_broad_dom_tc",
            "sw_con_dom_tc",
            "wp_dom_tc",
            "pp_dom_tc",
            "recycled_paper_prod",
            "recycled_wood_prod",
        ]

        # Keep data for the last n years and for the selected country
        selector = dstat["year"] > dstat["year"].max() - self.n_years_dom_frac
        selector &= dstat["area"] == self.runner.country.country_name
        dstat = dstat.loc[selector, index + cols]
        # Merge country statistics with CBM output
        df = df_out.merge(dstat, on="year", how="right")
        # calculate the fractions for n years available in case, simulation is
        # based on absolute amounts required in future, then df["sw_dom_tc"],
        # df["pp_dom_tc"], df["wp_dom_tc"] have to be generated from that input
        # data just before the following arithmetic's

        # HANDLING DENOIMINATOR ZERO AND INF
        # df["sw_broad_fraction"] = df["sw_broad_dom_tc"] / df["sawlogs_broad"]
        df["sw_broad_fraction"] = (
            (df["sw_broad_dom_tc"] / df["sawlogs_broad"])
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )

        # df["sw_con_fraction"] = df["sw_con_dom_tc"] / df["sawlogs_con"]
        df["sw_con_fraction"] = (
            (df["sw_con_dom_tc"] / df["sawlogs_con"])
            # NEW lines to ensure non inf due to denomintor zero sometimes
            .replace([np.inf, -np.inf], 0).fillna(0)
        )

        # df["pp_fraction"] = df["pp_dom_tc"] / df["pulpwood"]
        df["pp_fraction"] = (
            (df["pp_dom_tc"] / df["pulpwood"]).replace([np.inf, -np.inf], 0).fillna(0)
        )

        df["sw_dom_tc"] = df["sw_broad_dom_tc"] + df["sw_con_dom_tc"]

        # df["wp_fraction"] = df["wp_dom_tc"] / (
        #    (df["sawlogs"] - df["sw_dom_tc"]) + (df["pulpwood"] - df["pp_dom_tc"])
        # )
        df["wp_fraction"] = (
            (
                df["wp_dom_tc"]
                / (df["sawlogs"] - df["sw_dom_tc"] + df["pulpwood"] - df["pp_dom_tc"])
            )
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )
        sw_selector = df["sw_broad_fraction"] > 0.55
        if any(sw_selector):
            msg = "Check broad sawnwood production from sawlogs production for the following years:\n"
            msg += "\n".join(
                f"Year {int(row['year'])} in {row['area']}: "
                f"sw_broad_dom_tc = {row['sw_broad_dom_tc']:.2f}, "
                f"sawlogs_broad = {row['sawlogs_broad']:.2f}, "
                f"Fraction = {row['sw_broad_fraction']:.2f}"
                for _, row in df[sw_selector].iterrows()
            )
            msg += "\nThis temporary warning related to the sw_broad_fraction should be an error instead."
            warnings.warn(msg)

        # Roundwood can never be converted totally to sawnwood. Fraction always have to
        # be below this value.
        sw_selector = df["sw_con_fraction"] > 0.65
        if any(sw_selector):
            msg = "Check con sawnwood production from sawlogs production for the following years:\n"
            msg += "\n".join(
                f"Year {int(row['year'])} in {row['area']}: "
                f"sw_con_dom_tc = {row['sw_con_dom_tc']:.2f}, "
                f"sawlogs_con = {row['sawlogs_con']:.2f}, "
                f"Fraction = {row['sw_con_fraction']:.2f}"
                for _, row in df[sw_selector].iterrows()
            )
            msg += "\nThis temporary warning related to the sw_con_fraction should be an error instead."
            warnings.warn(msg)

        pp_selector = df["pp_fraction"] > 1
        if any(sw_selector):
            msg = "Check pp production from pulplogs production for the following years:\n"
            msg += "\n".join(
                f"Year {int(row['year'])} in {row['area']}: "
                f"pp_dom_tc = {row['pp_dom_tc']:.2f}, "
                f"pulpwood = {row['pulpwood']:.2f}, "
                for _, row in df[sw_selector].iterrows()
            )
            msg += "\nThis temporary warning related to the pulplogs should be an error instead."
            warnings.warn(msg)

        wp_selector = df["wp_fraction"] > 1
        if any(wp_selector):
            msg = "Check wood panels production from sawlogs and pulplogs production for the following years:\n"
            msg += "\n".join(
                f"Year {int(row['year'])} in {row['area']}: "
                f"wp_dom_tc = {row['wp_dom_tc']:.2f}, "
                f"Available wood = {(row['sawlogs'] - row['sw_dom_tc'] + row['pulpwood'] - row['pp_dom_tc']):.2f}, "
                f"Fraction = {row['wp_fraction']:.2f}"
                for _, row in df[wp_selector].iterrows()
            )
            msg += "\nThis temporary warning related to the wp_fraction should be an error instead."
            warnings.warn(msg)

        # Compute the average of the selected columns
        selected_cols = [
            "sw_broad_fraction",
            "sw_con_fraction",
            "pp_fraction",
            "wp_fraction",
            "recycled_paper_prod",
            "recycled_wood_prod",
        ]
        mean_frac = df[selected_cols].mean()
        return mean_frac

    @property  # Don't cache, in case we change the number of years
    def fraction_semifinished_default(self) -> pandas.DataFrame:
        """Fraction of semi finished products in the default case"""
        mean_frac = self.fraction_semifinished_n_years_mean
        max_year = self.runner.country.base_year + self.runner.num_timesteps
        df = pandas.DataFrame({"year": range(1900, max_year + 1)})
        cols = [
            "sw_broad_fraction",
            "sw_con_fraction",
            "pp_fraction",
            "wp_fraction",
            "recycled_paper_prod",
            "recycled_wood_prod",
        ]
        for col in cols:
            df[col] = mean_frac[col]
        # Default recycling values to one
        df["recycled_wood_factor"] = 1
        df["recycled_paper_factor"] = 1
        # Return
        return df

    @property  # Don't cache, in case we change the number of years
    def fraction_semifinished_scenario(self) -> pandas.DataFrame:
        """Fraction of semi finished products in a scenario case

        Here we need to allow simulation choosing between input types either on
        fraction based inputs or on amount based inputs as defined in the input
        file hwp_fraction_semifinished_scenario.csv. If amounts are defined,
        then they will be used, otherwise fractions will be used.


            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> # Choose a scenario
            >>> runner.post_processor.hwp.hwp_frac_scenario = "more_sw"
            >>> runner.post_processor.hwp.fraction_semifinished_scenario

        """
        mean_frac = self.fraction_semifinished_n_years_mean
        df = hwp_common_input.hwp_fraction_semifinished_scenario.copy()
        # Select data for the relevant country and scenario
        selector = df["country"] == self.runner.country.country_name
        selector &= df["hwp_frac_scenario"] == self.hwp_frac_scenario
        df = df.loc[selector]

        # Keep only fraction columns or amount columns depending on which one
        # is defined in the scenario input file.
        fraction_cols = [x + "_fraction" for x in self.semifinished_products]
        amount_cols = [x + "_expected" for x in self.semifinished_products]
        fraction_defined = (~df[fraction_cols].isna()).any().any()
        amount_defined = (~df[amount_cols].isna()).any().any()
        if amount_defined and fraction_defined:
            msg = f"Both fractions and amounts are defined in\n{df}\n"
            msg += "Define either fractions or amounts."
            raise ValueError(msg)

        if fraction_defined:
            df.drop(columns=amount_cols)
        elif amount_defined:
            df.drop(columns=fraction_cols)
        # Add recycled values from the mean table
        df["recycled_paper_prod"] = mean_frac["recycled_paper_prod"]
        df["recycled_wood_prod"] = mean_frac["recycled_wood_prod"]
        df.drop(columns=["country", "hwp_frac_scenario"], inplace=True)
        return df

    @property  # Don't cache, in case we change the number of years
    def fraction_semifinished(self) -> pandas.DataFrame:
        """Fraction of semi finished products

        Either default values or values from a scenario input files:

        - The default values are from the fraction_semifinished_n_years_mean
          method
        - The input files values are from
          hwp_common_input.hwp_fraction_semifinished_scenario
        """
        if self.hwp_frac_scenario == "default":
            # Default scenario
            return self.fraction_semifinished_default
        # Other scenarios
        return self.fraction_semifinished_scenario

    @cached_property
    def prod_trade_fsm(self):
        """Production and trade data from a Forest Sector Model"""
        scenario_dir = (
            eu_cbm_data_pathlib / "domestic_harvest" / self.semifinished_prod_scenario
        )
        df = pandas.read_csv(scenario_dir / "hwp_expected_fsm.csv")
        selector = df["country"] == self.runner.country.country_name
        df = df.loc[selector].copy()
        return df

    @cached_property
    def dom_harvest_factor_fsm(self):
        """Factor to compute the production from domestic harvest

        Correct for export and import of saw logs and pulp logs
        If saw logs net trade is negative, export < import
        The net trade of industrial roundwood should be removed
        proportionally from the production of each semi finished product.
        If saw logs net trade is positive, import < export
        Then do nothing.

        Example:

            from eu_cbm_hat.core.continent import continent
            runner = continent.combos['reference'].runners['EE'][-1]
            df = runner.post_processor.hwp.dom_harvest_factor_fsm

        """
        df = self.prod_trade_fsm
        df = df.loc[df["product"] == "indround"].copy()
        df["net_trade"] = df["exp"] - df["imp"]
        df["f_trade"] = (df["prod"] - df["exp"]) / (df["prod"] + df["imp"] - df["exp"])
        # Set negative values to zero
        df.loc[df["f_trade"] < 0, "f_trade"] = 0
        return df

    @cached_property
    def prod_semifinished_from_dom_harv_fsm(self):
        """Production of semi finished products from an economic model

        Usage example:

            from eu_cbm_hat.core.continent import continent
            runner = continent.combos['reference'].runners['EE'][-1]
            df = runner.post_processor.hwp.prod_semifinished_from_dom_harv_fsm
            # df["product"].unique()
            # array(['indround', 'fuel', 'sawn', 'panel', 'pulp', 'paper']

        """
        df = self.prod_trade_fsm
        # Compute production from domestic harvest
        index = ["scenario", "year"]
        irw = self.dom_harvest_factor_fsm[index + ["f_trade"]]
        df = df.merge(irw, on=index, how="left")
        df["prod"] = df["prod"] * df["f_trade"]
        # Convert products to tons of carbon
        product_map = pandas.DataFrame(
            {
                "product": [
                    "sawn",
                    "panel",
                    "paper",
                ],
                "product_short": [
                    "sw",
                    "wp",
                    "pp",
                ],
                "conv_factor": [
                    hwp_common_input.c_sw,
                    hwp_common_input.c_wp,
                    hwp_common_input.c_pp,
                ],
            }
        )
        df = df.loc[df["product"].isin(product_map["product"])]
        df = df.merge(product_map, on="product", how="left")
        # Convert 1000m3 of sw and panel to tons of carbon
        # Convert 1000t of paper to tons of carbon
        df["prod_tc"] = df["prod"] * df["conv_factor"] * 1000
        # Reshape prod_tc to wide format with product_short in columns sw_
        df["variable_name"] = df["product_short"] + "_expected_tc"
        # Note we convert to carbon before splitting con and broad. It could
        # also be done afterwards with con and broad specific factors
        index = ["country", "year"]
        df_wide = df.pivot(
            index=index, columns="variable_name", values="prod_tc"
        ).reset_index()
        # Split con and broad based on a proportion from the last n years
        frac = self.fraction_semifinished_n_years_mean
        # Compute fraction for sw only
        sw_broad_fraction = frac["sw_broad_fraction"] / (
            frac["sw_con_fraction"] + frac["sw_broad_fraction"]
        )
        df_wide["sw_broad_expected_tc"] = df_wide["sw_expected_tc"] * sw_broad_fraction
        df_wide["sw_con_expected_tc"] = df_wide["sw_expected_tc"] * (
            1 - sw_broad_fraction
        )
        return df_wide

    # Don"t cache, in case we change the number of years or the self.add_recycling
    # property
    @property
    def prod_from_dom_harv_sim(self) -> pandas.DataFrame:
        """Compute the production of sanwood, panels and paper from domestic
        harvest as an output of the CBM simulated amounts of sawlogs and
        pulpwood.

        If amount columns are defined in the fraction semi finished scenario,
        use them as dom_tc production of semi finished products. Otherwise
        compute the amounts based on the fraction of semi finished products in
        the historical period.

        Enable scenarios of production from domestic harvest from an
        external model. See issue 104.
        https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat/-/issues/104#top

        Production from domestic harvest is based on an external model or on
        fraction scenarios:

            - If the file is defined in a scenario c ombination, then the
              external Forest Sector Model data will  be used. 
            - otherwise a fraction of semi finished can be used:
                - default fraciton 
                - there can also be a scenario of fractions 

        Example calling a runner with available exogenous data from a forest
        Sector Model:

            from eu_cbm_hat.core.continent import continent
            runner = continent.combos['reference'].runners['EE'][-1]
            hwp = runner.post_processor.hwp
            print("semifinished_prod_scenario:", hwp.semifinished_prod_scenario)
            print(hwp.prod_from_dom_harv_sim)
            print(hwp.stock_sink_results)

        Change the scenario and display the economic model data, as well as the
        output of simulated production from domestic harvest:

            hwp.semifinished_prod_scenario = "pikssp2_fel1"
            print("semifinished_prod_scenario:", hwp.semifinished_prod_scenario)
            print(hwp.prod_trade_fsm)
            print(hwp.prod_from_dom_harv_sim)

        Illustrate a change of the semi finished scenario from amounts to fractions.
        Modify fractions semi finished scenarios

            from eu_cbm_hat.core.continent import continent
            runner = continent.combos['reference'].runners['LU'][-1]
            hwp = runner.post_processor.hwp
            print(hwp.prod_from_dom_harv_sim)

            print("Fractions before modification, in the default scenario")
            print(hwp.fraction_semifinished_n_years_mean)
            print(hwp.fraction_semifinished)
            print(hwp.prod_from_dom_harv_sim)
            print(hwp.stock_sink_results)

            # Change the fraction semi finished
            runner.post_processor.hwp.hwp_frac_scenario = "more_sw"
            print("Fractions in the scenario")
            print(hwp.fraction_semifinished)
            # Display the effect on the production from domestic harvest
            print(hwp.prod_from_dom_harv_sim)
            # Display the effect on the final results
            print(hwp.stock_sink_results)

            # Add recycling (default)
            df_with_recycling = hwp.prod_from_dom_harv_sim
            # Don't add recycling
            hwp.add_recycling = False
            df_without_recycling = hwp.prod_from_dom_harv_sim

        """
        df = self.fluxes_by_grade.copy()
        # Add fractions and recycling to the CBM output data
        df = df.merge(self.fraction_semifinished, on="year")

        if self.semifinished_prod_scenario == "fraction":
            # Compute production from domestic harvest for the future
            df["sw_broad_dom_tc"] = df["sawlogs_broad"] * df["sw_broad_fraction"]
            df["sw_con_dom_tc"] = df["sawlogs_con"] * df["sw_con_fraction"]
            df["wp_dom_tc"] = df["sawlogs"] * df["wp_fraction"]
            df["pp_dom_tc"] = df["pulpwood"] * df["pp_fraction"]
        else:
            df = df.merge(self.prod_semifinished_from_dom_harv_fsm, on="year")
            # Compute the minimum between saw logs tc and sawnwood tc
            df["sw_con_dom_tc"] = np.minimum(
                df["sawlogs_con"], df["sw_con_expected_tc"]
            )
            df["sw_broad_dom_tc"] = np.minimum(
                df["sawlogs_broad"], df["sw_broad_expected_tc"]
            )
            # Compute the minimum between pulp lots  tc and paper tc
            df["pp_dom_tc"] = np.minimum(df["pulpwood"], df["pp_expected_tc"])
            # Compute the remaining amount for wood panels
            # exclude the parenthesis when the difference is negative
            df["wp_dom_tc"] = np.minimum(
                df["wp_expected_tc"],
                (df["sawlogs_con"] - df["sw_con_expected_tc"])
                + (df["sawlogs_broad"] - df["sw_broad_expected_tc"])
                + (df["pulpwood"] - df["pp_expected_tc"]),
            )
            # Change negative wood panel production to zero
            # Because of lack of availability
            df.loc[df["wp_dom_tc"] < 0, "wp_dom_tc"] = 0

        # Compute recycled amount if required
        if self.add_recycling:
            msg = "Add recycling amounts because "
            msg += f"add_recycling = {self.add_recycling}"
            print(msg)
            df["wp_dom_tc"] += (
                df["recycled_wood_prod"]
                * hwp_common_input.c_wp
                * df["recycled_wood_factor"]
            )
            df["pp_dom_tc"] += (
                df["recycled_paper_prod"]
                * hwp_common_input.c_pp
                * df["recycled_paper_factor"]
            )
        else:
            msg = "No recycling amounts because "
            msg += f"add_recycling = {self.add_recycling}"
            print(msg)
        return df

    @property  # Don't cache, in case we change the number of years
    def concat_1900_to_last_sim_year(self) -> pandas.DataFrame:
        """This applies with IPCC method. Concatenate backcasted data from
        1900, reported historical country data and CBM output until the end of
        the simulation.

        In the CBM simulated output, keep only years that are not already in
        country statistics.

        Plot production from domestic harvest for both historically reported
        data and simulation output:

            >>> import matplotlib.pyplot as plt
            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> df = runner.post_processor.hwp.concat_1900_to_last_sim_year
            >>> df.set_index("year").plot()
            >>> plt.show()

        """
        # Input data frames
        dstat = self.prod_from_dom_harv_stat.copy()
        df_out = self.prod_from_dom_harv_sim.copy()
        cols = ["sw_broad_dom_tc", "sw_con_dom_tc", "wp_dom_tc", "pp_dom_tc"]
        # Keep data for the selected country
        selector = dstat["area"] == self.runner.country.country_name
        dstat = dstat.loc[selector, ["year"] + cols]
        df_out = df_out[["year"] + cols].copy()
        # Keep only years not in country statistics
        selector = df_out["year"] > dstat["year"].max()
        df_out = df_out.loc[selector]
        # Concatenate
        df = pandas.concat([dstat, df_out])
        return df.reset_index(drop=True)

    def prepare_decay_and_inflow(self):
        """Prepare decay parameters and compute inflow with country-specific constants

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> hwp = runner.post_processor.hwp
        >>> hwp.prepare_decay_and_inflow__()

        """
        df = self.concat_1900_to_last_sim_year.copy()

        # Get the current country code
        country_code = self.runner.country.iso2_code

        # Define a dictionary of constants for each country
        constants = {
                    'AT':0.5,
                    'BE':0.5,
                    'BG':2,#OK
                    #'CZ':1,
                    #'DE':1,
                    'DK':2,#OK
                    #'EE':1,
                    #'ES':1,
                    #'FI':1,
                    #'FR':1,
                    #'GR':1,
                    #'HR':1,
                    #'HU':1,
                    'IE':2,#OK
                    'IT':0.5,
                    #'LT':1,
                    'LU':0.5,
                    #'LV':1,
                    'NL':2,
                    'PL':0.5,# OK
                    'PT':1.5,
                    #'RO':1,
                    'SE':2,# OK
                    #'SI':1,
                    #'SK':1
                            }

        # Retrieve the multiplier for the current country, default to 1.0 if not found
        constant = constants.get(country_code, 1.0)

        # Define the columns to multiply
        columns_to_multiply = [
            "sw_broad_dom_tc",
            "sw_con_dom_tc",
            "wp_dom_tc",
            "pp_dom_tc",
        ]

        # Apply the country-specific constant to the selected columns
        df[columns_to_multiply] = df[columns_to_multiply] * constant

        # Assign decay parameters
        decay_params = hwp_common_input.decay_params
        for col in decay_params.columns:
            df[col] = decay_params[col].values[0]

        # Compute the corrected inflow based on decay parameters
        df = df.assign(
            sw_broad_inflow=(df.sw_broad_dom_tc * df.k1_sw),
            sw_con_inflow=(df.sw_con_dom_tc * df.k1_sw),
            wp_inflow=(df.wp_dom_tc * df.k1_wp),
            pp_inflow=(df.pp_dom_tc * df.k1_pp),
        )

        return df

    @property  # Don't cache, in case we change the number of years
    def build_hwp_stock_since_1900(self):
        # def build_hwp_stock(self):
        """IPCC method: Build HWP stock values for 1900 to end of simulated period

        Plot stock evolution

            >>> import matplotlib.pyplot as plt
            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> df = runner.post_processor.hwp.build_hwp_stock_since_1900
            >>> cols = ['sw_stock', 'wp_stock', 'pp_stock']
            >>> df.set_index("year")[cols].plot()
            >>> plt.show()

        """
        df = self.prepare_decay_and_inflow().copy()
        cols = ["sw_broad_inflow", "sw_con_inflow", "wp_inflow", "pp_inflow"]
        cols += ["e_sw", "e_wp", "e_pp", "k_sw", "k_wp", "k_pp"]
        df = df[["year"] + cols]
        # Initiate stock values
        df["sw_broad_stock"] = 0.0  # Keep the dot to create a floating point number
        df["sw_con_stock"] = 0.0
        df["wp_stock"] = 0.0
        df["pp_stock"] = 0.0

        # Compute the stock for each semi finite product for all subsequent years
        df = df.set_index("year")
        for t in range(df.index.min() + 1, df.index.max()):
            df.loc[t, "sw_broad_stock"] = (
                df.loc[t - 1, "sw_broad_stock"] * df.loc[t, "e_sw"]
                + df.loc[t, "sw_broad_inflow"]
            )
            df.loc[t, "sw_con_stock"] = (
                df.loc[t - 1, "sw_con_stock"] * df.loc[t, "e_sw"]
                + df.loc[t, "sw_con_inflow"]
            )
            df.loc[t, "wp_stock"] = (
                df.loc[t - 1, "wp_stock"] * df.loc[t, "e_wp"] + df.loc[t, "wp_inflow"]
            )
            df.loc[t, "pp_stock"] = (
                df.loc[t - 1, "pp_stock"] * df.loc[t, "e_pp"] + df.loc[t, "pp_inflow"]
            )
        df.reset_index(inplace=True)
        df.fillna(0, inplace=True)

        # Add annual loses by decay of historical stock, as the limit for recycling
        df["sw_con_loss"] = df["sw_con_stock"] * df["k_sw"]
        df["sw_broad_loss"] = df["sw_broad_stock"] * df["k_sw"]
        df["wp_loss"] = df["wp_stock"] * df["k_wp"]
        df["pp_loss"] = df["pp_stock"] * df["k_pp"]
        df["hwp_loss"] = (
            df["sw_con_loss"] + df["sw_broad_loss"] + df["wp_loss"] + df["pp_loss"]
        )

        # Compute the total stock
        df["hwp_tot_stock_tc"] = (
            df["sw_broad_stock"]
            + df["sw_broad_stock"]
            + df["wp_stock"]
            + df["pp_stock"]
        )

        # Do the difference between consecutive years
        df["hwp_tot_diff_tc"] = df["hwp_tot_stock_tc"].diff(periods=1)
        # Stock diff shifted by one year
        # df['hwp_tot_diff_tc_m1'] = df['hwp_tot_stock_tc'].diff(periods=1).shift(-1)
        df["hwp_tot_sink_tco2"] = df["hwp_tot_diff_tc"] * (-44 / 12)
        return df

    @property  # Don't cache, in case we change the number of years
    def build_hwp_stock_since_1990(self):
        """complementary KP method: build HWP stock values for 1990 to the end
        of simulated period

        Plot stock evolution

            >>> import matplotlib.pyplot as plt
            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> df = runner.post_processor.hwp.build_hwp_stock_1990
            >>> cols = ['sw_stock', 'wp_stock', 'pp_stock']
            >>> df.set_index("year")[cols].plot()
            >>> plt.show()

        """

        df = self.prepare_decay_and_inflow().copy()
        cols = ["sw_broad_inflow", "sw_con_inflow", "wp_inflow", "pp_inflow"]
        cols += ["k_sw", "k_wp", "k_pp"]
        cols += ["e_sw", "e_wp", "e_pp"]
        df = df[["year"] + cols]
        # Retain only the first five years including 1990
        df_mean = df[df["year"] >= 1990].head(5)
        # Initiate stock values as average of 1990-1995 as the average of the
        # First five years for each inflow type
        df["sw_con_stock"] = (df_mean["sw_con_inflow"].mean()) / (
            df_mean["k_sw"].mean()
        )
        df["sw_broad_stock"] = (df_mean["sw_broad_inflow"].mean()) / (
            df_mean["k_sw"].mean()
        )
        df["wp_stock"] = (df_mean["wp_inflow"].mean()) / (df_mean["k_wp"].mean())
        df["pp_stock"] = (df_mean["pp_inflow"].mean()) / (df_mean["k_pp"].mean())

        # Compute the stock for each semi finite product for all subsequent years
        df = df.set_index("year")
        for t in range(df.index.min() + 1, df.index.max()):
            df.loc[t, "sw_broad_stock"] = (
                df.loc[t - 1, "sw_broad_stock"] * df.loc[t, "e_sw"]
                + df.loc[t, "sw_broad_inflow"]
            )
            df.loc[t, "sw_con_stock"] = (
                df.loc[t - 1, "sw_con_stock"] * df.loc[t, "e_sw"]
                + df.loc[t, "sw_con_inflow"]
            )
            df.loc[t, "wp_stock"] = (
                df.loc[t - 1, "wp_stock"] * df.loc[t, "e_wp"] + df.loc[t, "wp_inflow"]
            )
            df.loc[t, "pp_stock"] = (
                df.loc[t - 1, "pp_stock"] * df.loc[t, "e_pp"] + df.loc[t, "pp_inflow"]
            )
        df.reset_index(inplace=True)

        # Add annual loses by decay of historical stock, as the limit for recycling
        df["sw_con_loss"] = df["sw_con_stock"] * df["k_sw"]
        df["sw_broad_loss"] = df["sw_broad_stock"] * df["k_sw"]
        df["wp_loss"] = df["wp_stock"] * df["k_wp"]
        df["pp_loss"] = df["pp_stock"] * df["k_pp"]
        df["hwp_loss"] = (
            df["sw_broad_loss"] + df["sw_con_loss"] + df["wp_loss"] + df["pp_loss"]
        )
        # Compute the total stock
        df["hwp_tot_stock_tc"] = (
            df["sw_broad_stock"] + df["sw_con_stock"] + df["wp_stock"] + df["pp_stock"]
        )
        # Do the difference between consecutive years
        df["hwp_tot_diff_tc"] = df["hwp_tot_stock_tc"].diff(periods=1)
        # Stock diff shifted by one year
        # df['hwp_tot_diff_tc_m1'] = df['hwp_tot_stock_tc'].diff(periods=1).shift(-1)
        df["hwp_tot_sink_tco2"] = df["hwp_tot_diff_tc"] * (-44 / 12)
        # Keep only after 1990
        df = df[df["year"] >= 1990]
        return df

    @cached_property
    def fluxes_to_primary_fw(self) -> pandas.DataFrame:
        """Fluxes to primary Fuel Wood."""
        df = self.fluxes_to_products
        # Add bark fraction
        df = df.merge(self.parent.wood_density_bark_frac, on="forest_type", how="left")

        # Switch off black autoformatting to avoid the long lines below to be wrapped.
        # fmt: off
        # Primary Fuel Wood removed directly as fulewood trees
        df['tc_soft_fw_merch'] = df['softwood_merch_to_product'] * (1-df['softwood_merch_irw_frac'])
        df['tc_soft_fw_other'] = df['softwood_other_to_product'] * (1-df['softwood_other_irw_frac'])
        df['tc_soft_fw_stem_snag'] = df['softwood_stem_snag_to_product'] * (1-df['softwood_stem_snag_irw_frac'])
        df['tc_soft_fw_branch_snag'] = df['softwood_branch_snag_to_product'] * (1-df['softwood_branch_snag_irw_frac'])
        df['tc_hard_fw_merch'] = df['hardwood_merch_to_product'] * (1-df['hardwood_merch_irw_frac'])
        df['tc_hard_fw_other'] = df['hardwood_other_to_product'] * (1-df['hardwood_other_irw_frac'])
        df['tc_hard_fw_stem_snag'] = df['hardwood_stem_snag_to_product'] * (1-df['hardwood_stem_snag_irw_frac'])
        df['tc_hard_fw_branch_snag'] = df['hardwood_branch_snag_to_product'] * (1-df['hardwood_branch_snag_irw_frac'])
        # fmt: on

        # Aggregate
        index = ["year"]
        tc_cols = df.columns[df.columns.str.contains("tc_")]
        # Aggregate over the index
        df_agg = df.groupby(index)[tc_cols].agg("sum")
        # Sum fluxes columns together into one tc_irw column
        df_agg = df_agg[tc_cols].sum(axis=1).reset_index()
        df_agg.rename(columns={0: "tc_primary_fw"}, inplace=True)
        return df_agg

    @cached_property
    def fluxes_to_secondary_fw(self) -> pandas.DataFrame:
        """Deduce actual products from overall industrial roundwood

        Part of the eligible HWP amount is converted to actual products. We
        consider that the remaining part is burned as secondary fuel wood.

        Part of the IRW Bark is also used as fuel wood.
        Compute the bark obtain from Industrial Roundwood and add it to the total.

        """
        df = self.fluxes_to_products
        # Add bark fraction
        df = df.merge(self.parent.wood_density_bark_frac, on="forest_type", how="left")

        # fmt: off
        # Compute the bark obtain from Industrial Roundwood
        #IRW's bark to be included in "FW_secondary" pools
        df['tc_soft_fw_irw_merch'] = df['softwood_merch_to_product'] * df ['softwood_merch_irw_frac']*df['bark_frac']
        df['tc_soft_fw_irw_other'] = df['softwood_other_to_product'] * df['softwood_other_irw_frac']*df['bark_frac']
        df['tc_soft_fw_irw_stem_snag'] = df['softwood_stem_snag_to_product'] * df['softwood_stem_snag_irw_frac']*df['bark_frac']
        df['tc_soft_fw_irw_branch_snag'] = df['softwood_branch_snag_to_product'] * df['softwood_branch_snag_irw_frac']*df['bark_frac']
        df['tc_hard_fw_irw_merch'] = df['hardwood_merch_to_product'] * df['hardwood_merch_irw_frac']*df['bark_frac']
        df['tc_hard_fw_irw_other'] = df['hardwood_other_to_product'] * df['hardwood_other_irw_frac']*df['bark_frac']
        df['tc_hard_fw_irw_stem_snag'] = df['hardwood_stem_snag_to_product'] * df['hardwood_stem_snag_irw_frac']*df['bark_frac']
        df['tc_hard_fw_irw_branch_snag'] = df['hardwood_branch_snag_to_product'] * df['hardwood_branch_snag_irw_frac']*df['bark_frac']
        # fmt: on

        cols = [
            "tc_soft_fw_irw_merch",
            "tc_soft_fw_irw_other",
            "tc_soft_fw_irw_stem_snag",
            "tc_soft_fw_irw_branch_snag",
            "tc_hard_fw_irw_merch",
            "tc_hard_fw_irw_other",
            "tc_hard_fw_irw_stem_snag",
            "tc_hard_fw_irw_branch_snag",
        ]

        df = df.groupby(["year"])[cols].sum().reset_index()
        df["fw_irw_bark"] = df[cols].sum(axis=1)
        df1 = self.fluxes_by_grade
        df1["hwp_eligible"] = df1[["pulpwood", "sawlogs"]].sum(axis=1)
        df2 = self.prod_from_dom_harv_sim
        df2["sw_dom_tc"] = df2[["sw_broad_dom_tc", "sw_con_dom_tc"]].sum(axis=1)
        df2["hwp_allocated"] = df2[["sw_dom_tc", "wp_dom_tc", "pp_dom_tc"]].sum(axis=1)
        df = df1[["year", "hwp_eligible"]].merge(
            df2[["year", "hwp_allocated"]].merge(df[["year", "fw_irw_bark"]]), on="year"
        )
        df["tc_secondary_fw"] = (
            df["hwp_eligible"] - df["hwp_allocated"] + df["fw_irw_bark"]
        )

        return df

    @cached_property
    def ghg_emissions_fw(self) -> pandas.DataFrame:
        """Green House Gas Emissions from both primary and secondary fuel wood"""
        df1 = self.fluxes_to_primary_fw
        df2 = self.fluxes_to_secondary_fw
        df = df1.merge(df2, on="year", how="left")
        df["tc_fw"] = df[["tc_primary_fw", "tc_secondary_fw"]].sum(axis=1)

        # convert to joules as EFs are on TJ
        # Net Cal Value by mass: logwood (stacked – air dry: 20% MC) = 14.7 GJ/tonne = 0.0147 Tj/tonne of dry mass (Forestry Commission, 2022).
        ncv = 0.0147  # TJ/tone dry mass
        # EMISSION FACTORS for Biomass category: Wood / Wood Waste.
        # Note that CO2 emissions are already included in living biomass loss (for primary) and in HWP loss (for secondary)
        ef_ch4 = 0.003  # tCH4/TJ
        ef_n2o = 0.0004  # tN2O/TJ
        # GWPs
        gwp_ch4 = 21
        gwp_n2o = 300
        # intermediary calcualtions
        df["ncv_x_ef_ch4_x_gwp"] = ncv * ef_ch4 * gwp_ch4
        df["ncv_x_ef_n2o_x_gwp"] = ef_n2o * gwp_n2o
        # convert to dry mass
        # df["fw_dm"] = df["tc_fw"] / 0.5
        df["fw_primary_dm"] = df["tc_primary_fw"] / 0.5
        df["fw_secondary_dm"] = df["tc_secondary_fw"] / 0.5

        # Estimate the CO2 equivalent emissions for non CO2 gases
        df["fw_primary_ghg_co2_eq"] = (
            df["fw_primary_dm"] * df["ncv_x_ef_ch4_x_gwp"]
            + df["fw_primary_dm"] * df["ncv_x_ef_n2o_x_gwp"]
        )

        df["fw_secondary_ghg_co2_eq"] = (
            df["fw_secondary_dm"] * df["ncv_x_ef_ch4_x_gwp"]
            + df["fw_secondary_dm"] * df["ncv_x_ef_n2o_x_gwp"]
        )
        df["fw_primary_co2"] = df["tc_primary_fw"] * 44 / 12
        df["fw_secondary_co2"] = df["tc_secondary_fw"] * 44 / 12
        # Estimate the Green House Gas Emissions as CO2 Equivalent
        df["fw_ghg_co2_eq"] = (
            df["fw_primary_ghg_co2_eq"] + df["fw_secondary_ghg_co2_eq"]
        )
        df["fw_co2"] = df["fw_primary_co2"] + df["fw_secondary_co2"]

        return df

    @cached_property
    def ghg_emissions_waste(self) -> pandas.DataFrame:
        """Non CO2 emissions from waste dumps Waste amounts
        We don't calculate CO2 emissions because CO2 emissions are already
        accounted under HWP. This is about non-CO2 emissions. Calculation for
        CH4 emissions.

        Implements the method in IPCC 2006-2019. See steps in the Technical report:
            - Extend the time series in the past to prepare to compute
              accumulation
            - Compute cumulated Decomposable Degradable Organic Carbon
            - Get CH4 emissions by appling DOCF and MCF, F
            - Apply GWP Global Warming Potential
        """
        df = hwp_common_input.waste
        # Select data for this country
        selector = df["country_iso2"] == self.runner.country.iso2_code
        df = df.loc[selector]

        # Start from an early year to compute the stock accumulation.
        # Annualize biannual data
        years = np.arange(1960, 2071)
        new_df = pandas.DataFrame({"year": years})

        # Merge the two DataFrames and interpolate
        df = pandas.merge(new_df, df, on="year", how="left")
        df["wood_landfill_tfm"] = df["wood_landfill_tfm"].interpolate()
        df = df.bfill().ffill()
        # Assign decay parameter inside df
        decay_params = hwp_common_input.decay_params
        df["e_ww"] = decay_params["e_sw"].values[0]
        # Initialize cumulated wood waste  data from the annual input
        df["ddoc_mat_doc_stock_tdm"] = 0.0  # Initialize as float instead of Int
        # Initialize annual loss from wood waste stock
        df["ddocm_decompt_tdm"] = 0.0  # Initialize as float instead of Int
        # Add factor for excluding the amount subject to aerobic decomposition
        df["docf_factor"] = 0.5
        # Add factor for mass convertible to CH4
        df["mcf_factor"] = 0.5  #
        df = df.set_index("year")
        # Fill the columns for DDOCM historically cumulated doc, and annual
        # loss ddoc convertible to CH4
        for y in range(df.index.min() + 1, df.index.max() + 1):
            df.loc[y, "ddoc_mat_doc_stock_tdm"] = (
                df.loc[y - 1, "ddoc_mat_doc_stock_tdm"] * df.loc[y, "e_ww"]
                + df.loc[y, "w_annual_wood_landfill_tdm"]
                * df.loc[y, "docf_factor"]
                * df.loc[y, "mcf_factor"]
            )
            df.loc[y, "ddocm_decompt_tdm"] = df.loc[y - 1, "ddoc_mat_doc_stock_tdm"] * (
                1 - df.loc[y, "e_ww"]
            )
        df = df.reset_index()

        # Remove years before a certain period
        df = df[df["year"] > 2020].copy()

        # Get CH4 emissions by appling DOCF and MCF, F
        f_factor = 0.5
        df["ch4_generated_tch4"] = df["ddocm_decompt_tdm"] * f_factor * 16 / 12
        # Apply GWP Global Warming Potential
        df["waste_co2_eq"] = df["ch4_generated_tch4"] * 21
        return df

    @cached_property
    def ctf_unfccc(self) -> pandas.DataFrame:
        """Common Table Format for HWP calibration
        Exogenous reporting data from the CTF country reports to the UNFCCC.
        """
        df = hwp_common_input.ctf_unfccc()
        # Select the country
        selector = df["member_state"] == self.runner.country.iso2_code
        df = df.loc[selector].copy()
        return df

    @property
    def stock_sink_results(self) -> pandas.DataFrame:
        """Comparison table for HWP calibration

        Collect data from different initial year, which correspond to different
        methodologies:

            - Base year 1900 (IPCC 2006/2018/2019)
            - Base year 1990 (IPCC 2013)
            - non-CO2 emissions and total GHG emissions from burning wood for
              energy
            - Load GHG emissions from waste

        Example use:

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> hwp = runner.post_processor.hwp
            >>> print(hwp.stock_sink_results)

        """
        # Load GHG emissions reported by country to UNFCCC for HWP pool
        cols = ["member_state", "year", "crf_hwp_tco2"]
        df_ctf = self.ctf_unfccc[cols].copy()
        df_ctf["year"] = df_ctf["year"].astype(int)

        # Load stock and sink
        cols_stock = ["hwp_tot_stock_tc", "hwp_tot_sink_tco2", "hwp_loss"]
        # Initial year 1900 (IPCC 2006/2018/2019)
        df_1900 = self.build_hwp_stock_since_1900[["year"] + cols_stock].copy()
        # Add '_1900' to the columns
        df_1900 = df_1900.rename(columns={col: f"{col}_1900" for col in cols_stock})
        selector = df_1900["year"] >= 1990
        df_1900 = df_1900.loc[selector]

        # Initial year 1990 (IPCC 2013)
        df_1990 = self.build_hwp_stock_since_1990[["year"] + cols_stock]
        # Add '_1990' to the columns
        df_1990 = df_1990.rename(columns={col: f"{col}_1990" for col in cols_stock})

        # Load GHG emissions from burning wood for energy
        cols = [
            "year",
            "fw_primary_ghg_co2_eq",
            "fw_secondary_ghg_co2_eq",
            "fw_primary_co2",
            "fw_secondary_co2",
        ]

        df_fw = self.ghg_emissions_fw[cols]

        # Load GHG emissions from waste
        cols = ["year", "waste_co2_eq"]
        df_waste = self.ghg_emissions_waste[cols]

        # Merge
        df = df_ctf.merge(df_1900, on="year", how="outer")
        df = df.merge(df_1990, on="year", how="outer")
        df = df.merge(df_fw, on="year", how="outer")
        df = df.merge(df_waste, on="year", how="outer")
        # Add a scenario column
        df["hwp_frac_scenario"] = self.hwp_frac_scenario
        # Place the last column first
        cols = df.columns.to_list()
        cols = cols[-1:] + cols[:-1]

        # Fill in the last simulated year with average of the previous two years
        # Define the columns to fill
        cols_to_fill = [
            "hwp_tot_stock_tc_1900",
            "hwp_tot_sink_tco2_1900",
            "hwp_tot_stock_tc_1990",
            "hwp_tot_sink_tco2_1990",
        ]

        # Get the max year
        max_year = df["year"].max()

        # Get the two years before the max year
        prev_years = df[df["year"] < max_year].nlargest(2, "year")["year"].unique()

        # Loop through each column to fill
        for col in cols_to_fill:
            # Calculate the average of the previous two years
            avg_value = df.loc[df["year"].isin(prev_years), col].mean()

            # Fill the missing value with the average
            df.loc[df["year"] == max_year, col] = avg_value

        # Define the columns to keep
        cols_to_keep = [
            "hwp_frac_scenario",
            "member_state",
            "year",
            "crf_hwp_tco2",
            "hwp_tot_stock_tc_1900",
            "hwp_tot_sink_tco2_1900",
            "hwp_tot_stock_tc_1990",
            "hwp_tot_sink_tco2_1990",
            "hwp_loss_1900",
            "hwp_loss_1990",
            "fw_primary_ghg_co2_eq",
            "fw_secondary_ghg_co2_eq",
            "fw_primary_co2",
            "fw_secondary_co2",
            "waste_co2_eq",
        ]
        # Return the updated DataFrame with all required columns
        df = df[cols_to_keep]

        df["member_state"] = df["member_state"].ffill()

        return df[cols]
