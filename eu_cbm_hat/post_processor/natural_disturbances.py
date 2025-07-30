"""Get harvest expected and provided"""

from typing import Union, List
from functools import cached_property
import numpy as np
import pandas
import yaml
from eu_cbm_hat.info.harvest import combined
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ub
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ob

"""
This dictionary allows splitting the natural disturbances area, harvest and emissions 

In this script "salvage" stands for natural disturbances
"""
dist_silv_corresp = { 
                1 :'thinnings',#generic 5%
                1 :'thinnings',#generic 5% (calibration)
                2 :'salvage',#Wildfire
                3 :'final_cut',#Clearcut harvesting without salvage
                7 :'salvage',#Deforestation
                10 :'thinnings',#10% commercial thinning
                11 :'thinnings',#generic 10%
                12 :'thinnings',#10% commercial thinning
                12 :'thinnings',#15% commercial thinning
                13 :'thinnings',#generic 15%
                13 :'thinnings',#generic 20%
                14 :'thinnings',#15% commercial thinning
                14 :'thinnings',#20% commercial thinning
                15 :'thinnings',#generic 20%
                15 :'thinnings',#generic 25%
                16 :'thinnings',#20% commercial thinning
                16 :'thinnings',#25% commercial thinning
                16 :'thinnings',#30% commercial thinning
                17 :'thinnings',#generic 25%
                17 :'thinnings',#generic 30%
                18 :'thinnings',#25% commercial thinning
                18 :'thinnings',#30% commercial thinning
                18 :'thinnings',#35% commercial thinning
                18 :'thinnings',#35% Commercial thinning
                19 :'thinnings',#35% commercial thinning
                21 :'final_cut',#97% clearcut
                22 :'final_cut',#Clearcut harvesting with salvage
                24 :'final_cut',#Clearcut with slash-burn
                40 :'thinnings',#generic 15% (calibration)
                40 :'final_cut',#Stand Replacing Natural Succession
                40 :'final_cut',#Stand Replacing Natural Succession (calibration)
                41 :'salvage',#generic 40% mortality (calibration)
                41 :'final_cut',#generic 90% mortality
                41 :'final_cut',#generic 90% mortality (calibration)
                41 :'salvage',#Insects with salvage logging
                41 :'salvage',#Insects with salvage logging (calibration)
                42 :'salvage',#generic 90% mortality (calibration)
                42 :'salvage',#Insects with salvage logging (calibration)
                42 :'salvage',#Insects with salvage logging (nd_nsr), Matrix ID 25
                43 :'salvage',#generic 60% mortality (calibration)
                43 :'salvage',#Salvage logging after insects (calibration)
                45 :'salvage',#generic 90% mortality (calibration)
                45 :'salvage',#Salvage logging after insects (calibration)
                50 :'salvage',#Fire with salvage logging
                50 :'salvage',#Fire with salvage logging (calibration)
                50 :'salvage',#generic 50% mortality (calibration)
                51 :'salvage',#Fire with salvage logging (calibration)
                115 :'thinnings',#15% commercial thinning
                120 :'thinnings',#generic 40% mortality
                125 :'final_cut',#generic 70%
                130 :'final_cut',#generic 85%
                49	:'salvage',#Windstorm (with multiyears salvage, for projection)
                29	:'salvage',#Salvage year 1 post-windstorm
                30	:'salvage',#Salvage year 2 post-windstorm
                400 :'final_cut',#Stand Replacing Natural Succession (projection)
                400: 'final_cut', #Stand Replacing Natural Succession (no salvage, projection)
                401 :'thinnings',#generic 15% (projection)
                401 :'final_cut',#generic 90% mortality (projection)
                401 :'final_cut',#Stand Replacing Natural Succession (projection)
                401	: 'final_cut', #Windstorm (with full salvage in the year, for projection)
                402 :'salvage',#Insects with salvage logging (projection)
                411 :'thinnings',#generic 40% mortality (projection)
                411 :'salvage',#generic 90% mortality (projection)
                411 :'salvage',#Insects with salvage logging (projection)
                411	:'salvage',#Insect outbreak low intensity with salvage logging (projection)
                412	:'salvage',#Insect outbreak medium intensity with salvage logging (projection)
                413	:'salvage',#Insect outbreak high intensity with salvage logging (projection)
                420 :'salvage',#Insects with salvage logging (projection)
                421 :'salvage',#generic 90% mortality (projection)
                421 :'salvage',#Insects with salvage logging (projection)
                431 :'salvage',#generic 60% mortality (projection)
                431 :'salvage',#Salvage logging after insects (projection)
                451 :'salvage',#generic 90% mortality (projection)
                451 :'salvage',#Salvage logging after insects (projection)
                491 :'final_cut',#Stand Replacing Natural Succession (projection)
                500 :'salvage',#Fire with salvage logging (projection)
                501 :'salvage',#Fire with salvage logging (projection)
                501 :'salvage',#generic 50% mortality (projection)
                501	:'salvage',#Fire with salvage logging (projection)
                502	:'salvage',#Forest floor fire without salvage logging (projection)
                515 :'thinnings',#Post_conversion_LA_15%_commercial_thinning
                535 :'thinnings',#Step_1_conversion_LA_35%_commercial_thinning
                550 :'thinnings',#Step_2_conversion_LA_50%_commercial_thinning
                516 :'final_cut',#Conversion_to_u_u_con
                517 :'final_cut',#Conversion_to_u_u_broad
                518 :'final_cut',#Conversion_to_u_u_con
                615 :'thinnings',#Post_conversion_ST_15%_commercial_thinning
                625 :'thinnings',#Step_1_conversion_ST_25%_commercial_thinning
                640 :'thinnings',#Step_2_conversion_ST_40%_commercial_thinning
                700 :'final_cut',#Conversion_of_coppice_to_high_stands
                701 :'final_cut',#Conversion_of_old_stands_to_coppice
                1010 :'thinnings',#10% commercial thinning hist
                1111 :'thinnings',#generic 10% hist
                1212 :'thinnings',#10% commercial thinning hist
                1212 :'thinnings',#15% commercial thinning hist
                1313 :'thinnings',#generic 15% hist
                1313 :'thinnings',#generic 20% hist
                1414 :'thinnings',#15% commercial thinning hist
                1414 :'thinnings',#20% commercial thinning hist
                1515 :'thinnings',#generic 20% hist
                1515 :'thinnings',#generic 25% hist
                1616 :'thinnings',#20% commercial thinning hist
                1616 :'thinnings',#25% commercial thinning hist
                1616 :'thinnings',#30% commercial thinning hist
                1717 :'thinnings',#generic 25% hist
                1717 :'thinnings',#generic 30% hist
                1818 :'thinnings',#25% commercial thinning hist
                1818 :'thinnings',#30% commercial thinning hist
                1818 :'thinnings',#35% commercial thinning hist
                1818 :'thinnings',#35% Commercial thinning hist
                2121 :'final_cut',#97% clearcut hist
                2222 :'final_cut',#Clearcut harvesting with salvage hist
                2424 :'final_cut',#Clearcut with slash-burn hist
                4040 :'final_cut',#Stand Replacing Natural Succession (calibration) hist
                4141 :'salvage',#generic 40% mortality (calibration) hist
                4141 :'salvage',#generic 90% mortality (calibration) hist
                4141 :'salvage',#generic 90% mortality hist
                4141 :'salvage',#Insects with salvage logging (calibration) hist
                4242 :'salvage',#generic 90% mortality (calibration) hist
                4242 :'salvage',#Insects with salvage logging (calibration) hist
                4343 :'salvage',#generic 60% mortality (calibration) hist
                4343 :'salvage',#Salvage logging after insects (calibration) hist
                4545 :'salvage',#generic 90% mortality (calibration) hist
                4545 :'salvage',#Salvage logging after insects (calibration) hist
                115115 :'thinnings',#15% commercial thinning hist
                120120 :'thinnings',#generic 40% mortality hist
                125125 :'salvage',#generic 70% hist
                130130 :'salvage',#generic 85% hist
                }


FLUXES_DICT = {
    "loss_from_living_biomass": [
        # transfers to products
        "softwood_merch_to_product",
        "softwood_other_to_product",
        "hardwood_merch_to_product",
        "hardwood_other_to_product",
        # any direct flux to air
        "disturbance_merch_to_air",
        "disturbance_fol_to_air",
        "disturbance_oth_to_air",
        "disturbance_coarse_to_air",
        "disturbance_fine_to_air",
    ],
    "loss_from_litter": [
        "decay_v_fast_ag_to_air",
        "decay_fast_ag_to_air",
        "decay_slow_ag_to_air",
    ],
    "loss_from_dead_wood": [
        "softwood_stem_snag_to_product",
        "softwood_branch_snag_to_product",
        "hardwood_stem_snag_to_product",
        "hardwood_branch_snag_to_product",
        "decay_sw_stem_snag_to_air",
        "decay_sw_branch_snag_to_air",
        "decay_hw_stem_snag_to_air",
        "decay_hw_branch_snag_to_air",
        "decay_fast_bg_to_air",
        "decay_medium_to_air",
    ],
    "loss_from_soil": [
        "decay_v_fast_bg_to_air",
        "decay_slow_bg_to_air",
    ],
    "loss_from_non_co2_emissions": [
        "disturbance_bio_ch4_emission",
        "disturbance_bio_co_emission",
        "disturbance_domch4_emission",
        "disturbance_domco_emission",
    ],
}


class NatDist:
    """
    
    Compute the harvest expected and provided

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        self.pools = self.parent.pools
        self.fluxes = self.parent.fluxes

    def __repr__(self):
        return '%s object code "%s"' % (self.__class__, self.runner.short_name)


    @cached_property
    def nd_harvest(self):
        """Harvest from ND provided in one country"""
        df = self.fluxes
        
        # Sum all columns that have a flux to products
        cols_to_product = df.columns[df.columns.str.contains("to_product")]
        df["to_product"] = df[cols_to_product].sum(axis=1)
        
        # Keep only rows with a flux to product
        selector = df.to_product != 0
        df = df[selector]
        
        # Check we only have 1 year since last disturbance
        time_since_last = df["time_since_last_disturbance"].unique()
        if not time_since_last == 1:
            msg = "Time since last disturbance should be one"
            msg += f"it is {time_since_last}"
            raise ValueError(msg)
        # Add wood density information by forest type
        df = df.merge(self.parent.wood_density_bark_frac, on="forest_type")
    
        # Convert tons of carbon to volume under bark
        df["total_harvest_ub_provided"] = ton_carbon_to_m3_ub(df, "to_product")
        df["total_harvest_ob_provided"] = ton_carbon_to_m3_ob(df, "to_product")
    
        # add silvicultural practices
        # Add a new column to the DataFrame
        df['silv_practice'] = None
        # Match the values in df with the keys in dist_silv_corresp
        for i in range(len(df)):
            disturbance_type = df.loc[i, 'disturbance_type']
            if disturbance_type in dist_silv_corresp:
                df.loc[i, 'silv_practice'] = dist_silv_corresp[disturbance_type]
        df = df[df['silv_practice'] == 'salvage']
       
        # Area information
        index = ["identifier", "timestep"]
        area = self.pools[index + ["area"]]
        df = df.merge(area, on=index)

        df = df.groupby("year")['area'].sum().reset_index()   
        return df


    @cached_property
    def nd_emissions(self):
        """this is total CO2 emissions from all pools from NDs"""
        df = self.fluxes
        self.fluxes_dict = FLUXES_DICT.copy()
        self.groupby_nd = ["year", "silv_practice"]
        
        # Add wood density information by forest type
        #df = df.merge(self.parent.wood_density_bark_frac, on="forest_type")
        
        # Convert tons of carbon to volume under bark
        #df["total_harvest_ub_provided"] = ton_carbon_to_m3_ub(df, "to_product")
        #df["total_harvest_ob_provided"] = ton_carbon_to_m3_ob(df, "to_product")
        
        # add silvicultural practices
        # Add a new column to the DataFrame
        df['silv_practice'] = None
        # Match the values in df with the keys in dist_silv_corresp
        for i in range(len(df)):
            disturbance_type = df.loc[i, 'disturbance_type']
            if disturbance_type in dist_silv_corresp:
                df.loc[i, 'silv_practice'] = dist_silv_corresp[disturbance_type]
        df = df[df['silv_practice'] == 'salvage']

        # Area information
        index = ["identifier", "timestep"]
        area = self.pools[index + ["area"]]
        df = df.merge(area, on=index)
        
        for key in self.fluxes_dict:
            # Aggregate all pool columns to one pool value for this key
            df = df.copy()
            df.loc[:, key] = df[self.fluxes_dict[key]].sum(axis=1)*44/12
            
        cols = list(self.fluxes_dict.keys())+['area']
        df_agg = df.groupby(self.groupby_nd)[cols].agg("sum").reset_index()
        df_agg['total_emissions'] = df_agg[cols].sum(axis=1)
 
        return df_agg


        