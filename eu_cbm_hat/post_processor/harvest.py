"""Get harvest expected and provided"""

from typing import Union, List
from functools import cached_property
import numpy as np
import pandas
from eu_cbm_hat import CARBON_FRACTION_OF_BIOMASS
from eu_cbm_hat.info.harvest import combined



def ton_carbon_to_m3_ub(df, input_var):
    """Convert tons of carbon to volume in cubic meter under bark"""
    return (df[input_var] * (1 - df["bark_frac"])) / (
        CARBON_FRACTION_OF_BIOMASS * df["wood_density"]
    )


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

        >>> harvest_prov_by_dist = area_agg.pivot(columns="disturbance", index="year", values="harvest_prov")
        >>> harvest_prov_by_dist.plot(title="LU harvest volume by disturbance type")
        >>> plt.show()

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
    def demand(self) -> pandas.DataFrame:
        """Get demand from the economic model using eu_cbm_hat/info/harvest.py
        """
        harvest_scenario_name = self.runner.combo.config["harvest"]
        irw = combined["irw"]
        irw["product"] = "irw_demand"
        fw = combined["fw"]
        fw["product"] = "fw_demand"
        df = pandas.concat([irw, fw]).reset_index(drop=True)
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
        """Harvest provided in one country
        """
        df = self.fluxes
        # Add wood density information by forest type
        df = df.merge(self.runner.silv.coefs.raw, on="forest_type")
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
        # Convert tons of carbon to volume under bark
        df["harvest_prov"] = ton_carbon_to_m3_ub(df, "to_product")
        # Area information
        index = ["identifier", "timestep"]
        area = self.pools[index + ["area"]]
        df = df.merge(area, on=index)
        # Disturbance type information
        dist = self.runner.output["parameters"][index + ["disturbance_type"]]
        df = df.merge(dist, on=index)
        return df

    def provided_agg(self, groupby: Union[List[str], str]):
        """Aggregated version of harvest provided
        Group rows and sum all identifier rows in the same group"""
        df_agg = (
            self.provided
            .groupby(groupby)
            .agg(
                disturbed_area=("area", "sum"),
                to_product=("to_product", "sum"),
                harvest_prov=("harvest_prov", "sum"),
            )
            .reset_index()
        )
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
        df["disturbance"] = "thinning"
        clearcut = df["dist_desc_input"].str.contains("deforestation|cut", case=False)
        df.loc[clearcut, "disturbance"] = "clearcut"
        salvage = df["dist_desc_input"].str.contains("salvage", case=False)
        df.loc[salvage, "disturbance"] = "salvage"
        return df

    @cached_property
    def area(self):
        """Harvest area"""
        df = self.provided
        cols = self.parent.classifiers_list + ["year"]
        cols += df.columns[df.columns.str.contains("to_product")].to_list()
        cols += ["harvest_prov", "area", "disturbance_type"]
        df = df[cols]
        df = df.merge(self.disturbance_types[["disturbance_type", "disturbance"]],
                      on="disturbance_type")
        return df

    def area_agg(self, groupby: Union[List[str], str]):
        """Aggregated area by classifiers or other grouping columns available"""
        if isinstance(groupby, str):
            groupby = [groupby]
        df = self.area
        cols = df.columns[df.columns.str.contains("to_product")].to_list()
        cols += ["harvest_prov", "area"]
        df_agg = self.area.groupby(groupby)[cols].agg("sum").reset_index()
        return df_agg


