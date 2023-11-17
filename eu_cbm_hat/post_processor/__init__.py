#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

from typing import Union, List
from functools import cached_property
from eu_cbm_hat.post_processor.sink import Sink

class PostProcessor(object):
    """
    This class will xxxx.
    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        self.runner = parent

    def __repr__(self):
        return '%s object code "%s"' % (self.__class__, self.runner.short_name)

    def __call__(self):
        """
        xxxx.
        """
        return
        # Message #
        self.parent.log.info("Post-processing results.")
        # Lorem #
        pass

    @cached_property
    def pools(self):
        """Pools used for the sink computation
        """
        classifiers = self.runner.output.classif_df
        classifiers["year"] = self.runner.country.timestep_to_year(classifiers["timestep"])
        index = ["identifier", "timestep"]
        # Data frame of pools content at the maximum disaggregated level by
        # identifier and timestep that will be sent to the other sink functions
        df = (
            self.runner.output["pools"].merge(classifiers, "left", on=index)
            # Add 'time_since_land_class_change' and 'time_since_last_disturbance'
            .merge(self.runner.output["state"], "left", on=index)
        )
        ###################################################
        # Compute the area afforested in the current year #
        ###################################################
        # This will be used to treat afforestation soil stock change from NF.
        # This corresponds to time_since_land_class_change==1
        selector_afforest = df["status"].str.contains("AR")
        selector_afforest &= df["time_since_land_class_change"] == 1
        # Exclude land_class==0 we are not interested in the internal CBM mechanism
        # that returns the land class to zero 20 years after the afforestation
        # event.
        selector_afforest &= df["land_class"] != 0
        df["area_afforested_current_year"] = df["area"] * selector_afforest
        ###################################################
        # Compute the area deforested in the current year #
        ###################################################
        selector_deforest = df["last_disturbance_type"] == 7
        selector_deforest &= df["time_since_land_class_change"] == 1
        df["area_deforested_curent_year_without_land_class"] = df["area"] * selector_deforest
        # Keep only land_class==15 we are not interested in the internal CBM
        # mechanism that changes to land class 5 after 20 years.
        selector_deforest &= df["land_class"] == 15
        df["area_deforested_current_year"] = df["area"] * selector_deforest
        return df

    @cached_property
    def fluxes(self):
        """Fluxes used for the sink computation"""
        classifiers = self.runner.output.classif_df
        classifiers["year"] = self.runner.country.timestep_to_year(classifiers["timestep"])
        index = ["identifier", "timestep"]
        # Data frame of fluxes at the maximum disaggregated level by
        # identifier and timestep that will be sent to the other functions
        df = (
            self.runner.output["flux"].merge(classifiers, "left", on=index)
            # Add 'time_since_land_class_change'
            .merge(self.runner.output["state"], "left", on=index)
        )
        # TODO: Add area subject to harvest based on fluxes to products and
        # time since last disturbance
        product_cols = df.columns[df.columns.str.contains("to_product")]
        df["to_product"] = df[product_cols].sum(axis=1)
        
        return df

    @cached_property
    def sink(self):
        """Compute the forest carbon sink"""
        return Sink(self)

    def sum_flux_pool(self, by: Union[List[str], str], pools: List[str]):
        """Aggregate the flux pool table over the "by" variables and for the
        given list of pools.

        Example

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner_at = continent.combos["pikssp2"].runners["AT"][-1]
            >>> living_biomass_pools = [
            >>>     "softwood_merch",
            >>>     "softwood_other",
            >>>     "softwood_foliage",
            >>>     "softwood_coarse_roots",
            >>>     "softwood_fine_roots",
            >>>     "hardwood_merch",
            >>>     "hardwood_foliage",
            >>>     "hardwood_other",
            >>>     "hardwood_coarse_roots",
            >>>     "hardwood_fine_roots",
            >>> ]
            >>> runner_at.post_processor.sum_flux_pool(by="year", pools=living_biomass_pools)
            >>> runner_at.post_processor.sum_flux_pool(by=["year", "forest_type"], pools=living_biomass_pools)

        """
        df = self.runner.output.pool_flux.groupby(by)[pools].sum()
        df.reset_index(inplace=True)
        return df


