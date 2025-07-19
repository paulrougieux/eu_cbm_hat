"""Get harvest expected and provided"""

from typing import Union, List
from functools import cached_property
from plumbing.cache import property_cached
import numpy as np
import pandas
import yaml
from eu_cbm_hat.info.harvest import combined
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ub
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ob
from eu_cbm_hat.info.silviculture import keep_clfrs_without_question_marks

"""
This dictionary is addedd to allow splitting the outputs on silvicultural practices. 
The correspondence of disturbance_types and silv_practices should be validf for all countries for the calibration period
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

class Harvest:
    """Compute the harvest expected and provided

    Methods to load intermediate data frames used in the computation of the
    harvest expected and provided:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.harvest.demand
        >>> runner.post_processor.harvest.hat_events
        >>> runner.post_processor.harvest.hat_extra
        >>> runner.post_processor.harvest.expected_agg("year")
        >>> runner.post_processor.harvest.provided
        >>> runner.post_processor.harvest.provided_agg("year")
        >>> harvest_group = ["year", "forest_type", "mgmt_type", "mgmt_strategy", "con_broad", "disturbance_type"]
        >>> runner.post_processor.harvest.provided_agg(harvest_group)

        >>> runner.post_processor.harvest.expected_provided("year")
        >>> runner.post_processor.harvest.expected_provided(["year", "forest_type"])
        >>> runner.post_processor.harvest.expected_provided(["year", "disturbance_type"])
        >>> runner.post_processor.harvest.disturbance_types
        >>> runner.post_processor.harvest.area
        >>> runner.post_processor.harvest.area_agg(["year", "disturbance"])
        >>> runner.post_processor.harvest.area_agg(["year", "disturbance", "disturbance_type"])

    Plot harvest area by disturbance type through time

        >>> from matplotlib import pyplot as plt
        >>> area_agg = runner.post_processor.harvest.area_agg(["year", "disturbance"])
        >>> area_by_dist = area_agg.pivot(columns="disturbance", index="year", values="area")
        >>> area_by_dist.plot(title="LU harvest area by disturbance type")
        >>> plt.show()

    Plot harvest volume by disturbance type through time

        >>> harvest_prov_by_dist = area_agg.pivot(columns="disturbance", index="year", values="harvest_prov_ub")
        >>> harvest_prov_by_dist.plot(title="LU harvest volume by disturbance type")
        >>> plt.show()

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        self.pools = self.parent.pools
        self.fluxes = self.parent.fluxes
        self.country = self.runner.country
        self.classif_list = self.country.orig_data.classif_list

    def __repr__(self):
        return '%s object code "%s"' % (self.__class__, self.runner.short_name)

    @cached_property
    def demand(self) -> pandas.DataFrame:
        """Get demand from the economic model using eu_cbm_hat/info/harvest.py

        Convert demand volumes from 1000m3 ub to m3 ub.
        """
        harvest_scenario_name = self.runner.combo.config["harvest"]
        irw = combined["irw"]
        irw["product"] = "irw_demand"
        fw = combined["fw"]
        fw["product"] = "fw_demand"
        df = pandas.concat([irw, fw]).reset_index(drop=True)
        # Convert volumes from 1000m3 ub to m3 ub
        df["value"] *= 1e3
        index = ["scenario", "iso2_code", "year"]
        df = df.pivot(index=index, columns="product", values="value").reset_index()
        df["rw_demand"] = df["fw_demand"] + df["irw_demand"]
        df = df.rename_axis(columns=None)
        selector = df["scenario"] == harvest_scenario_name
        selector &= df["iso2_code"] == self.runner.country.iso2_code
        return df[selector]

    @cached_property
    def hat_events(self) -> pandas.DataFrame:
        """Events from the harvest allocation tool

        Load HAT events which were saved in this line of cbm/dynamic.py:

            >>> self.runner.output.events = pandas.concat([self.runner.output.events, df[cols]])

        """
        # Load output events from the harvest allocation tool, generated in cbm/dynamic.py
        df = self.runner.output["events"]
        # Rename the amount expected by the Harvest Allocation Tool
        df.rename(columns={"amount": "amount_exp_hat"}, inplace=True)
        df["harvest_exp_hat"] = ton_carbon_to_m3_ub(df, "amount_exp_hat")
        # Check that the amount converted from tons of carbon back to cubic
        # meter gives the same value as the sum of irw_need and fw_colat
        for col in ["harvest_exp_hat", "irw_need", "fw_colat", "fw_need"]:
            df[col] = df[col].fillna(0)
        pandas.testing.assert_series_equal(
            df["harvest_exp_hat"],
            df["irw_need"] + df["fw_colat"] + df["fw_need"],
            rtol=1e-4,
            check_names=False,
        )
        # Column name consistent with runner.output["parameters"]
        df["disturbance_type"] = df["dist_type_name"]
        return df

    @cached_property
    def hat_extra(self) -> pandas.DataFrame:
        """Extra information from the harvest allocation tool"""
        df = self.runner.output["extras"]
        df.rename(
            columns={
                "index": "year",
                "harvest_irw_vol": "harvest_demand_irw",
                "harvest_fw_vol": "harvest_demand_fw",
            },
            inplace=True,
        )
        df["harvest_demand"] = df["harvest_demand_irw"] + df["harvest_demand_fw"]
        return df

    def expected_agg(self, groupby: Union[List[str], str]):
        """Harvest expected by the Harvest Allocation Tool (HAT) aggregated
        along grouping variables

        Get the harvest expected from disturbances allocated by hat which are
        allocated at some level of classifier groupings (other classifiers
        might have question marks i.e. where harvest can be allocated to any
        value of that particular classifier).

        In case of yearly information only, this will use extra information on pre
        determined disturbances from HAT cbm/dynamic.py.
        Use extra information from the HAT cbm/dynamic.py

        The `groupby` argument makes it possible to group on year, group on year
        and classifiers or group on the disturbance id.
        """
        if isinstance(groupby, str):
            groupby = [groupby]
        # Aggregate
        cols = ["irw_need", "fw_colat", "fw_need", "amount_exp_hat", "harvest_exp_hat"]
        df = self.hat_events.groupby(groupby)[cols].agg("sum").reset_index()
        # If grouping on years only, join demand from the economic model.
        if groupby == ["year"]:
            # msg = "Group by year. Get harvest demand and predetermined harvest "
            # msg += "information from the output extra table."
            # print(msg)
            df = df.merge(self.hat_extra, on="year", how="left")
            # Check that "harvest_exp_hat" computed from HAT disturbances is the
            # same as the sum of remaining irw and fw harvest computed at the
            # begining of cbm/dynamic.py
            # np.testing.assert_allclose(
            #     df["harvest_exp_hat"],
            #     df["remain_irw_harvest"] + df["remain_fw_harvest"],
            #     rtol=1e-4,
            # )
        return df

    @cached_property
    def provided(self):
        """Harvest provided in one country"""
        df = self.fluxes
        
        # Sum all columns that have a flux to products
        cols_to_product = df.columns[df.columns.str.contains("to_product")]
        df["to_product"] = df[cols_to_product].sum(axis=1)
        # Keep only rows with a flux to product
        selector = df.to_product > 0
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
        # #################
        # add irw fractions from input file to convert to IRW and FW
        df_irw = self.parent.irw_frac
        clfrs_noq = keep_clfrs_without_question_marks(df_irw, self.classif_list)
                
        # define the scenario applicable for IRW from .yaml combo
        yaml_path = self.runner.combo.yaml_path
        with open(yaml_path, 'r') as file:
            yaml_data = file.read()
        data = yaml.safe_load(yaml_data)
        min_year = min(data['irw_frac_by_dist'].keys())
        mngm_scenario = data['irw_frac_by_dist'][min_year]
        df_irw = df_irw[df_irw['scenario'] == mngm_scenario]
        df = df.merge(df_irw, how='left',
                      on=clfrs_noq + ["year", "disturbance_type"])

        #convert roundwood output to IRW and FW
        # add adintional split on con and broad
        df["irw_to_product_soft"] = (
            df["softwood_merch_to_product"]*df["softwood_merch_irw_frac"]+
            df["softwood_other_to_product"]*df["softwood_other_irw_frac"]+
            df["softwood_stem_snag_to_product"]*df["softwood_stem_snag_irw_frac"]+
            df["softwood_branch_snag_to_product"]*df["softwood_branch_snag_irw_frac"]
                                    )
        df["irw_to_product_hard"] = (
            df["hardwood_merch_to_product"]*df["hardwood_merch_irw_frac"]+
            df["hardwood_other_to_product"]*df["hardwood_other_irw_frac"]+
            df["hardwood_stem_snag_to_product"]*df["hardwood_stem_snag_irw_frac"]+
            df["hardwood_branch_snag_to_product"]*df["hardwood_branch_snag_irw_frac"]
                               )
        df["fw_to_product_soft"] = (
            df["softwood_merch_to_product"]*(1-df["softwood_merch_irw_frac"])+
            df["softwood_other_to_product"]*(1-df["softwood_other_irw_frac"])+
            df["softwood_stem_snag_to_product"]*(1-df["softwood_stem_snag_irw_frac"])+
            df["softwood_branch_snag_to_product"]*(1-df["softwood_branch_snag_irw_frac"])
                                )
        df["fw_to_product_hard"] = (    
            df["hardwood_merch_to_product"]*(1-df["hardwood_merch_irw_frac"])+
            df["hardwood_other_to_product"]*(1-df["hardwood_other_irw_frac"])+
            df["hardwood_stem_snag_to_product"]*(1-df["hardwood_stem_snag_irw_frac"])+
            df["hardwood_branch_snag_to_product"]*(1-df["hardwood_branch_snag_irw_frac"])
                            )
        df["irw_to_product"] = (df["irw_to_product_soft"] + df["irw_to_product_hard"] )
        df["fw_to_product"] = (df["fw_to_product_soft"] + df["fw_to_product_hard"] )
                              
        # Convert tons of carbon to volume under bark
        df["irw_harvest_prov_ub_con"] = ton_carbon_to_m3_ub(df, "irw_to_product_soft")
        df["irw_harvest_prov_ub_broad"] = ton_carbon_to_m3_ub(df, "irw_to_product_hard")
        df["irw_harvest_prov_ob_con"] = ton_carbon_to_m3_ob(df, "irw_to_product_soft")
        df["irw_harvest_prov_ob_broad"] = ton_carbon_to_m3_ob(df, "irw_to_product_hard")
        df["fw_harvest_prov_ub_con"] = ton_carbon_to_m3_ub(df, "fw_to_product_soft")
        df["fw_harvest_prov_ub_broad"] = ton_carbon_to_m3_ub(df, "fw_to_product_hard")
        df["fw_harvest_prov_ob_con"] = ton_carbon_to_m3_ob(df, "fw_to_product_soft")
        df["fw_harvest_prov_ob_broad"] = ton_carbon_to_m3_ob(df, "fw_to_product_hard")

        df["irw_harvest_prov_ub"] =  df["irw_harvest_prov_ub_con"] + df["irw_harvest_prov_ub_broad"]
        df["irw_harvest_prov_ob"] = df["irw_harvest_prov_ob_con"] + df["irw_harvest_prov_ob_broad"]
        df["fw_harvest_prov_ub"] = df["fw_harvest_prov_ub_con"] + df["fw_harvest_prov_ub_broad"]
        df["fw_harvest_prov_ob"] = df["fw_harvest_prov_ob_con"] + df["fw_harvest_prov_ob_broad"]
        
        # Area information
        index = ["identifier", "timestep"]
        area = self.pools[index + ["area"]]
        df = df.merge(area, on=index)
               
        return df

    def provided_fw(self):
        """explicit split on FW from IRW and FW dedicated silviculturasl practices, provided in one country"""
        df = self.fluxes
        df_total = self.provided
        
        # total harvest ub/ob on years need to calculate aggregated indicators at the end of the fuction
        df_total_harvest = df_total[["year","area","total_harvest_ub_provided", "total_harvest_ob_provided"]]
        # group on years to get the total harvest
        df_total_harvest = df_total_harvest.groupby("year")[["area","total_harvest_ub_provided", "total_harvest_ob_provided"]].sum().reset_index()

        # Sum all columns that have a flux to products
        cols_to_product = df.columns[df.columns.str.contains("to_product")]
        df["to_product"] = df[cols_to_product].sum(axis=1)
        # Keep only rows with a flux to product
        selector = df.to_product > 0
        df = df[selector]
        # Check we only have 1 year since last disturbance
        time_since_last = df["time_since_last_disturbance"].unique()
        if not time_since_last == 1:
            msg = "Time since last disturbance should be one"
            msg += f"it is {time_since_last}"
            raise ValueError(msg)
        # Add wood density information by forest type
        df = df.merge(self.parent.wood_density_bark_frac, on="forest_type")

        # Convert tons of carbon to volume under and over bark, the total harvest volume 
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
        
        # add irw fractions from input file to convert to IRW and FW
        df_irw = self.parent.irw_frac
                
        # define the scenario applicable for IRW from .yaml combo
        yaml_path = self.runner.combo.yaml_path
        with open(yaml_path, 'r') as file:
            yaml_data = file.read()
        data = yaml.safe_load(yaml_data)
        min_year = min(data['irw_frac_by_dist'].keys())
        mngm_scenario = data['irw_frac_by_dist'][min_year]
        df_irw = df_irw[df_irw['scenario'] == mngm_scenario]
        # exclude climate which is often "?"
        # dropna to get rid of events which may not apply (e.g., deforestation)
        df= df.merge(df_irw, on = ["status","forest_type", "region",
                                    "mgmt_type","mgmt_strategy",
                                    "disturbance_type", "con_broad", 
                                    "site_index", "growth_period"], how='inner')

        # here the split on 2dfs: one accounting for when there is no industrial use of roundwood, the other for the FW colateral IRW production. Because of this split, total_harvest_ub_provided is split. 
        # 'df_fw' and 'df_fw_irw'. Both contain the four source pools: merch, other, stem_snags and branch_snag
        
        columns = ['softwood_merch_irw_frac',
           'softwood_other_irw_frac',
           'softwood_stem_snag_irw_frac',
           'softwood_branch_snag_irw_frac',
           'hardwood_merch_irw_frac',
           'hardwood_other_irw_frac',
           'hardwood_stem_snag_irw_frac',
           'hardwood_branch_snag_irw_frac']
        df_fw = df[~df[columns].any(axis=1)]
        df_irw_fw = df[df[columns].any(axis=1)]

        ############# 
        # STREAM: FW colateral to IRW
        # total C on con broad
        df_irw_fw['irw_fw_to_product_soft'] = (
            df_irw_fw['softwood_merch_to_product']*(1-df_irw_fw['softwood_merch_irw_frac'])+
            df_irw_fw['softwood_other_to_product']*(1-df_irw_fw['softwood_other_irw_frac'])+
            df_irw_fw['softwood_stem_snag_to_product']*(1-df_irw_fw['softwood_stem_snag_irw_frac'])+
            df_irw_fw['softwood_branch_snag_to_product']*(1-df_irw_fw['softwood_branch_snag_irw_frac'])
                                )
        df_irw_fw['irw_fw_to_product_hard'] = (    
            df_irw_fw['hardwood_merch_to_product']*(1-df_irw_fw['hardwood_merch_irw_frac'])+
            df_irw_fw['hardwood_other_to_product']*(1-df_irw_fw['hardwood_other_irw_frac'])+
            df_irw_fw['hardwood_stem_snag_to_product']*(1-df_irw_fw['hardwood_stem_snag_irw_frac'])+
            df_irw_fw['hardwood_branch_snag_to_product']*(1-df_irw_fw['hardwood_branch_snag_irw_frac'])
                            )
        # total C of FW from IRW
        df_irw_fw['irw_fw_to_product'] = (df_irw_fw['irw_fw_to_product_soft'] + df_irw_fw['irw_fw_to_product_hard'])
        
        # C OB on components
        df_irw_fw['irw_softwood_merch_to_product'] = df_irw_fw['softwood_merch_to_product']*(1-df_irw_fw['softwood_merch_irw_frac'])
        df_irw_fw['irw_softwood_other_to_product'] = df_irw_fw['softwood_other_to_product']*(1-df_irw_fw['softwood_other_irw_frac'])
        df_irw_fw['irw_softwood_stem_snag_to_product'] = df_irw_fw['softwood_stem_snag_to_product']*(1-df_irw_fw['softwood_stem_snag_irw_frac'])
        df_irw_fw['irw_softwood_branch_snag_to_product'] = df_irw_fw['softwood_branch_snag_to_product']*(1-df_irw_fw['softwood_branch_snag_irw_frac'])
        df_irw_fw['irw_hardwood_merch_to_product'] = df_irw_fw['hardwood_merch_to_product']*(1-df_irw_fw['hardwood_merch_irw_frac'])
        df_irw_fw['irw_hardwood_other_to_product'] = df_irw_fw['hardwood_other_to_product']*(1-df_irw_fw['hardwood_other_irw_frac'])
        df_irw_fw['irw_hardwood_stem_snag_to_product'] = df_irw_fw['hardwood_stem_snag_to_product']*(1-df_irw_fw['hardwood_stem_snag_irw_frac'])
        df_irw_fw['irw_hardwood_branch_snag_to_product'] = df_irw_fw['hardwood_branch_snag_to_product']*(1-df_irw_fw['hardwood_branch_snag_irw_frac'])
        
        # in the following, 'harvest' in the string means that unit is 'volume' (m3)
        # disaggregated. Convert to volume underbark fw, 'harvest' in the string means that value is 'volume' (m3)
        df_irw_fw['irw_fw_harvest_prov_softwood_merch_ub'] = ton_carbon_to_m3_ub(df_irw_fw, 'irw_softwood_merch_to_product')
        df_irw_fw['irw_fw_harvest_prov_softwood_other_ub'] = ton_carbon_to_m3_ub(df_irw_fw, 'irw_softwood_other_to_product')
        df_irw_fw['irw_fw_harvest_prov_softwood_stem_snag_ub'] = ton_carbon_to_m3_ub(df_irw_fw, 'irw_softwood_stem_snag_to_product')
        df_irw_fw['irw_fw_harvest_prov_softwood_branch_snag_ub'] = ton_carbon_to_m3_ub(df_irw_fw, 'irw_softwood_branch_snag_to_product')
        df_irw_fw['irw_fw_harvest_prov_hardwood_merch_ub'] = ton_carbon_to_m3_ub(df_irw_fw, 'irw_hardwood_merch_to_product')
        df_irw_fw['irw_fw_harvest_prov_hardwood_other_ub'] = ton_carbon_to_m3_ub(df_irw_fw, 'irw_hardwood_other_to_product')
        df_irw_fw['irw_fw_harvest_prov_hardwood_stem_snag_ub'] = ton_carbon_to_m3_ub(df_irw_fw, 'irw_hardwood_stem_snag_to_product')
        df_irw_fw['irw_fw_harvest_prov_hardwood_branch_snag_ub'] = ton_carbon_to_m3_ub(df_irw_fw, 'irw_hardwood_branch_snag_to_product')

        # disaggregated. group on volume of biomass componsnts ub
        df_irw_fw['irw_fw_harvest_prov_merch_ub'] = df_irw_fw[['irw_fw_harvest_prov_softwood_merch_ub', 'irw_fw_harvest_prov_hardwood_merch_ub']].sum(axis=1)
        df_irw_fw['irw_fw_harvest_prov_other_ub'] = df_irw_fw[['irw_fw_harvest_prov_softwood_other_ub', 'irw_fw_harvest_prov_hardwood_other_ub']].sum(axis=1)
        df_irw_fw['irw_fw_harvest_prov_stem_snag_ub'] = df_irw_fw[['irw_fw_harvest_prov_softwood_stem_snag_ub', 'irw_fw_harvest_prov_hardwood_stem_snag_ub']].sum(axis=1)
        df_irw_fw['irw_fw_harvest_prov_branch_snag_ub'] = df_irw_fw[['irw_fw_harvest_prov_softwood_branch_snag_ub', 'irw_fw_harvest_prov_hardwood_branch_snag_ub']].sum(axis=1)

        # disaggregated. Convert to volume overbark fw
        df_irw_fw['irw_fw_harvest_prov_softwood_merch_ob'] = ton_carbon_to_m3_ob(df_irw_fw, 'irw_softwood_merch_to_product')
        df_irw_fw['irw_fw_harvest_prov_softwood_other_ob'] = ton_carbon_to_m3_ob(df_irw_fw, 'irw_softwood_other_to_product')
        df_irw_fw['irw_fw_harvest_prov_softwood_stem_snag_ob'] = ton_carbon_to_m3_ob(df_irw_fw, 'irw_softwood_stem_snag_to_product')
        df_irw_fw['irw_fw_harvest_prov_softwood_branch_snag_ob'] = ton_carbon_to_m3_ob(df_irw_fw, 'irw_softwood_branch_snag_to_product')
        df_irw_fw['irw_fw_harvest_prov_hardwood_merch_ob'] = ton_carbon_to_m3_ob(df_irw_fw, 'irw_hardwood_merch_to_product')
        df_irw_fw['irw_fw_harvest_prov_hardwood_other_ob'] = ton_carbon_to_m3_ob(df_irw_fw, 'irw_hardwood_other_to_product')
        df_irw_fw['irw_fw_harvest_prov_hardwood_stem_snag_ob'] = ton_carbon_to_m3_ob(df_irw_fw, 'irw_hardwood_stem_snag_to_product')
        df_irw_fw['irw_fw_harvest_prov_hardwood_branch_snag_ob'] = ton_carbon_to_m3_ob(df_irw_fw, 'irw_hardwood_branch_snag_to_product')

        # disaggregated. group on volume of biomass componsnts ob
        df_irw_fw['irw_fw_harvest_prov_merch_ob'] = df_irw_fw[['irw_fw_harvest_prov_softwood_merch_ob', 'irw_fw_harvest_prov_hardwood_merch_ob']].sum(axis=1)
        df_irw_fw['irw_fw_harvest_prov_other_ob'] = df_irw_fw[['irw_fw_harvest_prov_softwood_other_ob', 'irw_fw_harvest_prov_hardwood_other_ob']].sum(axis=1)
        df_irw_fw['irw_fw_harvest_prov_stem_snag_ob'] = df_irw_fw[['irw_fw_harvest_prov_softwood_stem_snag_ob', 'irw_fw_harvest_prov_hardwood_stem_snag_ob']].sum(axis=1)
        df_irw_fw['irw_fw_harvest_prov_branch_snag_ob'] = df_irw_fw[['irw_fw_harvest_prov_softwood_branch_snag_ob', 'irw_fw_harvest_prov_hardwood_branch_snag_ob']].sum(axis=1)
        
        # aggregated. total FW colateral to IRW volume under bark and overbark on con and broad
        df_irw_fw['irw_fw_harvest_prov_ub_con'] = ton_carbon_to_m3_ub(df_irw_fw, 'irw_fw_to_product_soft')
        df_irw_fw['irw_fw_harvest_prov_ub_broad'] = ton_carbon_to_m3_ub(df_irw_fw, 'irw_fw_to_product_hard')
        df_irw_fw['irw_fw_harvest_prov_ob_con'] = ton_carbon_to_m3_ob(df_irw_fw, 'irw_fw_to_product_soft')
        df_irw_fw['irw_fw_harvest_prov_ob_broad'] = ton_carbon_to_m3_ob(df_irw_fw, 'irw_fw_to_product_hard')

        # total volume under bark and overbark
        df_irw_fw['irw_fw_harvest_prov_ub'] = df_irw_fw['irw_fw_harvest_prov_ub_con'] + df_irw_fw['irw_fw_harvest_prov_ub_broad']
        df_irw_fw['irw_fw_harvest_prov_ob'] = df_irw_fw['irw_fw_harvest_prov_ob_con'] + df_irw_fw['irw_fw_harvest_prov_ob_broad']
        
        ##############
        # STREAM: FW from FW-dedictated silvicultural practices (1- irw_frac = 0 always)
        # explicit on tree biomass components
        
        # Convert to volume underbark fw
        df_fw['fw_harvest_prov_softwood_merch_ub'] = ton_carbon_to_m3_ub(df_fw, 'softwood_merch_to_product')
        df_fw['fw_harvest_prov_softwood_other_ub'] = ton_carbon_to_m3_ub(df_fw, 'softwood_other_to_product')
        df_fw['fw_harvest_prov_softwood_stem_snag_ub'] = ton_carbon_to_m3_ub(df_fw, 'softwood_stem_snag_to_product')
        df_fw['fw_harvest_prov_softwood_branch_snag_ub'] = ton_carbon_to_m3_ub(df_fw, 'softwood_branch_snag_to_product')
        df_fw['fw_harvest_prov_hardwood_merch_ub'] = ton_carbon_to_m3_ub(df_fw, 'hardwood_merch_to_product')
        df_fw['fw_harvest_prov_hardwood_other_ub'] = ton_carbon_to_m3_ub(df_fw, 'hardwood_other_to_product')
        df_fw['fw_harvest_prov_hardwood_stem_snag_ub'] = ton_carbon_to_m3_ub(df_fw, 'hardwood_stem_snag_to_product')
        df_fw['fw_harvest_prov_hardwood_branch_snag_ub'] = ton_carbon_to_m3_ub(df_fw, 'hardwood_branch_snag_to_product')
        
        # Convert to volume overbark fw
        df_fw['fw_harvest_prov_softwood_merch_ob'] = ton_carbon_to_m3_ob(df_fw, 'softwood_merch_to_product')
        df_fw['fw_harvest_prov_softwood_other_ob'] = ton_carbon_to_m3_ob(df_fw, 'softwood_other_to_product')
        df_fw['fw_harvest_prov_softwood_stem_snag_ob'] = ton_carbon_to_m3_ob(df_fw, 'softwood_stem_snag_to_product')
        df_fw['fw_harvest_prov_softwood_branch_snag_ob'] = ton_carbon_to_m3_ob(df_fw, 'softwood_branch_snag_to_product')
        df_fw['fw_harvest_prov_hardwood_merch_ob'] = ton_carbon_to_m3_ob(df_fw, 'hardwood_merch_to_product')
        df_fw['fw_harvest_prov_hardwood_other_ob'] = ton_carbon_to_m3_ob(df_fw, 'hardwood_other_to_product')
        df_fw['fw_harvest_prov_hardwood_stem_snag_ob'] = ton_carbon_to_m3_ob(df_fw, 'hardwood_stem_snag_to_product')
        df_fw['fw_harvest_prov_hardwood_branch_snag_ob'] = ton_carbon_to_m3_ob(df_fw, 'hardwood_branch_snag_to_product')

        
        # group on volume of biomass componsnts ub
        df_fw['fw_harvest_prov_merch_ub'] = df_fw['fw_harvest_prov_softwood_merch_ub'] + df_fw['fw_harvest_prov_hardwood_merch_ub']
        df_fw['fw_harvest_prov_other_ub'] = df_fw['fw_harvest_prov_softwood_other_ub'] + df_fw['fw_harvest_prov_hardwood_other_ub']
        df_fw['fw_harvest_prov_stem_snag_ub'] = df_fw['fw_harvest_prov_softwood_stem_snag_ub'] + df_fw['fw_harvest_prov_hardwood_stem_snag_ub']
        df_fw['fw_harvest_prov_branch_snag_ub'] = df_fw['fw_harvest_prov_softwood_branch_snag_ub']  + df_fw['fw_harvest_prov_hardwood_branch_snag_ub'] 

        # group on volume of biomass componsnts ob
        df_fw['fw_harvest_prov_merch_ob'] = df_fw['fw_harvest_prov_softwood_merch_ob'] + df_fw['fw_harvest_prov_hardwood_merch_ob']
        df_fw['fw_harvest_prov_other_ob'] = df_fw['fw_harvest_prov_softwood_other_ob'] + df_fw['fw_harvest_prov_hardwood_other_ob']
        df_fw['fw_harvest_prov_stem_snag_ob'] = df_fw['fw_harvest_prov_softwood_stem_snag_ob'] + df_fw['fw_harvest_prov_hardwood_stem_snag_ob']
        df_fw['fw_harvest_prov_branch_snag_ob'] = df_fw['fw_harvest_prov_softwood_branch_snag_ob']  + df_fw['fw_harvest_prov_hardwood_branch_snag_ob'] 

      
        # Convert to con broad totals ub
        df_fw['fw_harvest_prov_softwood_ub'] = (df_fw['fw_harvest_prov_softwood_merch_ub'] +
                                                        df_fw['fw_harvest_prov_softwood_other_ub'] +
                                                        df_fw['fw_harvest_prov_softwood_stem_snag_ub'] +
                                                        df_fw['fw_harvest_prov_softwood_branch_snag_ub'] )
        
        df_fw['fw_harvest_prov_hardwood_ub'] = (df_fw['fw_harvest_prov_hardwood_merch_ub'] +
                                                    df_fw['fw_harvest_prov_hardwood_other_ub'] +
                                                    df_fw['fw_harvest_prov_hardwood_stem_snag_ub'] +
                                                    df_fw['fw_harvest_prov_hardwood_branch_snag_ub'])
        
        # Convert to overbark fw
        df_fw['fw_harvest_prov_softwood_ob'] = (df_fw['fw_harvest_prov_softwood_merch_ob'] +
                                                df_fw['fw_harvest_prov_softwood_other_ob'] +
                                                df_fw['fw_harvest_prov_softwood_stem_snag_ob'] +
                                                df_fw['fw_harvest_prov_softwood_branch_snag_ob'])
        
        df_fw['fw_harvest_prov_hardwood_ob'] = (df_fw['fw_harvest_prov_hardwood_merch_ob'] +
                                                    df_fw['fw_harvest_prov_hardwood_other_ob'] +
                                                    df_fw['fw_harvest_prov_hardwood_stem_snag_ob'] +
                                                    df_fw['fw_harvest_prov_hardwood_branch_snag_ob'])
        
        df_fw['fw_harvest_prov_ub'] = df_fw['fw_harvest_prov_softwood_ub'] + df_fw['fw_harvest_prov_hardwood_ub']
        df_fw['fw_harvest_prov_ob'] = df_fw['fw_harvest_prov_softwood_ob'] + df_fw['fw_harvest_prov_hardwood_ob']

        # tick/untick as needed
        
        cols_irw_fw = ['year',
                        # total volume harvested has to be retrived from def provided(self) because of the split on fw_only, and irw_and_fw
                        # collateral FW, volume on biomass components, under and over bark
                        #'irw_fw_harvest_prov_softwood_merch_ub',
                        #'irw_fw_harvest_prov_softwood_other_ub', 
                        #'irw_fw_harvest_prov_softwood_stem_snag_ub', 
                        #'irw_fw_harvest_prov_softwood_branch_snag_ub', 
                        #'irw_fw_harvest_prov_hardwood_merch_ub', 
                        #'irw_fw_harvest_prov_hardwood_other_ub',
                        #'irw_fw_harvest_prov_hardwood_stem_snag_ub',
                        #'irw_fw_harvest_prov_hardwood_branch_snag_ub',
                        #'irw_fw_harvest_prov_softwood_merch_ob', 
                        #'irw_fw_harvest_prov_softwood_other_ob',
                        #'irw_fw_harvest_prov_softwood_stem_snag_ob', 
                        #'irw_fw_harvest_prov_softwood_branch_snag_ob',
                        #'irw_fw_harvest_prov_hardwood_merch_ob', 
                        #'irw_fw_harvest_prov_hardwood_other_ob', 
                        #'irw_fw_harvest_prov_hardwood_stem_snag_ob', 
                        #'irw_fw_harvest_prov_hardwood_branch_snag_ob', 
                        # FW, volume aggregation on softwood and hardwood, under and over bark
                        #'irw_fw_harvest_prov_ub_con', 
                        #'irw_fw_harvest_prov_ub_broad',
                        #'irw_fw_harvest_prov_ob_con',
                        #'irw_fw_harvest_prov_ob_broad',
                        'irw_fw_harvest_prov_ub',
                        'irw_fw_harvest_prov_ob',
                        'irw_fw_harvest_prov_merch_ub',
                        'irw_fw_harvest_prov_merch_ob',
                        'irw_fw_harvest_prov_other_ub',
                        'irw_fw_harvest_prov_other_ob',
                        'irw_fw_harvest_prov_stem_snag_ub',
                        'irw_fw_harvest_prov_stem_snag_ob',
                        'irw_fw_harvest_prov_branch_snag_ub',
                        'irw_fw_harvest_prov_branch_snag_ob',
                        ]

        cols_fw = ['year',
                    # FW, volume on biomass components, under and over bark
                    #'fw_harvest_prov_softwood_merch_ub', 
                    #'fw_harvest_prov_softwood_other_ub',
                    #'fw_harvest_prov_softwood_stem_snag_ub',
                    #'fw_harvest_prov_softwood_branch_snag_ub', 
                    #'fw_harvest_prov_hardwood_merch_ub', 
                    #'fw_harvest_prov_hardwood_other_ub', 
                    #'fw_harvest_prov_hardwood_stem_snag_ub', 
                    #'fw_harvest_prov_hardwood_branch_snag_ub', 
                    #'fw_harvest_prov_softwood_merch_ob', 
                    #'fw_harvest_prov_softwood_other_ob', 
                    #'fw_harvest_prov_softwood_stem_snag_ob',
                    #'fw_harvest_prov_softwood_branch_snag_ob', 
                    #'fw_harvest_prov_hardwood_merch_ob', 
                    #'fw_harvest_prov_hardwood_other_ob', 
                    #'fw_harvest_prov_hardwood_stem_snag_ob', 
                    #'fw_harvest_prov_hardwood_branch_snag_ob', 
                    # FW, volume aggregation on softwood and hardwood, under and over bark
                    #'fw_harvest_prov_softwood_ub', 
                    #'fw_harvest_prov_hardwood_ub', 
                    #'fw_harvest_prov_softwood_ob', 
                    #'fw_harvest_prov_hardwood_ob',
                    'fw_harvest_prov_ub', 
                    'fw_harvest_prov_ob',
                    'fw_harvest_prov_merch_ub',
                    'fw_harvest_prov_merch_ob',
                    'fw_harvest_prov_other_ub',
                    'fw_harvest_prov_other_ob',
                    'fw_harvest_prov_stem_snag_ub',
                    'fw_harvest_prov_stem_snag_ob',
                    'fw_harvest_prov_branch_snag_ub',
                    'fw_harvest_prov_branch_snag_ob'
                  ]
        
        # Aggregate the columns by 'year'
        df_irw_fw_year = df_irw_fw[cols_irw_fw].groupby('year').sum().reset_index()
        
        df_fw_year = df_fw[cols_fw].groupby('year').sum().reset_index()

        df_irw_fw_year['year'] = pandas.to_numeric(df_irw_fw_year['year'], errors='coerce')
        df_fw_year['year'] = pandas.to_numeric(df_fw_year['year'], errors='coerce')

        df_irw_fw_year = df_irw_fw_year.set_index('year')
        df_fw_year = df_fw_year.set_index('year')
        
        # merge the two types of wood, and also add the total harvest per year 'total_harvest_ub_provided'
        df_merged = pandas.merge(df_total_harvest, df_irw_fw_year, on='year')
        df_merged = pandas.merge(df_merged, df_fw_year, on='year')
                   
        # aggregated indicators, fractions
        # total fuelwood amount
        df_merged['total_fw_ub_provided'] = df_merged['irw_fw_harvest_prov_ub']+df_merged['fw_harvest_prov_ub']
        df_merged['total_fw_ob_provided'] = df_merged['irw_fw_harvest_prov_ob']+df_merged['fw_harvest_prov_ob']
        
        # fraction of total FW in total harvest
        df_merged['total_fw_ub_in_total_harvest_ub_frac'] = df_merged['total_fw_ub_provided']/df_merged['total_harvest_ub_provided']
        
        # FW colateral to IRW and FW in total FW harvest, i.e. sum of the frac = 1
        df_merged['irw_fw_ub_in_total_fw_ub_frac'] = df_merged['irw_fw_harvest_prov_ub']/df_merged['total_fw_ub_provided']
        df_merged['fw_ub_in_total_fw_ub_frac'] = df_merged['fw_harvest_prov_ub']/df_merged['total_fw_ub_provided']
        
        # stems in FW colateral to IRW
        df_merged['irw_fw_merch_ub_in_irw_fw_ub_provided_frac'] = df_merged['irw_fw_harvest_prov_merch_ub']/df_merged['irw_fw_harvest_prov_ub']
        
        # stems in FW dedicated silvicultural practices
        df_merged['fw_merch_ub_in_fw_ub_provided_frac'] = df_merged['fw_harvest_prov_merch_ub']/(df_merged['fw_harvest_prov_ub'])

        df_merged['country'] = self.runner.country.iso2_code
  
        return df_merged


#################################################        

    @cached_property
    def provided_shares(self):
        """Harvest provided in one country on disturbance types"""
        df = self.fluxes
        
        # Sum all columns that have a flux to products
        cols_to_product = df.columns[df.columns.str.contains("to_product")]
        df["to_product"] = df[cols_to_product].sum(axis=1)
        
        # Keep only rows with a flux to product
        selector = df.to_product > 0
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
        
        # Add a new column to the DataFrame
        df['silv_practice'] = None
                        
        # Match the values in df with the keys in dist_silv_corresp
        for i in range(len(df)):
            disturbance_type = df.loc[i, 'disturbance_type']
            if disturbance_type in dist_silv_corresp:
                df.loc[i, 'silv_practice'] = dist_silv_corresp[disturbance_type]
        
        summed_df = df.groupby(['year', 'con_broad', 'silv_practice'])['harvest_prov_ub'].sum()
        summed_df = summed_df.reset_index() 

        # Camlculate the total harvest_prov_ub for each year and con_broad
        total_harvest = summed_df.groupby(['year', 'con_broad'])['harvest_prov_ub'].transform('sum')
        # Merge the total_harvest back to the dataframe
        percentage_df = summed_df.merge(total_harvest, left_index=True, right_index=True, suffixes=('', '_total'))
        # Calculate the share of thinnings to final_cut
        percentage_df['share_to_total'] = percentage_df['harvest_prov_ub'] / percentage_df['harvest_prov_ub_total']
        return percentage_df

        # to keep this temporary omnly
        # Match the values in df with the keys in dist_silv_corresp
        #for i in range(len(df)):
        #    disturbance_type = df.loc[i, 'disturbance_type']
        #    if disturbance_type in dist_silv_corresp:
        #        df.loc[i, 'silv_practice'] = dist_silv_corresp[disturbance_type]
        #df.to_csv('overall.csv', mode='w', index=False, header=True)
        
        ##summed_df = df.groupby(['year', 'con_broad', 'silv_practice'])['harvest_prov_ub'].sum()
        ##summed_df = summed_df.reset_index() 
        
        ## Camlculate the total harvest_prov_ub for each year and con_broad
        ##total_harvest = summed_df.groupby(['year', 'con_broad'])['harvest_prov_ub'].transform('sum')
        ##total_harvest.to_csv('summed_df.csv', mode='w', index=False, header=True)
        
        ## Merge the total_harvest back to the dataframe
        ##percentage_df = summed_df.merge(total_harvest, left_index=True, right_index=True, suffixes=('', '_total'))
        ##percentage_df.to_csv('percentage_df.csv', mode='w', index=False, header=True)
        #######

        ## a) Share of harvest_prov_ub for con and broad in the sum of con and broad for each year
        #total_harvest_by_year_con_broad = df.groupby(['year', 'con_broad'])['harvest_prov_ub'].sum()
        #total_harvest_by_year = df.groupby(['year'])['harvest_prov_ub'].sum()
        #share_con_broad = total_harvest_by_year_con_broad / total_harvest_by_year
        
        ## Convert Series to DataFrame and reset index
        #share_con_broad_df = share_con_broad.reset_index(name='share_con_broad_in_total')
        
        ## b) Share of final_cut in the sum of final_cut and thinnings for each of con and broad for each year
        #final_cut_total = df[df['silv_practice'] == 'final_cut'].groupby(['year', 'con_broad'])['harvest_prov_ub'].sum()
        #total_practices = df.groupby(['year', 'con_broad'])['harvest_prov_ub'].sum()
        #share_final_cut = final_cut_total / total_practices
        
        ## Convert Series to DataFrame and reset index
        #share_final_cut_df = share_final_cut.reset_index(name='share_final_cut_in_total')
        
        #df = share_final_cut_df.merge(share_con_broad_df, on  = ['year','con_broad'])
        
        ##df.to_csv('df.csv', mode='w', index=False, header=True)  
        
        #return df
        # #################
      

    def provided_agg(self, groupby: Union[List[str], str]):
        """Aggregated version of harvest provided
        Group rows and sum all identifier rows in the same group"""
        
        # add the new columns with IRW and FW
        
        cols = (["area", "to_product", "total_harvest_ub_provided", "total_harvest_ob_provided"] +
                ["irw_to_product","fw_to_product","irw_harvest_prov_ub",
                 "irw_harvest_prov_ob", "fw_harvest_prov_ub", "fw_harvest_prov_ob", 
                 "irw_harvest_prov_ub_con","irw_harvest_prov_ub_broad", "fw_harvest_prov_ub_con", 
                 "fw_harvest_prov_ub_broad"])
        df_agg = self.provided.groupby(groupby)[cols].agg("sum").reset_index()   
        return df_agg

    def irw_provided_2020_agg(self, groupby: Union[List[str], str]):
        
        """Aggregated version of harvest provided
        Group rows and sum all identifier rows in the same group

        >>>from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.harvest.irw_provided_2020_agg(['year', 'silv_practice'])
        
        """
        
        # add the new columns with IRW and FW
        
        cols = (["area", "to_product", "total_harvest_ub_provided", "total_harvest_ob_provided"] +
                ["irw_to_product","fw_to_product","irw_harvest_prov_ub",
                 "irw_harvest_prov_ob", "fw_harvest_prov_ub", "fw_harvest_prov_ob", 
                 "irw_harvest_prov_ub_con","irw_harvest_prov_ub_broad", "fw_harvest_prov_ub_con", 
                 "fw_harvest_prov_ub_broad", "silv_practice"])
        
        df= self.provided.groupby(groupby)[cols].agg("sum").reset_index()  

        #collect 2020
        df = df[(df['year']== 2021) | (df['year']== 2022) | (df['year']== 2023) ]
        df_agg = df.groupby(['year', 'silv_practice'])["irw_harvest_prov_ub_con","irw_harvest_prov_ub_broad"].sum()
        df_agg = df_agg.reset_index()
        df_agg['country'] = self.runner.country.country_name
        return df_agg

    def expected_provided(self, groupby: Union[List[str], str]):
        """Harvest excepted provided in one country

        There is a groupby  argument because we get the harvest expected from the
        hat output of disturbances allocated by hat which are allocated at some
        level of classifier groupings (other classifiers might have question marks
        i.e. where harvest can be allocated to any value of that particular
        classifier).

        In case the groupby argument is equal to "year", we also add the harvest
        demand from the economic model.
        """
        if isinstance(groupby, str):
            groupby = [groupby]
        # TODO: current version of harvest_exp_one_country() only contains HAT
        # disturbances. This should also provide static events that generate fluxes
        # to products especially in the historical period
        df_expected = self.expected_agg(groupby=groupby)
        df_provided = self.provided_agg(groupby=groupby)
        df = df_expected.merge(df_provided, on=groupby, how="outer")

        # Join demand from the economic model, if grouping on years only
        if groupby == ["year"]:
            # print("Group by year, adding demand columns from the economic model.")
            df = df.merge(self.demand, on=groupby)

        # Sort rows in the order of the grouping variables
        df.sort_values(groupby, inplace=True)
        return df

    @cached_property
    def disturbance_types(self):
        """Disturbance types for the purposes of harvest description,
        not suitable for natural disturbances"""
        df = self.runner.country.orig_data["disturbance_types"]
        df.rename(columns={"dist_type_name": "disturbance_type"}, inplace=True)
        df["disturbance_type"] = df["disturbance_type"].astype(int)
        df["disturbance"] = "thinning"  # Default to thinning
        dist_dict = {
            "afforestation": "afforestation",
            "deforestation|cut": "clearcut",
            "salvage": "salvage",
            "fire": "natural",
        }
        for key, value in dist_dict.items():
            selector = df["dist_desc_input"].str.contains(key, case=False)
            df.loc[selector, "disturbance"] = value
        return df

    @cached_property
    def area(self):
        """Harvest area"""
        df = self.provided
        cols = self.parent.classifiers_list + ["year"]
        cols += df.columns[df.columns.str.contains("to_product")].to_list()
        cols += ["total_harvest_ub_provided", "total_harvest_ob_provided", "area", "disturbance_type"]      
        df = df[cols]
        df = df.merge(
            self.disturbance_types[["disturbance_type", "disturbance"]],
            on="disturbance_type",
        )
        return df

    def area_agg(self, groupby: Union[List[str], str]):
        """Aggregated area by classifiers or other grouping columns available"""
        if isinstance(groupby, str):
            groupby = [groupby]
        df = self.area
        cols = df.columns[df.columns.str.contains("to_product")].to_list()
        cols += ["total_harvest_ub_provided", "total_harvest_ob_provided", "area"]
        df_agg = self.area.groupby(groupby)[cols].agg("sum").reset_index()
        return df_agg


    @cached_property
    def area_disturbance_groups(self):
        """Harvest area"""
        index = ["identifier", "timestep"]
        df = self.fluxes
        area = self.pools[index + ["area"]]
        df = df.merge(area, on=index)
        df = df.query("time_since_last_disturbance == 1 and disturbance_type > 1")
        
        # Check we only have 1 year since last disturbance
        time_since_last = df["time_since_last_disturbance"].unique()
        if not (time_since_last == 1).all():
            msg = "Time since last disturbance should be one"
            msg += f"it is {time_since_last}"
            raise ValueError(msg)
        cols = self.parent.classifiers_list + ["year", "disturbance_type"]
        cols += ["area", "disturbance_type"]
        # Match the values in df with the keys in dist_silv_corresp

        for index, row in df.iterrows():
            disturbance_type = row['disturbance_type']
            if disturbance_type in dist_silv_corresp:
                df.loc[index, 'disturbance_groups'] = dist_silv_corresp[disturbance_type]
        df = (df
            .groupby(["year","disturbance_groups"])
            .agg(disturbed_area = ('area', sum) ).astype(int)
            .reset_index()
            )
        return df
