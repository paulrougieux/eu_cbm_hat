from functools import cached_property
import numpy as np
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
        self.n_years_dom_frac = 3

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
        df["tc_soft_irw_merch"] = ( df["softwood_merch_to_product"] * df["softwood_merch_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_soft_irw_other"] = ( df["softwood_other_to_product"] * df["softwood_other_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_soft_irw_stem_snag"] = ( df["softwood_stem_snag_to_product"] * df["softwood_stem_snag_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_soft_irw_branch_snag"] = ( df["softwood_branch_snag_to_product"] * df["softwood_branch_snag_irw_frac"] * (1 - df["bark_frac"]))

        df["tc_hard_irw_merch"] = ( df["hardwood_merch_to_product"] * df["hardwood_merch_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_hard_irw_other"] = ( df["hardwood_other_to_product"] * df["hardwood_other_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_hard_irw_stem_snag"] = ( df["hardwood_stem_snag_to_product"] * df["hardwood_stem_snag_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_hard_irw_branch_snag"] = ( df["hardwood_branch_snag_to_product"] * df["hardwood_branch_snag_irw_frac"] * (1 - df["bark_frac"]))
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
        df["tc_irw"] = df["tc_irw"] * df["fraction_smoothed_theoretical_volume"]
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
        selector = ~np.isclose(df_comp["tc_irw_before"], df_comp["tc_irw_after"])
        if any(selector):
            msg = f"\nThe following tc_irw values  don't match between "
            msg += "input before and after dbh allocation\n"
            msg += f"{df_comp.loc[selector]}"
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
        selector = ~np.isclose(df_comp["tc_irw_before"], df_comp["tc_irw_after"])
        if any(selector):
            msg = f"The following tc_irw values  don't match between "
            msg += "input before and after NB grading allocation\n"
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
    def fraction_semifinished(self) -> pandas.DataFrame:
        """Compute the fraction of semi finished products

        Merge country statistics on domestic harvest and
        CBM output for n common years.

        param n: Number of years to keep from domestic harvest

        Example use using 3 or 4 years:

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> runner.post_processor.hwp.n_years_dom_frac = 3
            >>> df3 = runner.post_processor.hwp.fraction_semifinished
            >>> runner.post_processor.hwp.n_years_dom_frac = 4
            >>> df4 = runner.post_processor.hwp.fraction_semifinished

        """
        # Country statistics on domestic harvest
        dstat = hwp_common_input.prod_from_dom_harv_stat
        # CBM output
        df_out = self.fluxes_by_grade
        index = ["area", "year"]
        cols = ["sw_dom_tc", "wp_dom_tc", "pp_dom_tc"]
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
        cols = ["sw_fraction", "pp_fraction", "wp_fraction"]
        mean_frac = df[cols].mean()
        return mean_frac

    @property  # Don't cache, in case we change the number of years
    def prod_from_dom_harv_sim(self) -> pandas.DataFrame:
        """Compute the fraction of semi finished products"""
        df = self.fluxes_by_grade.copy()
        cols = ["sw_fraction", "pp_fraction", "wp_fraction"]
        mean_frac = self.fraction_semifinished
        # Add the mean fraction to the CBM output data
        for col in cols:
            df[col] = mean_frac[col]
        # Compute production from domestic harvest for the future
        df["sw_dom_tc"] = df["sawlogs"] * df["sw_fraction"]
        df["wp_dom_tc"] = df["sawlogs"] * df["wp_fraction"]
        df["pp_dom_tc"] = df["pulpwood"] * df["pp_fraction"]
        return df

    @property  # Don't cache, in case we change the number of years
    def concat_1900_to_last_sim_year(self) -> pandas.DataFrame:
        """Concatenate backcasted data from 1900, reported historical country data
        and CBM output until the end of the simulation.

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
        return df

    @property  # Don't cache, in case we change the number of years
    def prepare_decay_and_inflow(self):
        """Prepare decay parameters and compute inflow"""

        df = self.concat_1900_to_last_sim_year.copy()
        # Define half life in years
        hl_sw = 35
        hl_wp = 25
        hl_pp = 2
        hl_sw_wp = 30
        # prepare the params according the needs in HWP calcualtions
        df["log_2"] = np.log(2)
        df["hl_sw"] = hl_sw
        df["hl_wp"] = hl_wp
        df["hl_pp"] = hl_pp
        df["hl_sw_wp"] = hl_sw_wp
        # calculate **k_** the decay constant for each of SW, WP, PP
        df = df.assign(
            k_sw=(df.log_2 / df.hl_sw),
            k_wp=(df.log_2 / df.hl_wp),
            k_pp=(df.log_2 / df.hl_pp),
            k_sw_wp=(df.log_2 / df.hl_sw_wp),
        )
        # calculate **e_** the remaining C stock from the historical stock, e-k (see see eq. 2.8.5 (gpg)),
        df = df.assign(
            e_sw=np.exp(-df.k_sw),
            e_wp=np.exp(-df.k_wp),
            e_pp=np.exp(-df.k_pp),
            e_sw_wp=np.exp(-df.k_sw_wp),
        )
        # calculate **k1_** the remaining from the current year inflow, k1=(1-e-k)/k (see eq. 2.8.2 (gpg))
        df = df.assign(
            k1_sw=(1 - df.e_sw) / df.k_sw,
            k1_wp=(1 - df.e_wp) / df.k_wp,
            k1_pp=(1 - df.e_pp) / df.k_pp,
        )
        # Compute the corrected inflow according to decay elements in the square bracket
        # Estimate the annual inflows
        df = df.assign(
            sw_inflow=(df.sw_dom_tc * df.k1_sw),
            wp_inflow=(df.wp_dom_tc * df.k1_wp),
            pp_inflow=(df.pp_dom_tc * df.k1_pp),
        )
        return df

    @property  # Don't cache, in case we change the number of years
    def build_hwp_stock(self):
        """Build HWP stock values

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
        df["sw_stock"] = 0
        df["wp_stock"] = 0
        df["pp_stock"] = 0
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
