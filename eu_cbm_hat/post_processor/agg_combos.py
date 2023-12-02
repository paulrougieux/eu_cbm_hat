"""Aggregate scenario combination output and store them in the
from eu_cbm_hat.post_processor.area import area_by_status_one_country
`eu_cbm_data/output_agg` directory.

- Save data to parquet files.


    >>> from eu_cbm_hat.post_processor.agg_combos import sink_all_countries
    >>> sink = sink_all_countries("reference", "year")


Note: this script cannot be made a method of the
combos/base_combo.py/Combination class because of circular references such as
post_processor/harvest.py importing "continent" and "combined".

        from eu_cbm_hat.info.harvest import combined
        from eu_cbm_hat.core.continent import continent

    - To avoid these imports, functions in post_processor/harvest.py could be refactored.
    - Removing the "continent" could be done by changing functions to pass runner
      objects as arguments instead of creating the runner from the continent object.
    - The call to combined could be removed by loading the harvest demand table
      directly from csv files.

"""

from typing import Union, List
import pandas
from tqdm import tqdm
from eu_cbm_hat.core.continent import continent

from eu_cbm_hat import eu_cbm_data_pathlib

# Define where to store the data
output_agg_dir = eu_cbm_data_pathlib / "output_agg"
output_agg_dir.mkdir(exist_ok=True)


def apply_to_all_countries(data_func, combo_name, **kwargs):
    """Apply a function to many countries"""
    df_all = pandas.DataFrame()
    country_codes = continent.combos[combo_name].runners.keys()
    for key in tqdm(country_codes):
        try:
            df = data_func(combo_name, key, **kwargs)
            df_all = pandas.concat([df, df_all])
        except FileNotFoundError as e_file:
            print(e_file)
        except ValueError as e_value:
            print(key, e_value)
    df_all.reset_index(inplace=True, drop=True)
    return df_all


def save_agg_combo_output(combo_name: str):
    """Aggregate scenario combination output and store them in parquet files
    inside the `eu_cbm_data/output_agg` directory.

    Example use:

        >>> from eu_cbm_hat.post_processor.agg_combos import save_agg_combo_output
        >>> save_agg_combo_output("reference")
        >>> for x in ["reference", "pikssp2", "pikfair"]:
        >>>     save_agg_combo_output(x)

    """
    combo_dir = output_agg_dir / combo_name
    combo_dir.mkdir(exist_ok=True)
    # Harvest expected provided by year
    print(f"Processing {combo_name} harvest expected provided.")
    hexprov_by_year = harvest_exp_prov_all_countries(combo_name, "year")
    hexprov_by_year.to_parquet(combo_dir / "hexprov_by_year.parquet")
    # Harvest expected provided by year, forest type and disturbance type
    hexprov_by_year_ft_dist = harvest_exp_prov_all_countries(
        combo_name, ["year", "forest_type", "disturbance_type"]
    )
    hexprov_by_year_ft_dist.to_parquet(combo_dir / "hexprov_by_year_ft_dist.parquet")
    # Sink by year
    print(f"Processing {combo_name} sink.")
    sink = sink_all_countries(combo_name, "year")
    sink.to_parquet(combo_dir / "sink_by_year.parquet")
    # Sink by year and status
    sink = sink_all_countries(combo_name, ["year", "status"])
    sink.to_parquet(combo_dir / "sink_by_year_st.parquet")
    print(f"Processing {combo_name} area.")
    # Area by year and status
    area_status = apply_to_all_countries(area_by_status_one_country, combo_name=combo_name)
    area_status.to_parquet(combo_dir / "area_by_year_status.parquet")
    print(f"Processing {combo_name} harvest area.")
    harvest_area = apply_to_all_countries(
        harvest_area_by_dist_one_country,
        combo_name=combo_name
    )
    harvest_area.to_parquet(combo_dir / "harvest_area_by_year_dist.parquet")


def read_agg_combo_output(combo_name: list, file_name: str):
    """Read the aggregated combo output for the given list of combo names and
    the given file name. Return a concatenated data frame with data from all
    combos for that file.

    Example use:

        >>> from eu_cbm_hat.post_processor.agg_combos import read_agg_combo_output
        >>> sink = read_agg_combo_output(["reference", "pikfair"], "sink_by_year.parquet")
        >>> hexprov = read_agg_combo_output(["reference", "pikfair"], "hexprov_by_year.parquet")

    """
    df_all = pandas.DataFrame()
    for this_combo_name in combo_name:
        df = pandas.read_parquet(output_agg_dir / this_combo_name / file_name)
        df_all = pandas.concat([df_all, df])
    df_all.reset_index(inplace=True, drop=True)
    return df_all

def sink_one_country(
    combo_name: str,
    iso2_code: str,
    groupby: Union[List[str], str],
):
    """Sum the pools for the given country and add information on the combo
    country code

    The `groupby` argument specify the aggregation level. In addition to
    "year", one or more classifiers can be used for example "forest_type".

    The `pools_dict` argument is a dictionary mapping an aggregated pool name
    with the corresponding pools that should be aggregated into it. If you
    don't specify it, the function will used the default pools dict. The
    groupby argument makes it possible to specify how the sink rows will be
    grouped: by year, region, status and climate.

        >>> from eu_cbm_hat.post_processor.sink_all_countries import sink_one_country
        >>> ie_sink_y = sink_one_country("reference", "IE", groupby="year")
        >>> ie_sink_ys = sink_one_country("reference", "IE", groupby=["year", "status"])
        >>> lu_sink_y = sink_one_country("reference", "LU", groupby="year")
        >>> lu_sink_ys = sink_one_country("reference", "LU", groupby=["year", "status"])
        >>> lu_sink_yrc = sink_one_country("reference", "LU", groupby=["year", "region", "climate"])
        >>> hu_sink_y = sink_one_country("reference", "HU", groupby="year")

    Specify your own `pools_dict`:

        >>> pools_dict = {
        >>>     "living_biomass": [
        >>>         "softwood_merch",
        >>>         "softwood_other",
        >>>         "softwood_foliage",
        >>>         "softwood_coarse_roots",
        >>>         "softwood_fine_roots",
        >>>         "hardwood_merch",
        >>>         "hardwood_foliage",
        >>>         "hardwood_other",
        >>>         "hardwood_coarse_roots",
        >>>         "hardwood_fine_roots",
        >>>     ],
        >>>     "soil" : [
        >>>         "below_ground_very_fast_soil",
        >>>         "below_ground_slow_soil",
        >>>     ]
        >>> }
        >>> lu_sink_by_year = sink_one_country("reference", "LU", groupby="year", pools_dict=pools_dict)
        >>> index = ["year", "forest_type"]
        >>> lu_sink_by_y_ft = sink_one_country("reference", "LU", groupby=index, pools_dict=pools_dict)

    """
    if "year" not in groupby:
        raise ValueError("Year has to be in the group by variables")
    if isinstance(groupby, str):
        groupby = [groupby]
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    # Compute the sink
    df_agg = runner.post_processor.sink.df_agg(groupby=groupby)
    # Place combo name, country code and country name as first columns
    # TODO: move this to apply_to_all_countries
    df_agg["combo_name"] = runner.combo.short_name
    df_agg["iso2_code"] = runner.country.iso2_code
    df_agg["country"] = runner.country.country_name
    cols = list(df_agg.columns)
    cols = cols[-3:] + cols[:-3]
    return df_agg[cols]

def sink_all_countries(combo_name, groupby):
    """Sum flux pools and compute the sink

    Only return data for countries in which the model run was successful in
    storing the output data. Print an error message if the file is missing, but
    do not raise an error.

        >>> from eu_cbm_hat.post_processor.sink_all_countries import sink_all_countries
        >>> sink = sink_all_countries("reference", "year")

    The purpose of this script is to compute the sink for all countries

    The following code summarises the flux_pool output for each country.

    For each year in each country:
    - aggregate the living biomass pools
    - compute the stock change
    - multiply by -44/12 to get the sink.


    Usage example (see also functions documentation bellow).

    Get the biomass sink for 2 scenarios:

        >>> from eu_cbm_hat.post_processor.sink import sink_all_countries
        >>> import pandas
        >>> # Replace these by the relevant scenario combinations
        >>> sinkfair = sink_all_countries("pikfair", "year")
        >>> sinkbau =  sink_all_countries("pikssp2", "year")
        >>> df_all = pandas.concat([sinkfair, sinkbau])
        >>> df_all.reset_index(inplace=True, drop=True)
        >>> df_all.sort_values("country", inplace=True)

    Note the area is stable through time, transition rules only make it move from
    one set of classifiers to another set of classifiers.

        from eu_cbm_hat.core.continent import continent
        runner = continent.combos["pikfair"].runners["IE"][-1]
        classifiers = runner.output.classif_df
        index = ["identifier", "timestep"]
        pools = runner.output["pools"].merge(classifiers, "left", on=index)
        area_status = (pools.groupby(["timestep", "status"])["area"]
                       .agg("sum")
                       .reset_index()
                       .pivot(columns="status", index="timestep", values="area")
                       )
        cols = df.columns
        area_status["sum"] = area_status.sum(axis=1)

    The following code chunk is a justification of why we need to look at the
    carbon content of soils in this convoluted way. Because a few afforested plots
    have AR present in the first time step, then we cannot compute a difference to
    the previous time step, and we need . In Ireland for example the following
    identifiers have "AR" present in their first time step:

        from eu_cbm_hat.core.continent import continent
        runner = continent.combos['reference'].runners['IE'][-1]
        # Load pools
        classifiers = runner.output.classif_df
        classifiers["year"] = runner.country.timestep_to_year(classifiers["timestep"])
        index = ["identifier", "timestep"]
        df = runner.output["pools"].merge(classifiers, "left", on=index)
        # Show the first time step of each identifier with AR status
        df["min_timestep"] = df.groupby("identifier")["timestep"].transform(min)
        selector = df["status"].str.contains("AR")
        selector &= df["timestep"] == df["min_timestep"]
        ar_first = df.loc[selector]
        ar_first[["identifier", "timestep", "status", "area", "below_ground_slow_soil"]]

    Aggregate by year, status, region and climate

    TODO: complete this example
    Compute the sink along the status
    Provide an example that Aggregate columns that contains "AR", such as
    ["AR_ForAWS", "AR_ForNAWS"] to a new column called "AR_historical".

        >>> for new_column, columns_to_sum in aggregation_dict.items():
        >>>     df[new_column] = df[columns_to_sum].sum(axis=1)
        >>>     df.drop(columns=columns_to_sum, inplace=True)

    """
    df_all = apply_to_all_countries(
        sink_one_country, combo_name=combo_name, groupby=groupby
    )
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
    df_agg = df.groupby(groupby)["area"].agg("sum").reset_index()
    # Place combo name, country code and country name as first columns
    df_agg["combo_name"] = combo_name
    df_agg["iso2_code"] = runner.country.iso2_code
    df_agg["country"] = runner.country.country_name
    cols = list(df_agg.columns)
    cols = cols[-3:] + cols[:-3]
    return df_agg[cols]


def area_by_status_one_country(combo_name: str, iso2_code: str):
    """Area in wide format with one column for each status.

    This table describes the movement from non forested to forested areas.
    Afforestation and deforestation influence the changes in area. Total area
    remains the same.

    Usage:

        >>> from eu_cbm_hat.post_processor.area import area_by_status_one_country
        >>> from eu_cbm_hat.post_processor.area import apply_to_all_countries
        >>> area_by_status_one_country("reference", "ZZ")
        >>> ast_ie = area_by_status_one_country("reference", "IE")
        >>> # Load data for all countries
        >>> ast = apply_to_all_countries(area_by_status_one_country, combo_name="reference")
        >>> # Place total area column last
        >>> cols = list(ast.columns)
        >>> cols.remove("total_area")
        >>> cols += ["total_area"]
        >>> ast = ast[cols]

    """
    groupby = ["year", "status", "disturbance_type"]
    df = area_one_country(combo_name=combo_name, iso2_code=iso2_code, groupby=groupby)
    # Change disturbance deforestation to status D
    selector = df["disturbance_type"] == 7
    df.loc[selector, "status"] = "D"
    # Aggregate
    index = ["year", "status"]
    df = df.groupby(index)["area"].agg("sum").reset_index()
    # Pivot to wide format
    df_wide = df.pivot(index="year", columns="status", values="area")
    # Add the total area
    df_wide["total_area"] = df_wide.sum(axis=1)
    df_wide.reset_index(inplace=True)
    # Remove the sometimes confusing axis name
    df_wide.rename_axis(columns=None, inplace=True)
    # Place combo name, country code as first columns
    df_wide["combo_name"] = combo_name
    df_wide["iso2_code"] = iso2_code
    cols = list(df_wide.columns)
    cols = cols[-2:] + cols[:-2]
    return df_wide[cols]


def harvest_area_by_dist_one_country(combo_name: str, iso2_code: str):
    """Area in wide format with one column for each status.

    Usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> from eu_cbm_hat.post_processor.agg_combos import harvest_area_by_dist_one_country
        >>> harvest_area_by_dist_one_country("reference", "LU")

    """
    groupby = ["year", "disturbance_type", "disturbance"]
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df = runner.post_processor.harvest.area_agg(groupby=groupby)
    # Place combo name, country code as first columns
    df["combo_name"] = combo_name
    df["iso2_code"] = iso2_code
    df["country"] = runner.country.country_name
    cols = list(df.columns)
    cols = cols[-3:] + cols[:-3]
    return df[cols]


def area_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """Harvest area by status in wide format for all countries in the given scenario combination.

    >>> from eu_cbm_hat.post_processor.area import area_all_countries
    >>> area_all_countries("reference", ["year", "status", "con_broad", "disturbance_type"])

    """
    df_all = apply_to_all_countries(
        area_one_country, combo_name=combo_name, groupby=groupby
    )
    return df_all

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

        >>> from eu_cbm_hat.post_processor.agg_combos import harvest_exp_prov_one_country
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
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df = runner.post_processor.harvest.expected_provided(groupby=groupby)
    # Place combo name, country code and country name as first columns
    # TODO: move this to apply_to_all_countries
    df["combo_name"] = runner.combo.short_name
    df["iso2_code"] = runner.country.iso2_code
    df["country"] = runner.country.country_name
    cols = list(df.columns)
    cols = cols[-3:] + cols[:-3]
    return df[cols]

def harvest_exp_prov_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """Information on both harvest expected and provided for all countries in
    the combo_name.

    Some countries might have NA values. If the model didn't run successfully
    for those countries i.e. the output flux table was missing.

    Example use:

        >>> from eu_cbm_hat.post_processor.agg_combos import harvest_exp_prov_all_countries
        >>> harvest_exp_prov_all_countries("reference", "year")
        >>> harvest_exp_prov_all_countries("reference", ["year", "forest_type", "disturbance_type"])

    """
    df_all = apply_to_all_countries(
        harvest_exp_prov_one_country, combo_name=combo_name, groupby=groupby
    )
    return df_all

def dw_one_country(combo_name: str, iso2_code: str, groupby: Union[List[str], str]):
    """Harvest provided in one country
    Usage:

        >>> from eu_cbm_hat.post_processor.area import area_one_country
        >>> df = area_one_country("reference", "ZZ", ["year", 'status', "disturbance_type"])

    """
    df_agg = runner.post_processor.dw_stock_ratio
    return df_agg[cols]

def dw_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """Harvest area by status in wide format for all countries in the given scenario combination.

    >>> from eu_cbm_hat.post_processor.area import area_all_countries
    >>> area_all_countries("reference", ["year", "status", "con_broad", "disturbance_type"])

    """
    df_all = apply_to_all_countries(
        dw_one_country, combo_name=combo_name, groupby=groupby
    )
    return df_all
