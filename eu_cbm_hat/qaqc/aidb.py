#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.

Usage:

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['reference'].runners["ZZ"][-1]
    >>> runner.qaqc.aidb_check.run_all_checks()

Compare one country's table to all other countries, finding common rows.

    For each table in the aidb, an aggregated table
    with all countries data should be stored as a
    parquet file in the following directory

    eu_cbm_data/output_agg/aidb_comparison



"""

import pandas

AIDB_TABLES = [
    "admin_boundary",
    "admin_boundary_tr",
    "afforestation_initial_pool",
    "afforestation_pre_type",
    "afforestation_pre_type_tr",
    "biomass_to_carbon_rate",
    "composite_flux_indicator",
    "composite_flux_indicator_category",
    "composite_flux_indicator_category_tr",
    "composite_flux_indicator_tr",
    "composite_flux_indicator_value",
    "decay_parameter",
    "disturbance_matrix",
    "disturbance_matrix_association",
    "disturbance_matrix_tr",
    "disturbance_matrix_value",
    "disturbance_type",
    "disturbance_type_tr",
    "dom_pool",
    "eco_boundary",
    "eco_boundary_tr",
    "flux_indicator",
    "flux_indicator_sink",
    "flux_indicator_source",
    "flux_process",
    "forest_type",
    "forest_type_tr",
    "genus",
    "genus_tr",
    "growth_multiplier_series",
    "growth_multiplier_value",
    "land_class",
    "land_class_tr",
    "land_type",
    "locale",
    "pool",
    "pool_tr",
    "random_return_interval",
    "root_parameter",
    "slow_mixing_rate",
    "spatial_unit",
    "species",
    "species_tr",
    "spinup_parameter",
    "stump_parameter",
    "turnover_parameter",
    "vol_to_bio_factor",
    "vol_to_bio_forest_type",
    "vol_to_bio_genus",
    "vol_to_bio_species",
]


def check_dist_matrix_prop(df: pandas.DataFrame):
    """Check if the disturbance matrix proportions sum to one

    Usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> from eu_cbm_hat.qaqc.aidb import check_dist_matrix_prop
        >>> runner = continent.combos['reference'].runners['AT'][-1]
        >>> dist_matrix_value = runner.country.aidb.db.read_df('disturbance_matrix_value')
        >>> check_dist_matrix_prop(dist_matrix_value)

    """
    id_cols = ["disturbance_matrix_id", "source_pool_id"]
    df_check = (
        df.groupby(id_cols)["proportion"]
        .agg("sum")
        .reset_index()
        .rename(columns={"proportion": "proportion_sum"})
    )
    prop_issue = df_check.query("proportion_sum < 0.99 or proportion_sum > 1.001")
    if not prop_issue.empty:
        msg = "The disturbance matrix proportion don't sum to one."
        msg += "\nSummary data frame:"
        msg += f"\n{prop_issue}"
        msg += f"\n{prop_issue[id_cols].merge(df, on=id_cols)}"
        raise ValueError(msg)


class AIDBCheck:
    """
    Check the consistency of the AIDB

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners["ZZ"][-1]

    Check id duplication in vol_to_bio_factor

        >>> runner.qaqc.aidb_check.check_vol_to_bio_factor_id_duplication()

    Check disturbance matrix proportion sum to one

        >>> runner.qaqc.aidb_check.check_dist_matrix_proportions_sum_to_one()
    """

    def __init__(self, qaqc):
        # Default attributes #
        self.runner = qaqc.runner
        self.aidb = self.runner.country.aidb

    def run_all_checks(self):
        """Run all AIDB checks"""
        self.check_vol_to_bio_factor_id_duplication()

    def check_vol_to_bio_factor_id_duplication(self):
        """Investigate identifier duplication in the vol_to_bio_factor in the AIDB"""
        df = self.aidb.db.read_df("vol_to_bio_factor")
        # Select duplicated rows
        selector = df["id"].duplicated(keep=False)
        if any(selector):
            msg = "Duplicated ids in the vol_to_bio_factor table in the AIDB."
            msg += "The following rows are duplicated:\n"
            msg += f"{df[selector]}\n\n"
            msg += (
                "Investigate by loading the table with a command similar to this one:\n"
            )
            msg += "runner.country.aidb.db.read_df('vol_to_bio_factor')"
            raise ValueError(msg)

    def check_dist_matrix_proportions_sum_to_one(self):
        """Check if the disturbance matrix proportions sum to one"""
        dist_matrix_value = self.aidb.db.read_df("disturbance_matrix_value")
        check_dist_matrix_prop(dist_matrix_value)
