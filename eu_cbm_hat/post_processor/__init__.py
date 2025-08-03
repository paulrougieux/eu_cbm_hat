#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

from typing import Union, List
from functools import cached_property
import numpy as np
import pandas as pd

from eu_cbm_hat.post_processor.sink import Sink
from eu_cbm_hat.post_processor.harvest import Harvest
from eu_cbm_hat.post_processor.hwp import HWP
from eu_cbm_hat.post_processor.area import Area
from eu_cbm_hat.post_processor.stock import Stock
from eu_cbm_hat.post_processor.nai import NAI
from eu_cbm_hat.post_processor.npp import NPP
from eu_cbm_hat.post_processor.growth_curve import GrowthCurve
from eu_cbm_hat.post_processor.diagnostic import Diagnostic


class PostProcessor(object):
    """
    Compute aggregates based on the pools and sink table output from the model

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.pools
        >>> runner.post_processor.sink

        >>> runner.post_processor.pools_morf
        >>> runner.post_processor.fluxes_morf
        >>> runner.post_processor.pools_fluxes_morf

    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        self.runner = parent
        self.classifiers = self.runner.output.classif_df
        self.classifiers_list = self.classifiers.columns.to_list()
        self.classifiers_list.remove("identifier")
        self.classifiers_list.remove("timestep")
        self.classifiers["year"] = self.runner.timestep_to_year(
            self.classifiers["timestep"]
        )
        # Index used for both self.pools_morf and self.fluxes_morf
        self.index_morf = ["year", "disturbance_type"] + self.classifiers_list
        self.state = self.runner.output["state"]
        self.params = self.runner.output["parameters"]
        # Define disturbance types
        self.afforestation_dist_type = 8
        self.deforestation_dist_type = 7
        # Check that the afforestation an deforestation disturbance type numbers
        # correspond to the 'dist_type_name' given in disturbance_types.csv
        dist_def = self.get_dist_description("deforestation")
        assert all(
            dist_def["dist_type_name"].astype(str).unique()
            == str(self.deforestation_dist_type)
        )
        dist_aff = self.get_dist_description("afforestation")
        assert all(
            dist_aff["dist_type_name"].astype(str).unique()
            == str(self.afforestation_dist_type)
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

    def get_dist_description(self, pattern):
        """Get disturbance types which contain the given pattern in their name"""
        return self.runner.country.orig_data.get_dist_description(pattern)

    @cached_property
    def pools(self):
        """Pools used for the sink computation

        Number of rows in the pools table:

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> pools = runner.post_processor.pools
            >>> pools.value_counts(["year"]).reset_index()

        """
        index = ["identifier", "timestep"]
        # Data frame of pools content at the maximum disaggregated level by
        # identifier and timestep that will be sent to the other sink functions
        df = (
            self.runner.output["pools"]
            .merge(self.classifiers, "left", on=index)
            # Add 'time_since_land_class_change' and 'time_since_last_disturbance'
            .merge(self.state, "left", on=index)
            .merge(self.params, "left", on=index)
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
            self.runner.output["flux"]
            .merge(self.classifiers, "left", on=index)
            # Add 'time_since_land_class_change'
            .merge(self.state, "left", on=index)
            .merge(self.params, "left", on=index)
        )
        return df

    @cached_property
    def pools_morf(self):
        """Pools columns summed for merchantable, other, roots and foliage,
        across classifiers"""
        df = self.pools.copy()
        column_dict = {
            "merch": ["softwood_merch", "hardwood_merch"],
            "other": ["softwood_other", "hardwood_other"],
            "roots": [
                "softwood_fine_roots",
                "hardwood_fine_roots",
                "softwood_coarse_roots",
                "hardwood_coarse_roots",
            ],
            "foliage": ["softwood_foliage", "hardwood_foliage"],
        }
        for key, cols in column_dict.items():
            df[key] = df[cols].sum(axis=1)
        selected_columns = ["area"] + list(column_dict.keys())
        df_agg = df.groupby(self.index_morf)[selected_columns].agg("sum")
        df_agg = df_agg.reset_index()
        return df_agg

    @cached_property
    def fluxes_morf(self):
        """Fluxes columns summed for merchantable to products, natural turnover
        (from merch and OWC) disturbance litter input (from merch and OWC)"""
        df = self.fluxes.copy()
        # check this df
        column_dict = {
            "merch_prod": ["softwood_merch_to_product", "hardwood_merch_to_product"],
            # I add this flux to prod
            "oth_prod": ["softwood_other_to_product", "hardwood_other_to_product"],
        }
        for key, cols in column_dict.items():
            df[key] = df[cols].sum(axis=1)
        selected_columns = list(column_dict.keys())
        selected_columns += [
            # fluxes for NAI
            "turnover_merch_litter_input",
            "turnover_oth_litter_input",
            "disturbance_merch_litter_input",
            "disturbance_oth_litter_input",
            # fluxes for NAI
            "disturbance_merch_to_air",
            "disturbance_oth_to_air",
            # fluxes for NPP only
            # transfers to non living pools through disturbances
            'disturbance_fol_litter_input',
            'disturbance_coarse_litter_input',
            'disturbance_fine_litter_input',        
            'disturbance_fol_to_air',
            'disturbance_coarse_to_air',
            'disturbance_fine_to_air',
            # transfers to non living pools through natural decay
            'turnover_fol_litter_input',
            'turnover_coarse_litter_input',
            'turnover_fine_litter_input'            
            ]
        df_agg = df.groupby(self.index_morf)[selected_columns].agg("sum")
        df_agg = df_agg.reset_index()
        return df_agg

    @cached_property
    def pools_fluxes_morf(self):
        """Merchantable pools and fluxes aggregated at the morf level on the
        columns and at the classifiers level on the rows

        To be used in the Net Annual Increment computation.
        """
        df = self.pools_morf.merge(self.fluxes_morf, on=self.index_morf)
        return df

    @cached_property
    def area(self):
        """Compute the forest carbon sink"""
        return Area(self)

    @cached_property
    def diagnostic(self):
        """Net Annual Increment"""
        return Diagnostic(self)

    @cached_property
    def growth_curve(self):
        """Growth curve"""
        return GrowthCurve(self)

    @cached_property
    def harvest(self):
        """Compute harvest expected and provided"""
        return Harvest(self)

    @cached_property
    def hwp(self):
        """Compute harvest expected and provided"""
        return HWP(self)

    @cached_property
    def nai(self):
        """Net Annual Increment"""
        return NAI(self)
    
    @cached_property
    def npp(self):
        """Net primary productivity"""
        return NPP(self)

    @cached_property
    def sink(self):
        """Compute the forest carbon sink"""
        return Sink(self)

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

    @cached_property
    def wood_density_bark_frac(self):
        """Wood density and bark fraction, ready to join

        Check wood density and bark fraction in all countries:

            >>> from eu_cbm_hat.post_processor.agg_combos import get_df_all_countries
            >>> wood_density_bark_all = get_df_all_countries(
            >>>     combo_name="reference",
            >>>     runner_method_name="post_processor.wood_density_bark_frac"
            >>> )

        """
        df = self.runner.silv.coefs.raw
        return df[["forest_type", "wood_density", "bark_frac"]].copy()

    @cached_property
    def irw_frac(self):
        """load irw_frac for converting output to IRW and FW, ready to join

        irw_frac is not defined by year. It is however possible to define many
        values for the irw_frac in the combo.config["irw_frac_by_dist"].

        - an irw_frac data frame is used by the cbm/dynamic.py within each time
          step, where there is only one possible year and therefore one possible
          scenario.

        - in post processing however, we have many years. Therefore we need to
          expand irw_frac for all years defined in
          combo.config["irw_frac_by_dist"] so that the year column can
          subsequently be used in the merge index, when we merge with fluxes to
          products.
        
        """
        # Choices made for `irw` fraction in the current combo.
        # This can be defined differently for every year
        irw_frac_dict = self.runner.combo.config["irw_frac_by_dist"].copy()
        df_raw = self.runner.silv.irw_frac.raw
        # Replace spaces by NA values
        # Necessary because there were spaces in some countries such as
        # df_raw.climate.unique()
        # # array([' '], dtype=object)
        # df_raw.region.unique()
        # # array([' '], dtype=object)
        for col in self.classifiers_list:
            df_raw[col] = df_raw[col].replace(r'^\s*$', np.nan, regex=True)

        # Create a data frame with scenario and year
        scenarios = pd.DataFrame(
            {"year": irw_frac_dict.keys(), "scenario": irw_frac_dict.values()}
        )
        # Keep only scenarios defined for the given years through an inner
        # merge
        df = df_raw.merge(scenarios, on=["scenario"], how="inner")
        # Put the year back in first place
        cols = df.columns.to_list()
        cols = cols[-1:] + cols[:-1]
        df = df[cols]
        # Rename flux columns to append "_irw_frac"
        cols_to_rename = df.columns[-8:]
        # Rename the columns by appending '_irw_frac'
        new_column_names = {col: f"{col}_irw_frac" for col in cols_to_rename}
        # Apply the renaming
        df.rename(columns=new_column_names, inplace=True)
        # Remove duplicate rows based on the remaining columns
        df.drop_duplicates(inplace=True)
        # convert dist_ids string to values, as needed later
        df["disturbance_type"] = df["disturbance_type"].astype(int)
        # Check if df contains wildcards ?
        contains_question_mark = df.apply(
            lambda row: row.astype(str).str.contains("\?").any(), axis=1
        ).unique()
        if contains_question_mark:
            raise ValueError(f"The irw_frac contains question marks {df}")
        return df
