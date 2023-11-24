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
from eu_cbm_hat.post_processor.harvest import Harvest
from eu_cbm_hat.post_processor.area import Area
from eu_cbm_hat.post_processor.stock import Stock


class PostProcessor(object):
    """
    This class will xxxx.

    Get the pools and sink table with additional columns from the post processor

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.pools
        >>> runner.post_processor.sink

    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        self.runner = parent
        self.classifiers = self.runner.output.classif_df
        self.classifiers_list = self.classifiers.columns.to_list()
        self.classifiers_list.remove("identifier")
        self.classifiers_list.remove("timestep")
        self.classifiers["year"] = self.runner.country.timestep_to_year(
            self.classifiers["timestep"]
        )
        self.state = self.runner.output["state"]
        # Define disturbance types
        self.afforestation_dist_type = 8
        self.deforestation_dist_type = 7
        # Check the names correspond to the one given in disturbance_types.csv
        dist_def = self.runner.country.orig_data.get_dist_description("deforestation")
        assert all(
            dist_def["dist_type_name"].head(1) == str(self.deforestation_dist_type)
        )
        dist_aff = self.runner.country.orig_data.get_dist_description("afforestation")
        assert all(
            dist_aff["dist_type_name"].head(1) == str(self.afforestation_dist_type)
        )

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
        """Pools used for the sink computation"""
        index = ["identifier", "timestep"]
        # Data frame of pools content at the maximum disaggregated level by
        # identifier and timestep that will be sent to the other sink functions
        df = (
            self.runner.output["pools"].merge(self.classifiers, "left", on=index)
            # Add 'time_since_land_class_change' and 'time_since_last_disturbance'
            .merge(self.state, "left", on=index)
        )
        ###################################################
        # Compute the area afforested in the current year #
        ###################################################
        # This will be used to treat afforestation soil stock change from NF.
        # This corresponds to time_since_land_class_change==1
        selector_afforest = df["status"].str.contains("AR")
        selector_afforest &= df["time_since_last_disturbance"] == 1
        selector_afforest &= df["last_disturbance_type"] == self.afforestation_dist_type
        df["area_afforested_current_year"] = df["area"] * selector_afforest
        ###################################################
        # Compute the area deforested in the current year #
        ###################################################
        selector_deforest = df["last_disturbance_type"] == self.deforestation_dist_type
        selector_deforest &= df["time_since_last_disturbance"] == 1
        df["area_deforested_current_year"] = df["area"] * selector_deforest
        return df

    @cached_property
    def fluxes(self):
        """Fluxes used for the sink computation"""
        index = ["identifier", "timestep"]
        # Data frame of fluxes at the maximum disaggregated level by
        # identifier and timestep that will be sent to the other functions
        df = (
            self.runner.output["flux"].merge(self.classifiers, "left", on=index)
            # Add 'time_since_land_class_change'
            .merge(self.state, "left", on=index)
        )
        return df

    @cached_property
    def area(self):
        """Compute the forest carbon sink"""
        return Area(self)

    @cached_property
    def sink(self):
        """Compute the forest carbon sink"""
        return Sink(self)

    @cached_property
    def harvest(self):
        """Compute harvest expected and provided"""
        return Harvest(self)
    
    @cached_property
    def stock(self):
        """Compute standing stocks"""
        return Stock(self)

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
