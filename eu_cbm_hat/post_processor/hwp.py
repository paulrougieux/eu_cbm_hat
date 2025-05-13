from functools import cached_property
import numpy as np
import re
import warnings
import pandas
from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input


class HWP:
    """Compute the Harvested Wood Products Sink

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

    Compute results for the default scenario and for another hwp scenario

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> hwp = runner.post_processor.hwp
        >>> print("Fractions before modification, in the default scenario")
        >>> print(hwp.fraction_semifinished_n_years_mean)
        >>> print(hwp.fraction_semifinished)
        >>> print(hwp.prod_from_dom_harv_sim)
        >>> print(hwp.stock_sink_results)

        >>> # Change the fraction semi finished
        >>> runner.post_processor.hwp.hwp_frac_scenario = "more_sw"
        >>> print("Fractions in the scenario")
        >>> print(hwp.fraction_semifinished)
        >>> # Display the effect on the production from domestic harvest
        >>> print(hwp.prod_from_dom_harv_sim)
        >>> # Display the effect on the final results
        >>> print(hwp.stock_sink_results)

    TODO:

        - Illustrate change of number of years used to compute domestic factors
          self.n_years_dom_frac = 10

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        self.classifiers_list = self.parent.classifiers_list
        # Use pool fluxes to get area and age class as well
        self.pools_fluxes = self.runner.output.pool_flux
        # Number of common years to be used to compute the
        # Fraction domestic semi finished products
        self.n_years_dom_frac = 10
        self.hwp_frac_scenario = "default"

    def __repr__(self):
        return '%s object code "%s"' % (self.__class__, self.runner.short_name)

    @cached_property
    def irw_frac(self) -> pandas.DataFrame:
        """Industrial Roundwood Fraction

        import irw and fw fractions, keep all types of "status", inlcuding NF

        """
        df = self.parent.irw_frac
        # convert dist_ids string to values, as needed later
        df["disturbance_type"] = df["disturbance_type"].astype(int)

        # keep only relevant columns
        df = df[
            [
                "status",
                "region",
                "forest_type",
                "mgmt_type",
                "mgmt_strategy",
                "con_broad",
                "disturbance_type",
                "softwood_merch_irw_frac",
                "softwood_other_irw_frac",
                "softwood_stem_snag_irw_frac",
                "softwood_branch_snag_irw_frac",
                "hardwood_merch_irw_frac",
                "hardwood_other_irw_frac",
                "hardwood_stem_snag_irw_frac",
                "hardwood_branch_snag_irw_frac",
            ]
        ]
        # Check if df contains wildcards ?
        contains_question_mark = df.apply(
            lambda row: row.astype(str).str.contains("\?").any(), axis=1
        ).unique()
        if contains_question_mark:
            raise ValueError(f"The irw_frac contains question marks {df}")
        return df

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
        cols_of_interest = self.classifiers_list + index_cols + fluxes_cols
        df = self.pools_fluxes[cols_of_interest]
        # Keep only lines where there are fluxes to products.
        selector = df[fluxes_cols].sum(axis=1) > 0
        df = df.loc[selector].reset_index(drop=True)
        # Merge with IRW fractions
        coi = [
            "status",
            "region",
            "forest_type",
            "mgmt_type",
            "mgmt_strategy",
            "con_broad",
            "disturbance_type",
        ]
        df = df.merge(self.irw_frac, on=coi, how="left")
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
        """Allocate fluxes by age to a dbh_alloc distrubution"""
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
        """Allocate fluxes by age to a dbh_alloc distrubution"""
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
    def fluxes_by_grade(self) -> pandas.DataFrame:
        """Aggregate previous data frame and reshape wide by feedstock"""
        index = ["year", "grade"]
        df_long = (
            self.fluxes_by_grade_dbh.groupby(index)["tc_irw"].agg("sum").reset_index()
        )
        df = df_long.pivot(
            columns="grade", index=["year"], values="tc_irw"
        ).reset_index()
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

        """
        # Country statistics on domestic harvest
        dstat = hwp_common_input.prod_from_dom_harv_stat
        # CBM output
        df_out = self.fluxes_by_grade
        index = ["area", "year"]
        cols = [
            "sw_dom_tc",
            "wp_dom_tc",
            "pp_dom_tc",
            "recycled_paper_prod",
            "recycled_wood_prod",
        ]
        # Keep data for the last n years and for the selected country
        selector = dstat["year"] > dstat["year"].max() - self.n_years_dom_frac
        selector &= dstat["area"] == self.runner.country.country_name
        dstat = dstat.loc[selector, index + cols]
        dstat = dstat.fillna(0)
        # Merge country statistics with CBM output
        df = df_out.merge(dstat, on="year", how="right")
        # calculate the fractions for n years available
        df["sw_fraction"] = df["sw_dom_tc"] / df["sawlogs"]
        df["pp_fraction"] = df["pp_dom_tc"] / df["pulpwood"]
        df["wp_fraction"] = df["wp_dom_tc"] / (
            (df["sawlogs"] - df["sw_dom_tc"]) + (df["pulpwood"] - df["pp_dom_tc"])
        )

        # Check if available raw material is sufficient to produce the amount
        # of semi finished products reported by countries.
        sw_selector = df["sw_fraction"] > 1
        if any(sw_selector):
            msg = "Reported sawnwood production can not be satisfied from "
            msg += "sawlogs production from CBM for the following years:\n"
            msg += f"{df.loc[sw_selector]}"
            raise ValueError(msg)

        pp_selector = df["pp_fraction"] > 1
        if any(pp_selector):
            msg = "Reported paper production can not be satisfied from "
            msg += "pulpwood production from CBM for the following years:\n"
            msg += f"{df.loc[pp_selector]}"
            raise ValueError(msg)

        wp_selector = df["wp_fraction"] > 1
        if any(wp_selector):
            msg = "Reported panel production can not be satisfied from "
            msg += "pulpwood and sawnwood production from CBM for the following years:\n"
            msg += f"{df.loc[wp_selector]}"
            raise ValueError(msg)
        # Compute the average of the selected columns
        selected_cols = [
            "sw_fraction",
            "pp_fraction",
            "wp_fraction",
            "recycled_paper_prod",
            "recycled_wood_prod",
        ]
        mean_frac = df[selected_cols].mean()
        return mean_frac

    @property  # Don't cache, in case we change the number of years
    def fraction_semifinished(self) -> pandas.DataFrame:
        """Fraction of semi finished products

        Either default values or values from a scenario input files:

        - The default values are from the fraction_semifinished_n_years_mean
          method
        - The input files values are from
          hwp_common_input.hwp_fraction_semifinished_scenario
        """
        mean_frac = self.fraction_semifinished_n_years_mean
        # Default scenario
        if self.hwp_frac_scenario == "default":
            max_year = self.runner.country.base_year + self.runner.num_timesteps
            df =  pandas.DataFrame({"year" : range(1900, max_year+1)})
            cols = [
                "sw_fraction",
                "pp_fraction",
                "wp_fraction",
                "recycled_paper_prod",
                "recycled_wood_prod",
            ]
            for col in cols:
                df[col] = mean_frac[col]
            # Return
            return df
        # Other scenarios
        df = hwp_common_input.hwp_fraction_semifinished_scenario.copy()
        selector = df["country"] == self.runner.country.country_name
        selector &= df["hwp_frac_scenario"] == self.hwp_frac_scenario
        df.drop(columns=["country", "hwp_frac_scenario"], inplace=True)
        # Add recycled values from the mean table
        df["recycled_paper_prod"] = mean_frac["recycled_paper_prod"]
        df["recycled_wood_prod"] = mean_frac["recycled_wood_prod"]
        return df





    @property  # Don"t cache, in case we change the number of years
    def prod_from_dom_harv_sim(self) -> pandas.DataFrame:
        """Compute the production of sanwood, panels and paper from domestic
        harvest as an output of the CBM simulated amounts of sawlogs and
        pulpwood.

        Illustrate a change of the sw, wp, pp fractions:

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> hwp = runner.post_processor.hwp
            >>> print("Fractions before modification, in the default scenario")
            >>> print(hwp.fraction_semifinished_n_years_mean)
            >>> print(hwp.fraction_semifinished)
            >>> print(hwp.prod_from_dom_harv_sim)
            >>> print(hwp.stock_sink_results)

            >>> # Change the fraction semi finished
            >>> runner.post_processor.hwp.hwp_frac_scenario = "more_sw"
            >>> print("Fractions in the scenario")
            >>> print(hwp.fraction_semifinished)
            >>> # Display the effect on the production from domestic harvest
            >>> print(hwp.prod_from_dom_harv_sim)
            >>> # Display the effect on the final results
            >>> print(hwp.stock_sink_results)

        """
        df = self.fluxes_by_grade.copy()
        # Add the fractions to the CBM output data
        df = df.merge(self.fraction_semifinished, on="year")
        # Compute production from domestic harvest for the future
        df["sw_dom_tc"] = df["sawlogs"] * df["sw_fraction"]
        df["wp_dom_tc"] = df["sawlogs"] * df["wp_fraction"]
        df["pp_dom_tc"] = df["pulpwood"] * df["pp_fraction"]
        # Correct for recycling
        df["wp_dom_tc"] += df["recycled_wood_prod"] * hwp_common_input.c_wp
        df["pp_dom_tc"] += df["recycled_paper_prod"] * hwp_common_input.c_pp
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
        dstat = hwp_common_input.prod_from_dom_harv_stat.copy()
        df_out = self.prod_from_dom_harv_sim.copy()
        cols = ["sw_dom_tc", "wp_dom_tc", "pp_dom_tc"]
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

    @property  # Don't cache, in case we change the number of years
    def prepare_decay_and_inflow(self):
        """Prepare decay parameters and compute inflow"""
        df = self.concat_1900_to_last_sim_year.copy()
        # Assign decay parameters inside df
        decay_params = hwp_common_input.decay_params
        for col in decay_params.columns:
            df[col] = decay_params[col].values[0]
        # Compute the corrected inflow according to decay elements in the square bracket
        # Estimate the annual inflows
        df = df.assign(
            sw_inflow=(df.sw_dom_tc * df.k1_sw),
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
            >>> df = runner.post_processor.hwp.build_hwp_stock
            >>> cols = ['sw_stock', 'wp_stock', 'pp_stock']
            >>> df.set_index("year")[cols].plot()
            >>> plt.show()

        """

        df = self.prepare_decay_and_inflow.copy()
        cols = ["sw_inflow", "wp_inflow", "pp_inflow"]
        cols += ["e_sw", "e_wp", "e_pp"]
        df = df[["year"] + cols]
        # Initiate stock values
        df["sw_stock"] = 0.0  # Keep it with a dot to create a floating point number
        df["wp_stock"] = 0.0
        df["pp_stock"] = 0.0
        # Compute the stock for each semi finite product for all subsequent years
        df = df.set_index("year")
        for t in range(df.index.min() + 1, df.index.max()):
            df.loc[t, "sw_stock"] = (
                df.loc[t - 1, "sw_stock"] * df.loc[t, "e_sw"] + df.loc[t, "sw_inflow"]
            )
            df.loc[t, "wp_stock"] = (
                df.loc[t - 1, "wp_stock"] * df.loc[t, "e_wp"] + df.loc[t, "wp_inflow"]
            )
            df.loc[t, "pp_stock"] = (
                df.loc[t - 1, "pp_stock"] * df.loc[t, "e_pp"] + df.loc[t, "pp_inflow"]
            )
        df.reset_index(inplace=True)
        df.fillna(0, inplace=True)
        # Compute the total stock
        df["hwp_tot_stock_tc"] = df["sw_stock"] + df["wp_stock"] + df["pp_stock"]

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

        df = self.prepare_decay_and_inflow.copy()
        cols = ["sw_inflow", "wp_inflow", "pp_inflow"]
        cols += ["e_sw", "e_wp", "e_pp", "k_sw", "k_wp", "k_pp"]
        df = df[["year"] + cols]
        # retain only the first five years including 1990
        df = df[df["year"] >= 1990]
        # Initiate stock values as average of 1990-1995 as the average of the
        # first five years for each inflow type
        df["sw_stock"] = (df["sw_inflow"].head(5).mean()) / (df["k_sw"].head(5).mean())
        df["wp_stock"] = (df["wp_inflow"].head(5).mean()) / (df["k_wp"].head(5).mean())
        df["pp_stock"] = (df["pp_inflow"].head(5).mean()) / (df["k_pp"].head(5).mean())
        # Compute the stock for each semi finite product for all subsequent years
        df = df.set_index("year")
        for t in range(df.index.min() + 1, df.index.max()):
            df.loc[t, "sw_stock"] = (
                df.loc[t - 1, "sw_stock"] * df.loc[t, "e_sw"] + df.loc[t, "sw_inflow"]
            )
            df.loc[t, "wp_stock"] = (
                df.loc[t - 1, "wp_stock"] * df.loc[t, "e_wp"] + df.loc[t, "wp_inflow"]
            )
            df.loc[t, "pp_stock"] = (
                df.loc[t - 1, "pp_stock"] * df.loc[t, "e_pp"] + df.loc[t, "pp_inflow"]
            )
        df.reset_index(inplace=True)
        df.fillna(0, inplace=True)
        # Compute the total stock
        df["hwp_tot_stock_tc"] = df["sw_stock"] + df["wp_stock"] + df["pp_stock"]
        # Do the difference between consecutive years
        df["hwp_tot_diff_tc"] = df["hwp_tot_stock_tc"].diff(periods=1)
        # Stock diff shifted by one year
        # df['hwp_tot_diff_tc_m1'] = df['hwp_tot_stock_tc'].diff(periods=1).shift(-1)
        df["hwp_tot_sink_tco2"] = df["hwp_tot_diff_tc"] * (-44 / 12)
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
        df["fw_dm"] = df["tc_fw"] / 0.5
        # Estimate the CO2 equivalent emissions for non CO2 gases
        df["fw_ghg_co2_eq"] = (
            df["fw_dm"] * df["ncv_x_ef_ch4_x_gwp"]
            + df["fw_dm"] * df["ncv_x_ef_n2o_x_gwp"]
        )
        # Estimate the Total Green House Gas Emissions as CO2 Equivalent
        df["fw_co2_eq"] = df["fw_ghg_co2_eq"] + df["tc_fw"] * 44 / 12
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
        df = hwp_common_input.ctf_unfccc
        # Select the country
        selector = df["member_state"] == self.runner.country.country_name
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

        """
        # Load GHG emissions reported by country to UNFCCC for HWP pool
        cols =  ['member_state', 'year', 'crf_hwp_tco2']
        df_ctf = self.ctf_unfccc[cols].copy()
        df_ctf['year'] = df_ctf['year'].astype(int)
       
        # Load stock and sink
        cols = ["year", "hwp_tot_stock_tc", "hwp_tot_sink_tco2"]
        # Initial year 1900 (IPCC 2006/2018/2019)
        df_1900 = self.build_hwp_stock_since_1900[cols].copy()
        # Add '_1900' to the columns
        cols_1900 = ["hwp_tot_stock_tc", "hwp_tot_sink_tco2"]
        df_1900 = df_1900.rename(columns={col: f"{col}_1900" for col in cols_1900})
        selector = df_1900["year"] >= 1990
        df_1900 = df_1900.loc[selector]
        
        # Initial year 1990 (IPCC 2013)
        df_1990 = self.build_hwp_stock_since_1990[cols]
        # Add '_1990' to the columns
        cols_1990 = ["hwp_tot_stock_tc", "hwp_tot_sink_tco2"]
        df_1990 = df_1990.rename(columns={col: f"{col}_1990" for col in cols_1990})
        
        # Load GHG emissions from burning wood for energy
        cols = ["year", "fw_ghg_co2_eq", "fw_co2_eq"]
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
        return df[cols]

