#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

from typing import Union, List

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
