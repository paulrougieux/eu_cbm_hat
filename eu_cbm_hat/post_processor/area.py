"""Ouput information on changes in area"""

from typing import Union, List
import pandas
from tqdm import tqdm

from eu_cbm_hat.core.continent import continent


def apply_to_all_countries(data_func, combo_name, groupby, **kwargs):
    """Apply a function to many countries"""
    df_all = pandas.DataFrame()
    country_codes = continent.combos[combo_name].runners.keys()
    for key in tqdm(country_codes):
        try:
            df = data_func(combo_name, key, groupby=groupby, **kwargs)
            df_all = pandas.concat([df, df_all])
        except FileNotFoundError as e_file:
            print(e_file)
    df_all.reset_index(inplace=True, drop=True)
    return df_all


def area_one_country(combo_name: str, iso2_code: str, groupby: Union[List[str], str]):
    """Harvest provided in one country

    Usage:

        >>> from eu_cbm_hat.post_processor.area import area_one_country
        >>> df = area_one_country("reference", "ZZ", ["year", 'status', "disturbance_type"])

    """
    index = ["identifier", "timestep"]
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    # Load Area
    df = runner.output["pools"][index + ["area"]]
    df["year"] = runner.country.timestep_to_year(df["timestep"])
    # Add classifiers
    df = df.merge(runner.output.classif_df, on=index)
    # Disturbance type information
    dist = runner.output["parameters"][index + ["disturbance_type"]]
    df = df.merge(dist, on=index)
    # Aggregate
    df_agg = df.groupby(groupby)["area"].agg(sum).reset_index()
    # Place combo name, country code and country name as first columns
    df_agg["combo_name"] = combo_name
    df_agg["iso2_code"] = runner.country.iso2_code
    df_agg["country"] = runner.country.country_name
    cols = list(df_agg.columns)
    cols = cols[-3:] + cols[:-3]
    return df_agg[cols]


def area_by_status_one_country(
    combo_name: str, iso2_code: str, groupby: Union[List[str], str] = None
):
    """Harvest provided in one country

    Usage:

        >>> from eu_cbm_hat.post_processor.area import area_by_status_one_country
        >>> df = area_by_status_one_country("reference", "ZZ")

    """
    if isinstance(groupby, str):
        groupby = [groupby]
    groupby_default = ["year", "status", "disturbance_type"]
    if groupby is None:
        groupby = groupby_default
    else:
        groupby = groupby_default + list(set(groupby) - set(groupby_default))
    df = area_one_country(combo_name=combo_name, iso2_code=iso2_code, groupby=groupby)
    # Change disturbance deforestation to status D
    selector = df["disturbance_type"] == 7
    df.loc[selector, "status"] = "D"
    # Aggregate
    index = ["year", "status"]
    df = df.groupby(index)["area"].agg(sum).reset_index()
    # Pivot to wide format
    df_wide = df.pivot(index="year", columns="status", values="area").reset_index()
    # Remove the sometimes confusing axis name
    df_wide.rename_axis(columns=None, inplace=True)
    return df_wide


def area_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """Harvest area by status in wide format for all countries in the given scenario combination.

    >>> from eu_cbm_hat.post_processor.area import area_all_countries
    >>> area_all_countries("reference", ["year", "status", "con_broad", "disturbance_type"])

    """
    df_all = apply_to_all_countries(
        area_one_country, combo_name=combo_name, groupby=groupby
    )
    return df_all
