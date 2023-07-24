"""The purpose of this script is to compare expected and provided harvest

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
import pandas
from tqdm import tqdm

from eu_cbm_hat.info.harvest import combined
from eu_cbm_hat.core.continent import continent

CARBON_FRACTION_OF_BIOMASS = 0.49


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


def harvest_expected_one_country(
    combo_name: str, iso2_code: str, groupby: Union[List[str], str]
):
    """Harvest excepted in one country, as allocated by the Harvest Allocation Tool

    Get the harvest expected from the hat output of disturbances allocated by
    hat which are allocated at some level of classifier groupings (other
    classifiers might have question marks i.e. where harvest can be allocated
    to any value of that particular classifier).

    Usage:

        >>> from eu_cbm_hat.post_processor.harvest import harvest_expected_one_country
        >>> harvest_expected_one_country("reference", "ZZ", "year")
        >>> harvest_expected_one_country("reference", "ZZ", ["year", "forest_type"])

    """
    # Load harvest expected
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    events = runner.output["events"]
    events["harvest_exp"] = ton_carbon_to_m3_ub(events, "amount")
    # Check that we get the same value as the sum of irw_need and fw_colat
    events["fw_need"] = events["fw_need"].fillna(0)
    pandas.testing.assert_series_equal(
        events["harvest_exp"],
        events["irw_need"] + events["fw_colat"] + events["fw_need"],
        rtol=1e-4,
        check_names=False,
    )
    # Aggregate
    cols = ["irw_need", "fw_colat", "fw_need", "amount", "harvest_exp"]
    df = events.groupby(groupby)[cols].agg(sum).reset_index()
    return df


def harvest_provided_one_country(
    combo_name: str, iso2_code: str, groupby: Union[List[str], str]
):
    """Harvest provided in one country

    Usage:

        >>> from eu_cbm_hat.post_processor.harvest import harvest_provided_one_country
        >>> harvest_provided_one_country("reference", "ZZ", "year")
        >>> harvest_provided_one_country("reference", "ZZ", ["year", "forest_type"])

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
    # Group rows and sum all identifier rows in the same group
    df_agg = (
        df.groupby(groupby)
        .agg(
            disturbed_area=("area", sum),
            flux_to_product=("flux_to_product", sum),
            harvest_prov=("harvest_prov", sum),
        )
        .reset_index()
    )
    # Place combo name, country code and country name as first columns
    df_agg["combo_name"] = runner.combo.short_name
    df_agg["iso2_code"] = runner.country.iso2_code
    df_agg["country"] = runner.country.country_name
    cols = list(df_agg.columns)
    cols = cols[-3:] + cols[:-3]
    return df_agg[cols]


def harvest_provided_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """Harvest provided in all countries
    Example use:

        >>> from eu_cbm_hat.post_processor.harvest import harvest_provided_all_countries
        >>> hp = harvest_provided_all_countries(combo_name="reference", groupby="year")

    """
    df_all = pandas.DataFrame()
    country_codes = continent.combos[combo_name].runners.keys()
    for key in tqdm(country_codes):
        try:
            df = harvest_provided_one_country(
                combo_name=combo_name, iso2_code=key, groupby=groupby
            )
            df_all = pandas.concat([df, df_all])
        except FileNotFoundError as e_file:
            print(e_file)
    df_all.reset_index(inplace=True, drop=True)
    return df_all


def harvest_expected_provided_one_country(
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
    """
    # Load harvest expected
    runner = continent.combos[combo_name].runners[iso2_code][-1]

    # Join harvest provided
    df_provided = harvest_provided_one_country(
        combo_name=combo_name, iso2_code=iso2_code, groupby=groupby
    )

    # Join demand from the economic model, if grouping on years only
    if groupby == "year":
        print("group by year")

    # return df


def harvest_expected_provided_all_countries(combo_name):
    """Information on both harvest expected and provided for all
    countries in the combo_name. Some countries might have NA values.
    If the model didn't run successfully for those countries i.e.
    the output flux table was missing."""
    # Harvest scenario associated with the combo_name
    harvest_scenario = continent.combos[combo_name].config["harvest"]
