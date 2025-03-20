from functools import cached_property
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
    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        self.classifiers_list = self.parent.classifiers_list
        # Use pool fluxes to get area and age class as well
        self.pools_fluxes = self.runner.output.pool_flux

    def __repr__(self):
        return '%s object code "%s"' % (self.__class__, self.runner.short_name)

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
    def fluxes_to_irw(self) -> pandas.DataFrame:
        """Fluxes to Industrial Roundwood Aggregated by index Extract the IRW
        only, e.g. separate the df as IRW ub exclude bark, because cbm output
        includes the barkand add it to FW. E.g., "df ['softwood_merch']" is the
        IRW fraction.
        """
        df = self.fluxes_to_products
        # Add bark fraction 
        df = df.merge(self.parent.wood_density_bark_frac, on="forest_type", how="left")

        # Keep only the IRW fraction by multiplying with the fractions coming from self.irw_frac
        df["tc_soft_irw_merch"] = ( df["softwood_merch_to_product"] * df["softwood_merch_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_soft_irw_other"] = ( df["softwood_other_to_product"] * df["softwood_other_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_soft_irw_stem_snag"] = ( df["softwood_stem_snag_to_product"] * df["softwood_stem_snag_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_soft_irw_branch_snag"] = ( df["softwood_branch_snag_to_product"] * df["softwood_branch_snag_irw_frac"] * (1 - df["bark_frac"]))

        df["tc_hard_irw_merch"] = ( df["hardwood_merch_to_product"] * df["hardwood_merch_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_hard_irw_other"] = ( df["hardwood_other_to_product"] * df["hardwood_other_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_hard_irw_stem_snag"] = ( df["hardwood_stem_snag_to_product"] * df["hardwood_stem_snag_irw_frac"] * (1 - df["bark_frac"]))
        df["tc_hard_irw_branch_snag"] = ( df["hardwood_branch_snag_to_product"] * df["hardwood_branch_snag_irw_frac"] * (1 - df["bark_frac"]))

        # Aggregate
        index = ["forest_type", "mgmt_type", "mgmt_strategy", "con_broad", "age_class"]
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
        index = ['mgmt_type', 'mgmt_strategy', 'age_class', "forest_type"]
        df = self.fluxes_to_irw.merge(dbh_alloc, on=index, how="left")
        return df

