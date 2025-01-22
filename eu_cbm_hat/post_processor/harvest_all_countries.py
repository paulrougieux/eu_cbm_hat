"""
TODO:delete this script once the refactoring is complete.
Refactoring functions to methods of a post_processor.harvest object

The purpose of this script is to compare expected and provided harvest

- Get expected harvest from the economic model
- Get provided harvest from the fluxes to products

Compute expected provided for total roundwood demand, as the sum of IRW and FW.

Usage:

    from eu_cbm_hat.core.continent import continent
    runner = continent.combos['reference'].runners['ZZ'][-1]
    runner.output["flux"]

Conversion method refactored from Viorel's Notebook at:
https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_explore/-/blob/main/output_exploration/supply_vs_demand_total_volume.ipynb

"""


from typing import Union, List
import numpy as np
import pandas

from eu_cbm_hat.info.harvest import combined
from eu_cbm_hat.core.continent import continent
from eu_cbm_hat import CARBON_FRACTION_OF_BIOMASS


def ton_carbon_to_m3_ub(df, input_var):
    """Convert tons of carbon to volume in cubic meter under bark"""
    return (df[input_var] * (1 - df["bark_frac"])) / (
        CARBON_FRACTION_OF_BIOMASS * df["wood_density"]
    )


def harvest_demand(selected_scenario: str) -> pandas.DataFrame:
    """Get demand from the economic model using eu_cbm_hat/info/harvest.py

    Usage:

        >>> from eu_cbm_hat.post_processor.harvest import harvest_demand
        >>> harvest_demand("pikfair")

    """
    irw = combined["irw"]
    irw["product"] = "irw_demand"
    fw = combined["fw"]
    fw["product"] = "fw_demand"
    df = pandas.concat([irw, fw]).reset_index(drop=True)
    index = ["scenario", "iso2_code", "year"]
    df = df.pivot(index=index, columns="product", values="value").reset_index()
    df["rw_demand"] = df["fw_demand"] + df["irw_demand"]
    df = df.rename_axis(columns=None)
    return df.loc[df["scenario"] == selected_scenario]


def harvest_exp_one_country(
    combo_name: str, iso2_code: str, groupby: Union[List[str], str]
):
    """Harvest excepted in one country, as allocated by the Harvest Allocation Tool

    Get the harvest expected from the hat output of disturbances allocated by
    hat which are allocated at some level of classifier groupings (other
    classifiers might have question marks i.e. where harvest can be allocated
    to any value of that particular classifier).

    In case of yearly information only, this will use extra information on pre
    determined disturbances from HAT cbm/dynamic.py.

    The `groupby` argument makes it possible to group on year, group on year
    and classifiers or group on the disturbance id:

        >>> from eu_cbm_hat.post_processor.harvest import harvest_exp_one_country
        >>> harvest_exp_one_country("reference", "LU", "year")
        >>> harvest_exp_one_country("reference", "LU", ["year", "forest_type"])
        >>> harvest_exp_one_country("reference", "LU", ["year", "disturbance_type"])

    """
    # Load harvest expected
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    events = runner.output["events"]
    events["harvest_exp_hat"] = ton_carbon_to_m3_ub(events, "amount")
    # Check that we get the same value as the sum of irw_need and fw_colat
    for col in ["harvest_exp_hat", "irw_need", "fw_colat", "fw_need"]:
        events[col] = events[col].fillna(0)
    pandas.testing.assert_series_equal(
        events["harvest_exp_hat"],
        events["irw_need"] + events["fw_colat"] + events["fw_need"],
        rtol=1e-4,
        check_names=False,
    )
    # Column name consistent with runner.output["parameters"]
    events["disturbance_type"] = events["dist_type_name"]
    # Aggregate
    cols = ["irw_need", "fw_colat", "fw_need", "amount", "harvest_exp_hat"]
    df = events.groupby(groupby)[cols].agg("sum").reset_index()
    # Rename the amount expected by the Harvest Allocation Tool
    df.rename(columns={"amount": "amount_exp_hat"}, inplace=True)

    # Join demand from the economic model, if grouping on years only
    # Use extra information from the HAT cbm/dynamic.py
    if groupby == "year" or groupby == ["year"]:
        # msg = "Group by year. Get harvest demand and predetermined harvest "
        # msg += "information from the output extra table."
        # print(msg)
        extras = runner.output["extras"].rename(columns={"index": "year"})
        df = df.merge(extras, on="year", how="left")
        # Check that "harvest_exp_hat" computed from HAT disturbances is the
        # same as the sum of remaining irw and fw harvest computed at the
        # begining of cbm/dynamic.py
        # np.testing.assert_allclose(
        #     df["harvest_exp_hat"],
        #     df["remain_irw_harvest"] + df["remain_fw_harvest"],
        #     rtol=1e-4,
        # )
        df.rename(
            columns={
                "harvest_irw_vol": "harvest_demand_irw",
                "harvest_fw_vol": "harvest_demand_fw",
            },
            inplace=True,
        )
        df["harvest_demand"] = df["harvest_demand_irw"] + df["harvest_demand_fw"]

    # Place combo name, country code and country name as first columns
    df["combo_name"] = combo_name
    df["iso2_code"] = runner.country.iso2_code
    df["country"] = runner.country.country_name
    cols = list(df.columns)
    cols = cols[-3:] + cols[:-3]
    return df[cols]


def harvest_prov_one_country(
    combo_name: str, iso2_code: str, groupby: Union[List[str], str]
):
    """Harvest provided in one country

    Usage:

        >>> from eu_cbm_hat.post_processor.harvest import harvest_prov_one_country
        >>> harvest_prov_one_country("reference", "ZZ", "year")
        >>> harvest_prov_one_country("reference", "ZZ", ["year", "forest_type"])
        >>> harvest_prov_one_country("reference", "ZZ", ["year", "disturbance_type"])

    """
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df = runner.output["flux"]
    df["year"] = runner.country.timestep_to_year(df["timestep"])
    # Merge index to be used on the output tables
    index = ["identifier", "timestep"]
    # Add classifiers
    df = df.merge(runner.output.classif_df, on=index)
    # Add wood density information by forest type
    df = df.merge(runner.silv.coefs.raw, on="forest_type")
        
    #print(df)
    # Sum all columns that have a flux to products
    cols_to_product = df.columns[df.columns.str.contains("to_product")]
    df["flux_to_product"] = df[cols_to_product].sum(axis=1)
    # Keep only rows with a flux to product
    selector = df.flux_to_product > 0
    df = df[selector]
    # Convert tons of carbon to volume under bark
    df["harvest_prov"] = ton_carbon_to_m3_ub(df, "flux_to_product")
    # Area information
    area = runner.output["pools"][index + ["area"]]
    df = df.merge(area, on=index)
    # Disturbance type information
    dist = runner.output["parameters"][index + ["disturbance_type"]]
    df = df.merge(dist, on=index)
    # Group rows and sum all identifier rows in the same group
    df_agg = (
        df.groupby(groupby)
        .agg(
            disturbed_area=("area", "sum"),
            flux_to_product=("flux_to_product", "sum"),
            harvest_prov=("harvest_prov", "sum"),
        )
        .reset_index()
    )

    # Place combo name, country code and country name as first columns
    df_agg["combo_name"] = combo_name
    df_agg["iso2_code"] = runner.country.iso2_code
    df_agg["country"] = runner.country.country_name
    cols = list(df_agg.columns)
    cols = cols[-3:] + cols[:-3]
    return df_agg[cols]


def harvest_exp_prov_one_country(
    combo_name: str, iso2_code: str, groupby: Union[List[str], str]
):
    """Harvest excepted provided in one country

    There is a groupby  argument because we get the harvest expected from the
    hat output of disturbances allocated by hat which are allocated at some
    level of classifier groupings (other classifiers might have question marks
    i.e. where harvest can be allocated to any value of that particular
    classifier).

    In case the groupby argument is equal to "year", we also add the harvest
    demand from the economic model.

    Usage:

        >>> from eu_cbm_hat.post_processor.harvest import harvest_exp_prov_one_country
        >>> import pandas
        >>> pandas.set_option('display.precision', 0) # Display rounded numbers
        >>> harvest_exp_prov_one_country("reference", "ZZ", "year")
        >>> harvest_exp_prov_one_country("reference", "ZZ", ["year", "forest_type"])
        >>> harvest_exp_prov_one_country("reference", "ZZ", ["year", "disturbance_type"])

    """
    if isinstance(groupby, str):
        groupby = [groupby]

    # TODO: current version of harvest_exp_one_country() only contains HAT
    # disturbances. This should also provide static events that generate fluxes
    # to products especially in the historical period
    df_expected = harvest_exp_one_country(
        combo_name=combo_name, iso2_code=iso2_code, groupby=groupby
    )
    df_provided = harvest_prov_one_country(
        combo_name=combo_name, iso2_code=iso2_code, groupby=groupby
    )
    #print(df_provided)
    index = ["combo_name", "iso2_code", "country"]
    index += groupby
    df = df_expected.merge(df_provided, on=index, how="outer")

    # Join demand from the economic model, if grouping on years only
    if groupby == "year":
        # print("group by year")
        harvest_scenario_name = continent.combos[combo_name].config["harvest"]
        df_demand = harvest_demand(harvest_scenario_name)
        df_demand = df_demand.loc[df_demand["iso2_code"] == iso2_code]
        index = ["iso2_code", "year"]
        df = df.merge(df_demand, on=index)

    # Sort rows in the order of the grouping variables
    df.sort_values(groupby, inplace=True)

    return df


