#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# Third party modules #
import numpy

# First party modules #

# Internal modules #

class SilvCheck:
    """
    Check the consistency of silviculture input files

    Whenever possible tests are based on raw input files available before the run
    has started, when SIT is not available yet.

        >>> from libcbm_runner.core.continent import continent
        >>> r = continent.combos['special'].runners["LU"][-1]

    Input `events_templates`and `irw_frac_by_dist`

        >>> r.silv.events.raw
        >>> r.silv.irw_frac.raw

    Check that fuel wood disturbances don't generate industrial roundwood:

        >>> r.qaqc.silv_check.fw_doesnt_create_irw()

    """

    def __init__(self, qaqc):
        # Default attributes #
        self.runner = qaqc.runner

    def fw_doesnt_create_irw(self):
        """Check that fuel wood only disturbances don't generate industrial roundwood"""
        index = ["disturbance_type", "product_created"]
        prod_by_dist = (self.runner.silv.events.raw
                        .set_index(index).index
                        .unique().to_frame(index=False))
        fw_by_dist = prod_by_dist[prod_by_dist["product_created"] == "fw_only"]

        # Keep industrial roundwood fractions only for the fuel wood disturbances
        df = (self.runner.silv.irw_frac.raw
              .merge(fw_by_dist, on="disturbance_type", how="inner"))

        # Exclude identifier columns to find the name of the value columns
        cols = self.runner.silv.irw_frac.raw
        identifiers =  self.runner.silv.irw_frac.dup_cols
        identifiers += ["dist_type_name"]
        val_cols = list(set(cols) - set(identifiers))
        # assert value columns are zero
        agg_cols = {col: "sum" for col in val_cols}
        df_agg = df.groupby(["disturbance_type", "product_created"])
        df_agg = df_agg.agg(agg_cols)
        if not numpy.allclose(df_agg.sum(), 0):
            msg = "fuel wood only disturbances "
            msg += "should not generate industrial roundwood:"
            raise ValueError(msg, df_agg)










