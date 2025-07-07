"""
Aggregate scenario combination output and store them in the `eu_cbm_data/output_agg` directory.

For example, aggregate the output of the "reference" scenario combination and
save all post processing output tables for all countries to parquet files.

    >>> from eu_cbm_hat.post_processor.agg_combos import save_agg_combo_output
    >>> save_agg_combo_output("reference")

Other examples below explain how to run only some of the post processing steps.
This was useful as we were developing these output aggregation methods, we
often wanted to update only one type of output table for all scenarios at once,
and not have to wait to update all output tables for all scenarios.

- Save a specific data frame for all countries and all scenario combinations to
  parquet files

    >>> from eu_cbm_hat.post_processor.agg_combos import apply_to_all_combos
    >>> from eu_cbm_hat.post_processor.agg_combos import apply_to_all_countries
    >>> from eu_cbm_hat.post_processor.agg_combos import get_df_one_country
    >>> from eu_cbm_hat.post_processor.agg_combos import harvest_exp_prov_one_country
    >>> from eu_cbm_hat.post_processor.agg_combos import nai_one_country
    >>> from eu_cbm_hat.post_processor.agg_combos import output_agg_dir
    >>> from eu_cbm_hat.post_processor.agg_combos import pools_length_one_country

    >>> combos = ["pikssp2_fel1", "pikssp2_owc_max", "pikssp2_owc_min",
    >>>           "pikfair_fel1", "pikfair_owc_max", "pikfair_owc_min"]
    >>> apply_to_all_combos(pools_length_one_country, combos, "pools_length.parquet")
    >>> apply_to_all_combos(nai_one_country, combos, "nai_by_year_st.parquet", groupby=["status"])
    >>> apply_to_all_combos(harvest_exp_prov_one_country, combos,
    ...                     "hexprov_by_year.parquet", groupby=["year"])
    >>> apply_to_all_combos(area_one_country, combos, "area_st_ft_agecl.parquet",
    ...                     groupby=["year", "status", "forest_type", "age_class"])
    >>> apply_to_all_combos(harvest_exp_prov_one_country, combos, "hexprov_by_year_ft_dist.parquet",
    ...                     groupby=["year", "forest_type", "con_broad", "disturbance_type"])
    >>> apply_to_all_combos(get_df_one_country, combos, "stock_agg_by_year_ldist.parquet",
    ...                     groupby=["year", "last_disturbance"], runner_method_name="post_processor.stock.df_agg")

- Open the resulting parquet files to check the content of the data frames

    >>> from eu_cbm_hat.post_processor.agg_combos import read_agg_combo_output
    >>> sink = read_agg_combo_output(["reference", "pikfair"], "sink_by_year.parquet")
    >>> nai_st = read_agg_combo_output(combos, "nai_by_year_st_test_to_delete.parquet")
    >>> pools_length = read_agg_combo_output(combos, "pools_length.parquet")

- Save a specific data frame for all countries and only one scenario
  combination to parquet files

    >>> combo_name = "reference"
    >>> combo_dir = output_agg_dir / combo_name
    >>> sink = sink_all_countries(combo_name, "year")
    >>> sink.to_parquet(combo_dir / "sink_by_year_test_to_delete.parquet")
    >>> nai_st = apply_to_all_countries(nai_one_country, combo_name=combo_name, groupby=["status"])
    >>> nai_st.to_parquet(combo_dir / "nai_by_year_st_test_to_delete.parquet")
    >>> pools_length = apply_to_all_countries(pools_length_one_country, combo_name)
    >>> pools_length.to_parquet(combo_dir / "pools_length.parquet")

- Get data frames in all countries:

    >>> from eu_cbm_hat.post_processor.agg_combos import get_df_all_countries
    >>> # Events templates raw in all countries. This includes all scenarios,
    >>> # use with caution, it requires further filtering on the scenario column
    >>> # which is different than the combo_name column. The scenario column is given
    >>> # by runner.combo  runner.combo.config["events_templates"] variable.
    >>> events_templates_all = get_df_all_countries(
    >>>     combo_name="reference",
    >>>     runner_method_name="silv.events.raw"
    >>> )
    >>> # Load wood density and bark fraction in all countries.
    >>> wood_density_bark_all = get_df_all_countries(
    >>>     combo_name="reference",
    >>>     runner_method_name="post_processor.wood_density_bark_frac"
    >>> )
    >>> # Load inventory in all countries and sum the area by management type
    >>> inventory_all = get_df_all_countries(
    >>>     combo_name="reference",
    >>>     runner_method_name="country.orig_data.__getitem__",
    >>>     item=("mgmt", "inventory")
    >>> )
    >>> inventory_all["area"] = inventory_all["area"].astype(float)
    >>> inv_agg = inventory_all.groupby(["mgmt_strategy"]).agg(area = ("area","sum"))
    >>> inv_agg = inv_agg.assign(share = lambda x: x.area / x.area.sum())

- *Implementation note*: this script cannot be made a method of the
  combos/base_combo.py/Combination class because of circular references such as
  post_processor/harvest.py importing "continent" and "combined".

    >>> from eu_cbm_hat.info.harvest import combined
    >>> from eu_cbm_hat.core.continent import continent

    - To avoid these imports, functions in post_processor/harvest.py could be refactored.
    - Removing the "continent" could be done by changing functions to pass runner
      objects as arguments instead of creating the runner from the continent object.
    - The call to combined could be removed by loading the harvest demand table
      directly from CSV files.

"""

from typing import Union, List
import pandas
import warnings
from tqdm import tqdm
from p_tqdm import p_umap
from eu_cbm_hat.core.continent import continent
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ob
from eu_cbm_hat.constants import eu_cbm_data_pathlib

# Define where to store the data
output_agg_dir = eu_cbm_data_pathlib / "output_agg"
output_agg_dir.mkdir(exist_ok=True)


def place_combo_name_and_country_first(df, runner):
    """Add combo name and country code to a data frame,
    place them as first columns"""
    df["combo_name"] = runner.combo.short_name
    df["iso2_code"] = runner.country.iso2_code
    df["country"] = runner.country.country_name
    cols = list(df.columns)
    cols = cols[-3:] + cols[:-3]
    return df[cols]


def get_df_one_country(combo_name, iso2_code, runner_method_name, **kwargs):
    """A generic function that returns the data frame output of the given
    runner method. See example use in the `get_df_all_countries()` function.
    """
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    method = runner
    for method_name in runner_method_name.split("."):
        method = getattr(method, method_name)
    # If it's a @cached_property that returns a data frame directly
    if method.__class__.__name__ ==  "DataFrame":
        df = method
    # Otherwise call the method with additional arguments
    else:
        df = method(**kwargs)
    df = place_combo_name_and_country_first(df, runner)
    return df


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


def get_df_all_countries(combo_name, runner_method_name, **kwargs):
    """Get a data frame for all countries.

    Check wood density and bark fraction in all countries:

        >>> from eu_cbm_hat.post_processor.agg_combos import get_df_all_countries
        >>> wood_density_bark_all = get_df_all_countries(
        ...     combo_name="reference",
        ...     runner_method_name="post_processor.wood_density_bark_frac"
        ... )

    Check aggregated stock in all countries:

        >>> stock_agg_all = get_df_all_countries(
        ...     combo_name="reference",
        ...     runner_method_name="post_processor.stock.df_agg",
        ...     groupby = ["year", "last_disturbance"],
        ... )

    Area in all countries grouped by status, forest type, age and disturbances:

        >>> area_sfad_all = get_df_all_countries(
        ...     combo_name="reference",
        ...     runner_method_name="post_processor.area.df_agg",
        ...     groupby = ["year", 'status', "forest_type", "age","disturbance_type"],
        ... )

    Note: data types should be harmonized to avoid this error when writing to a parquet file
    ArrowTypeError: ("Expected bytes, got a 'int' object", 'Conversion failed for column climate with type object')
    """
    df_all = apply_to_all_countries(
        data_func=get_df_one_country,
        combo_name=combo_name,
        runner_method_name=runner_method_name,
        **kwargs,
    )
    return df_all

def apply_to_all_countries_and_save(args):
    """Get data for all countries and save it to a parquet file

    This function is to be used with
        - p_umap() in apply_to_all_combos().
        - and in save_agg_combo_output
    """
    data_func, combo_name, file_path, groupby, runner_method_name = args
    # Have to check if defined or not because combo_name is passed in **kwargs
    # TODO: check if it's possible to pass groupby, runner_method_name and
    # combo_name in kwargs
    if groupby is None and runner_method_name is None:
        print(f"Processing {combo_name} {data_func}.")
        df = apply_to_all_countries(data_func=data_func, combo_name=combo_name)
    elif runner_method_name is None:
        print(f"Processing {combo_name} {data_func} grouped by {groupby}.")
        df = apply_to_all_countries(
            data_func=data_func, combo_name=combo_name, groupby=groupby
        )
    else:
        msg = f"Processing {combo_name} {data_func} with {runner_method_name} "
        msg += f"grouped by {groupby}."
        print(msg)
        df = apply_to_all_countries(
            data_func=data_func, combo_name=combo_name, groupby=groupby, runner_method_name=runner_method_name
        )
    df.to_parquet(file_path)


def apply_to_all_combos(data_func, combo_names, file_name, groupby=None, runner_method_name=None):
    """Apply a function to all scenario combinations and save to parquet files

    This saves data for all countries in all scenario combinations into the
    given parquet file name. One file for each sub-directory in the
    eu_cbm_data/output_agg directory. These files can then be read and
    concatenated later with the read_agg_combo_output() function.

    Usage with the get_df_one_country function:

        >>> from eu_cbm_hat.post_processor.agg_combos import apply_to_all_combos
        >>> from eu_cbm_hat.post_processor.agg_combos import read_agg_combo_output
        >>> from eu_cbm_hat.post_processor.agg_combos import get_df_one_country
        >>> apply_to_all_combos(get_df_one_country, ["reference", "pikfair_fel1"], "stock_agg_example_to_delete.parquet", ["year", "last_disturbance"], "post_processor.stock.df_agg")
        >>> # Read the parquet file
        >>> stock_agg = read_agg_combo_output(["reference", "pikfair_fel1"], "stock_agg_example_to_delete.parquet")

   It can also be used with a custom function:
    
        >>> from eu_cbm_hat.post_processor.agg_combos import harvest_exp_prov_one_country
        >>> apply_to_all_combos(harvest_exp_prov_one_country, ["reference", "pikfair_fel1"], "hexprov_example_to_delete.parquet",
        ...                     groupby=["year", "forest_type", "con_broad", "disturbance_type"])
        >>> hexprov = read_agg_combo_output(["reference", "pikfair_fel1"], "hexprov_example_to_delete.parquet")

    """
    items = [
        (
            data_func,
            combo_name,
            output_agg_dir / combo_name / file_name,  # file path
            groupby,
            runner_method_name,
        )
        for combo_name in combo_names
    ]
    result = p_umap(apply_to_all_countries_and_save, items, num_cpus=4)
    return result


def save_agg_combo_output(combo_name: str):
    """Aggregate scenario combination output and store them in parquet files
    inside the `eu_cbm_data/output_agg` directory.

    Example save all post-processing data frames to `eu_cbm_data/output_agg`
    for one combo:

        >>> from eu_cbm_hat.post_processor.agg_combos import save_agg_combo_output
        >>> save_agg_combo_output("reference")

    Save for many scenario combinations in a loop:

        >>> for x in ["reference", "pikssp2", "pikfair"]:
        >>>     save_agg_combo_output(x)

    """
    combo_dir = output_agg_dir / combo_name
    combo_dir.mkdir(exist_ok=True)
    parameters = [
        {
            "data_func": harvest_exp_prov_one_country,
            "groupby": ["year"],
            "file_name": "hexprov_by_year.parquet",
        },
        {
            "data_func": harvest_exp_prov_one_country,
            "groupby": ["year", "forest_type", "con_broad", "disturbance_type"],
            "file_name": "hexprov_by_year_ft_dist.parquet",
        },
        {
            "data_func": sink_one_country,
            "groupby": "year",
            "file_name": "sink_by_year.parquet",
        },
        {
            "data_func": sink_one_country,
            "groupby": ["year", "status", "region"],
            "file_name": "sink_by_year_st_rg.parquet",
        },
        {
            "data_func": area_by_status_one_country,
            "groupby": None,
            "file_name": "area_by_year_status.parquet",
        },
        {
            "data_func": harvest_area_by_dist_one_country,
            "groupby": None,
            "file_name": "harvest_area_by_year_dist.parquet",
        },
        {
            "data_func": nai_one_country,
            "groupby": ["status"],
            "file_name": "nai_by_year_st.parquet",
        },
        {
            "data_func": area_by_age_class_one_country,
            "groupby": ["year", "status", "age_class"],
            "file_name": "area_by_age_class.parquet",
        },
        {
            "data_func": share_thinn_final_cut,
            "groupby": None,
            "file_name": "share_thinn_final_cut.parquet",
        
        ### to add stocks
        
        
        
        },
        ]
    # List of parameters to be fed p_umap
    items = [
        (
            param["data_func"],
            combo_name,
            output_agg_dir / combo_name / param["file_name"],  # file path
            param["groupby"],
            param.get("runner_method_name", None)
        )
        for param in parameters
    ]
    result = p_umap(apply_to_all_countries_and_save, items, num_cpus=4)
    return result


# def save_agg_combo_output_legacy(combo_name: str):
#    """Aggregate scenario combination output and store them in parquet files
#    inside the `eu_cbm_data/output_agg` directory.
#    """
#    warnings.warn("This is the legacy version, use save_agg_combo_output instead")
#    combo_dir = output_agg_dir / combo_name
#    combo_dir.mkdir(exist_ok=True)
#    # Harvest expected provided by year
#    print(f"Processing {combo_name} harvest expected provided.")
#    hexprov_by_year = harvest_exp_prov_all_countries(combo_name, "year")
#    hexprov_by_year.to_parquet(combo_dir / "hexprov_by_year.parquet")
#    # Harvest expected provided by year, forest type and disturbance type
#    hexprov_by_year_ft_dist = harvest_exp_prov_all_countries(
#        combo_name, ["year", "forest_type", "disturbance_type"]
#    )
#    hexprov_by_year_ft_dist.to_parquet(combo_dir / "hexprov_by_year_ft_dist.parquet")
#    # Sink by year
#    print(f"Processing {combo_name} sink.")
#    sink = apply_to_all_countries(
#        sink_one_country, combo_name=combo_name, groupby="year"
#    )
#    sink.to_parquet(combo_dir / "sink_by_year.parquet")
#    # Sink by year and status
#    sink_ys = apply_to_all_countries(
#        sink_one_country, combo_name=combo_name, groupby=["year", "status"]
#    )
#    sink_ys.to_parquet(combo_dir / "sink_by_year_st.parquet")
#    print(f"Processing {combo_name} area.")
#    # Area by year and status
#    area_status = apply_to_all_countries(
#        area_by_status_one_country, combo_name=combo_name
#    )
#    area_status.to_parquet(combo_dir / "area_by_year_status.parquet")
#    print(f"Processing {combo_name} harvest area.")
#    harvest_area = apply_to_all_countries(
#        harvest_area_by_dist_one_country, combo_name=combo_name
#    )
#    harvest_area.to_parquet(combo_dir / "harvest_area_by_year_dist.parquet")
#    print(f"Processing {combo_name} Net Annual Increment.")
#    nai_sf = apply_to_all_countries(
#        nai_one_country, combo_name=combo_name, groupby=["status", "forest_type"]
#    )
#    nai_sf.to_parquet(combo_dir / "nai_by_year_st_ft.parquet")
#    nai_s = apply_to_all_countries(
#        nai_one_country, combo_name=combo_name, groupby=["status"]
#    )
#    nai_s.to_parquet(combo_dir / "nai_by_year_st.parquet")


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
    df = pandas.DataFrame()
    for this_combo_name in combo_name:
        try:
            df = pandas.read_parquet(output_agg_dir / this_combo_name / file_name)
        except FileNotFoundError as error:
            print(error)
        df_all = pandas.concat([df_all, df])
    df_all.reset_index(inplace=True, drop=True)
    return df_all

# better check sink.py
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

        >>> from eu_cbm_hat.post_processor.agg_combos import sink_one_country
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

    Sum flux pools and compute the sink

    Only return data for countries in which the model run was successful in
    storing the output data. Print an error message if the file is missing, but
    do not raise an error.

    Define a sink_all_countries function for the following examples

        >>> from eu_cbm_hat.post_processor.sink_all_countries import sink_one_country
        >>> def sink_all_countries(combo_name, groupby):
        >>>     df_all = apply_to_all_countries(
        >>>         sink_one_country, combo_name=combo_name, groupby=groupby
        >>>     )
        >>>     return df_all
        >>> sink = sink_all_countries("reference", "year")

    The purpose of this script is to compute the sink for all countries

    The following code summarises the flux_pool output for each country.

    For each year in each country:
    - aggregate the living biomass pools
    - compute the stock change
    - multiply by -44/12 to get the sink.


    Usage example (see also functions documentation bellow).

    Get the biomass sink for 2 scenarios:

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
    if "year" not in groupby:
        raise ValueError("Year has to be in the group by variables")
    if isinstance(groupby, str):
        groupby = [groupby]
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df_agg = runner.post_processor.sink.df_agg(groupby=groupby)
    df_agg = place_combo_name_and_country_first(df_agg, runner)
    return df_agg


def area_one_country(combo_name: str, iso2_code: str, groupby: Union[List[str], str]):
    """area provided in one country

    Usage:

        >>> from eu_cbm_hat.post_processor.agg_combos import area_one_country
        >>> area_one_country("reference", "ZZ", ["year", 'status', "forest_type", "age","disturbance_type"])

    """
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df_agg = runner.post_processor.area.df_agg(groupby)
    df_agg = place_combo_name_and_country_first(df_agg, runner)
    return df_agg




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

""
def area_by_age_class_one_country(combo_name: str, iso2_code: str, groupby: Union[List[str], str]):
    """Area in wide format with one column for ageclass.
        from eu_cbm_hat.post_processor.area import aarea_by_age_class_one_country
        area_by_age_class_one_country("reference", ["year", "status", "con_broad", "disturbance_type"])
    """
    groupby = ["year", "status", "age_class"]
    df = area_one_country(combo_name=combo_name, iso2_code=iso2_code, groupby=groupby)
    df=df[['combo_name', 'iso2_code', 'country', 'year', 'age_class', 'area']]
    return df

def area_by_age_class_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """NAI area by status in wide format for all countries in the given scenario combination.

    >>> from eu_cbm_hat.post_processor.area import area_by_age_class_all_countries
    >>> area_by_age_class_all_countries("reference", ["year", "status", "con_broad", "disturbance_type"])

    """
    df_all = apply_to_all_countries(
        area_by_age_class_one_country, combo_name=combo_name, groupby=groupby
    )
    return df_all

""
def share_thinn_final_cut(combo_name: str, iso2_code: str):
    """Area in wide format with one column for each status.

    Usage:

        >>> from eu_cbm_hat.post_processor.agg_combos import share_thinn_final_cut
        >>> hare_thinn_final_cut("reference", "LU")

    """
    groupby = ['year', 'con_broad', 'silv_practice']
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df_shares = runner.post_processor.harvest.provided_shares
    df_shares ["scenario"] = runner.combo.short_name
    df_shares ["region"] = runner.country.country_name
    return df_shares

""
def harvest_area_by_dist_one_country(combo_name: str, iso2_code: str):
    """Area in wide format with one column for each status.

    Usage:

        >>> from eu_cbm_hat.post_processor.agg_combos import harvest_area_by_dist_one_country
        >>> harvest_area_by_dist_one_country("reference", "LU")

    """
    groupby = ["year", "disturbance_type", "disturbance"]
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df = runner.post_processor.harvest.area_agg(groupby=groupby)
    df = place_combo_name_and_country_first(df, runner)
    return df


def nai_one_country(combo_name: str, iso2_code: str, groupby: Union[List[str], str]):
    """Net Annual Increment data by status and forest type

    Usage:

        >>> from eu_cbm_hat.post_processor.agg_combos import nai_one_country
        >>> nai_one_country("reference", "LU", ["status"])
        >>> nai_one_country("reference", "LU", ["status", "forest_type"])

    """
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df = runner.post_processor.nai.df_agg(groupby=groupby)
    df = place_combo_name_and_country_first(df, runner)
    return df


def nai_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """NAI area by status in wide format for all countries in the given scenario combination.

    >>> from eu_cbm_hat.post_processor.agg_combos import nai_all_countries
    >>> nai_all_countries("reference", ["year", "status", "con_broad", "disturbance_type"])

    """
    df_all = apply_to_all_countries(
        nai_one_country, combo_name=combo_name, groupby=groupby
    )
    return df_all

def nai_con_broad_one_country(combo_name: str, iso2_code: str, groupby: Union[List[str], str]):
    """Net Annual Increment data by status and con_broad

    Usage:

        >>> from eu_cbm_hat.post_processor.agg_combos import nai_one_country
        >>> nai_one_country("reference", "LU", ["status"])
        >>> nai_one_country("reference", "LU", ["status", "forest_type"])

    """
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df = runner.post_processor.nai.df_agg_con_broad(groupby=groupby)
    df = place_combo_name_and_country_first(df, runner)
    return df

def nai_con_broad_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """NAI area by status in wide format for all countries in the given scenario combination.

    >>> from eu_cbm_hat.post_processor.area import nai_all_countries
    >>> nai_all_countries("reference", ["year", "status", "con_broad", "disturbance_type"])

    """
    df_all = apply_to_all_countries(
        nai_con_broad_one_country, combo_name=combo_name, groupby=groupby
    )
    cols_to_keep = ['combo_name', 'country', 'year', 'status', 'con_broad',
       'area', 'nai_merch', 'gai_merch','nai_agb', 'gai_agb', 'nai_merch_ha', 'gai_merch_ha', 'nai_agb_ha','gai_agb_ha']
    df_all = df_all[cols_to_keep]
    return df_all

def weighted_nai_one_country(combo_name: str, iso2_code: str, groupby: Union[List[str], str]):
    """Net Annual Increment data weighted by status

    Usage:

        >>> from eu_cbm_hat.post_processor.agg_combos import weighted_nai_one_country
        >>> weighted_nai_one_country("reference", "LU", ["status"])
        >>> weighted_nai_one_country("reference", "LU", ["status", "forest_type"])

    """
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df = runner.post_processor.nai.df_agg(groupby=groupby)
    df = place_combo_name_and_country_first(df, runner)

    # Calculate the weighted values for nai_merch_ha and gai_merch_ha by multiplying by area
    df['weighted_merch_nai'] = df['nai_merch_ha'] * df['area']
    df['weighted_merch_gai'] = df['gai_merch_ha'] * df['area']
    df['weighted_agb_nai'] = df['nai_agb_ha'] * df['area']
    df['weighted_agb_gai'] = df['gai_agb_ha'] * df['area']

    # Group by the necessary columns and sum the weighted values and the area
    grouped = df.groupby(['country', 'year']).agg(
        total_weighted_nai_merch=('weighted_merch_nai', 'sum'),
        total_weighted_gai_merch=('weighted_merch_gai', 'sum'),
        total_weighted_nai_agb=('weighted_agb_gai', 'sum'),
        total_weighted_gai_agb=('weighted_agb_gai', 'sum'),
        total_area=('area', 'sum')
    ).reset_index()
    
    # Calculate the weighted averages
    grouped['nai_merch_ha'] = grouped['total_weighted_nai_merch'] / grouped['total_area']
    grouped['gai_merch_ha'] = grouped['total_weighted_gai_merch'] / grouped['total_area']
    grouped['nai_agb_ha'] = grouped['total_weighted_nai_agb'] / grouped['total_area']
    grouped['gai_agb_ha'] = grouped['total_weighted_gai_agb'] / grouped['total_area']

    grouped = grouped.rename(columns = {'total_area':'area', 'total_weighted_nai_merch':'nai_merch', 'total_weighted_gai_merch':'gai_merch',
                                       'total_weighted_nai_agb':'nai_agb', 'total_weighted_gai_agb':'gai_agb'})
    
    # Select the relevant columns for the final output
    final_df = grouped[['country', 'year', 'area', 'nai_merch', 'gai_merch',
                       'nai_agb', 'gai_agb', 'nai_merch_ha', 'gai_merch_ha', 
                        'nai_agb_ha', 'gai_agb_ha']]
    return final_df

def nai_all_countries_weighted_nai_eu(combo_name: str, groupby: Union[List[str], str]):
    """
    This function nai for all countries and EU, 
    calculates the sums and weighted averages for the 'eu' iso2_code.
    """
    
    df_all = apply_to_all_countries(
        weighted_nai_one_country, combo_name=combo_name, groupby=groupby
    )
    
    # Filter out the 'eu' code if it already exists
    df_all = df_all[df_all['country'] != 'EU']
    
    # Group by year and calculate the sums and weighted averages
    df_eu = df_all.groupby('year').apply(
        lambda x: pandas.Series({
            'country': 'EU',
            #'combo_name': combo_name,
            #'status': '',  # You can set this to any value you want
            'area': x['area'].sum(),
            'nai_merch': x['nai_merch'].sum(),
            'gai_merch': x['gai_merch'].sum(),
            'nai_agb': x['nai_agb'].sum(),
            'gai_agb': x['gai_agb'].sum(),
            'nai_merch_ha': (x['nai_merch_ha'] * x['area']).sum() / x['area'].sum(),
            'gai_merch_ha': (x['gai_merch_ha'] * x['area']).sum() / x['area'].sum(),
            'nai_agb_ha': (x['nai_agb_ha'] * x['area']).sum() / x['area'].sum(),
            'gai_agb_ha': (x['gai_agb_ha'] * x['area']).sum() / x['area'].sum()
        })
    ).reset_index()
    
    # Reset the index to create a new column for the year
    df_eu = df_eu.rename(columns={'index': 'year'})
    
    # Concatenate the original DataFrame with the new 'eu' DataFrame
    df_all = pandas.concat([df_all, df_eu], ignore_index=True)
    
    return df_all

def weighted_nai_con_broad_one_country(combo_name: str, iso2_code: str, groupby: Union[List[str], str]):
    """Net Annual Increment data weighted by status

    Usage:

        >>> from eu_cbm_hat.post_processor.agg_combos import nai_one_country
        >>> nai_one_country("reference", "LU", ["status"])
        >>> nai_one_country("reference", "LU", ["status", "forest_type"])

    """
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df = runner.post_processor.nai.df_agg_con_broad(groupby=groupby)
    df = place_combo_name_and_country_first(df, runner)
    # Calculate the weighted values for nai_merch_ha and gai_merch_ha by multiplying by area
    df['weighted_nai'] = df['nai_merch_ha'] * df['area']
    df['weighted_gai'] = df['gai_merch_ha'] * df['area']
    
    # Group by the necessary columns and sum the weighted values and the area
    grouped = df.groupby(['country', 'year', 'con_broad']).agg(
        total_weighted_nai=('weighted_nai', 'sum'),
        total_weighted_gai=('weighted_gai', 'sum'),
        total_area=('area', 'sum')
    ).reset_index()
    
    # Calculate the weighted averages
    grouped['avg_nai_merch_ha'] = grouped['total_weighted_nai'] / grouped['total_area']
    grouped['avg_gai_merch_ha'] = grouped['total_weighted_gai'] / grouped['total_area']
    
    # Select the relevant columns for the final output
    final_df = grouped[['country', 'year', 'con_broad', 'avg_nai_merch_ha', 'avg_gai_merch_ha']]
    return final_df


def weighted_nai_con_broad_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """NAI area by status in wide format for all countries in the given scenario combination.

    >>> from eu_cbm_hat.post_processor.area import nai_all_countries
    >>> nai_all_countries("reference", ["year", "status", "con_broad", "disturbance_type"])

    """
    df_all = apply_to_all_countries(
        weighted_nai_con_broad_one_country, combo_name=combo_name, groupby=groupby
    )
    return df_all

def area_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """area area by status in wide format for all countries in the given scenario combination.

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
    df_all = place_combo_name_and_country_first(df, runner)

    return df_all


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

def harvest_exp_prov_all_countries_eu(combo_name: str, groupby: Union[List[str], str]):
    """
    This function harvest for all countries and EU, 
    calculates the sums and weighted averages for the 'eu' iso2_code.
    """
    
    df_all = apply_to_all_countries(
       harvest_exp_prov_one_country, combo_name=combo_name, groupby=groupby
    )
    
    # Filter out the 'eu' code if it already exists
    df_all = df_all[df_all['country'] != 'EU']
    
    # Group by year and calculate the sums and weighted averages
    df_eu = df_all.groupby('year').apply(
        lambda x: pandas.Series({
            'country': 'EU',
            'rw_demand': x['rw_demand'].sum(),
            'fw_demand': x['fw_demand'].sum(),
            'irw_demand': x['irw_demand'].sum(),
            'total_harvest_ub_provided': x['total_harvest_ub_provided'].sum(),
            'total_harvest_ob_provided': x['total_harvest_ob_provided'].sum(),
        })
    ).reset_index()
   
    # Reset the index to create a new column for the year
    df_eu = df_eu.rename(columns={'index': 'year'})
    
    # Concatenate the original DataFrame with the new 'eu' DataFrame
    df_all = pandas.concat([df_all, df_eu], ignore_index=True)
    
    return df_all

def volume_stock_one_country(
    combo_name: str, iso2_code: str, groupby: Union[List[str], str]
):
    """
    Usage:

        >>> from eu_cbm_hat.post_processor.agg_combos import volume_stock_one_country
        >>> import pandas
        >>> pandas.set_option('display.precision', 0) # Display rounded numbers
        >>> volume_stock_one_country("reference", "ZZ", "year")
        >>> volume_stock_one_country("reference", "ZZ", ["year", "status"])

    """
    if isinstance(groupby, str):
        groupby = [groupby]
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df = runner.post_processor.stock.volume_standing_stocks(groupby=groupby)
    #print(df.head(3))
    df = place_combo_name_and_country_first(df, runner)
    return df

def volume_stock_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """Information on both harvest expected and provided for all countries in
    the combo_name.
    Example use:

        >>> from eu_cbm_hat.post_processor.agg_combos import harvest_exp_prov_all_countries
        >>> harvest_exp_prov_all_countries("reference", "year")
        >>> harvest_exp_prov_all_countries("reference", ["year", "status"])

    """
    df_all = apply_to_all_countries(
        volume_stock_one_country, combo_name=combo_name, groupby=groupby
    )
    return df_all

def soc_one_country(combo_name: str, iso2_code: str, groupby: Union[List[str], str]):
    """Harvest provided in one country
    Usage:

        >>> from eu_cbm_hat.post_processor.agg_combos import soc_one_country
        >>> dw_zz = soc_one_country("reference", "ZZ", ["year", 'status', "disturbance_type"])

    """
    index = ["identifier", "timestep"]
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    # Load Area
    cols_to_keep = [
        "area",
        "softwood_merch",
        "hardwood_merch",
        "medium_soil",
        "softwood_stem_snag",
        "hardwood_stem_snag",
        # new ones
        "above_ground_very_fast_soil",
        "below_ground_very_fast_soil",
        "above_ground_fast_soil",
        "below_ground_fast_soil",
        "above_ground_slow_soil",
        "below_ground_slow_soil",
        "softwood_branch_snag",
        "hardwood_branch_snag",
    ]
    df = runner.output["pools"][index + cols_to_keep]
    df["year"] = runner.country.timestep_to_year(df["timestep"])
    # Add classifiers
    df = df.merge(runner.output.classif_df, on=index)
    # Disturbance type information
    dist = runner.output["parameters"][index + ["disturbance_type"]]
    df = df.merge(dist, on=index)
    # Aggregate
    # df_agg = df.groupby(groupby)["medium_soil"].agg("sum").reset_index()

    # Aggregate separately for softwood and hardwood
    df_agg = df.groupby(groupby).agg(
        softwood_stem_snag_tc=("softwood_stem_snag", "sum"),
        softwood_merch_tc=("softwood_merch", "sum"),
        hardwood_stem_snag_tc=("hardwood_stem_snag", "sum"),
        hardwood_merch_tc=("hardwood_merch", "sum"),
        medium_tc=("medium_soil", "sum"),
        # new ones
        above_ground_very_fast_soil_tc=("above_ground_very_fast_soil", sum),
        below_ground_very_fast_soil_tc=("below_ground_very_fast_soil", sum),
        above_ground_fast_soil_tc=("above_ground_fast_soil", sum),
        below_ground_fast_soil_tc=("below_ground_fast_soil", sum),
        above_ground_slow_soil_tc=("above_ground_slow_soil", sum),
        below_ground_slow_soil_tc=("below_ground_slow_soil", sum),
        area=("area", "sum"),
    )
    df_agg.reset_index(inplace=True)
    df_agg["softwood_standing_dw_ratio"] = (
        df_agg["softwood_stem_snag_tc"] / df_agg["softwood_merch_tc"]
    )
    df_agg["hardwood_standing_dw_ratio"] = (
        df_agg["hardwood_stem_snag_tc"] / df_agg["hardwood_merch_tc"]
    )
    # agregate over con and broad
    df_agg["standing_dw_c_per_ha"] = (
        df_agg["hardwood_stem_snag_tc"] + df_agg["softwood_stem_snag_tc"]
    ) / df_agg["area"]
    df_agg["laying_dw_c_per_ha"] = df_agg["medium_tc"] / df_agg["area"]

    # Place combo name, country code and country name as first columns
    df_agg["combo_name"] = combo_name
    df_agg["iso2_code"] = runner.country.iso2_code
    df_agg["country"] = runner.country.country_name
    cols = list(df_agg.columns)
    # cols = ['softwood_stem_snag_tc', 'softwood_merch_tc',
    # 'hardwood_stem_snag_tc', 'hardwood_merch_tc', 'area', 'medium_tc',
    # 'softwood_standing_dw_ratio', 'hardwood_standing_dw_ratio',
    # 'standing_dw_c_per_ha', 'laying_dw_c_per_ha']
    cols = cols[-3:] + cols[:-3]
    return df_agg[cols]


def soc_all_countries(combo_name: str, groupby: Union[List[str], str]):
    """Harvest area by status in wide format for all countries in the given scenario combination."""
    df_all = apply_to_all_countries(
        soc_one_country, combo_name=combo_name, groupby=groupby
    )
    return df_all


def pools_length_one_country(
    combo_name: str,
    iso2_code: str,
):
    """Number of rows in the pools table

    Usage:

        >>> from eu_cbm_hat.post_processor.agg_combos import pools_length_one_country
        >>> pools_length_one_country("reference", "LU")

    """
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    pools = runner.post_processor.pools
    df = pools.value_counts(["year"], sort=False).reset_index()
    df = place_combo_name_and_country_first(df, runner)
    # Fix for older versions of pandas
    df.rename(columns={0: "count"}, inplace=True)
    return df


def fw_source_provided_one_country(
    combo_name: str, iso2_code: str, groupby: Union[List[str], str]
):
    """Harvest excepted provided in one country

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
    df = runner.post_processor.harvest.provided_fw()
    df = place_combo_name_and_country_first(df, runner)
    return df
    
def fw_source_provided_eu(combo_name: str, groupby: Union[List[str], str]):
    """
    This function nai for all countries and EU, 
    calculates the sums and weighted averages for the 'eu' iso2_code.
    """
    
    df_all = apply_to_all_countries(
        fw_source_provided_one_country, combo_name=combo_name, groupby=groupby
    )
    
    # Filter out the 'eu' code if it already exists
    df_all = df_all[df_all['country'] != 'EU']
   
    # Group by year and calculate the sums and weighted averages
    df_eu = df_all.groupby('year').apply(
        lambda x: pandas.Series({
            'country': 'EU',
            #'combo_name': combo_name,
            #'status': '',  # You can set this to any value you want
            # totals
            'total_harvest_ub_provided': x['total_harvest_ub_provided'].sum(),
            'total_harvest_ob_provided': x['total_harvest_ob_provided'].sum(),
            'irw_fw_harvest_prov_ub': x['irw_fw_harvest_prov_ub'].sum(),
            'irw_fw_harvest_prov_ob': x['irw_fw_harvest_prov_ob'].sum(),
            'irw_fw_harvest_prov_merch_ub': x['irw_fw_harvest_prov_merch_ub'].sum(),
            'irw_fw_harvest_prov_other_ub': x['irw_fw_harvest_prov_merch_ob'].sum(),
            'irw_fw_harvest_prov_stem_snag_ub': x['irw_fw_harvest_prov_stem_snag_ub'].sum(),
            'irw_fw_harvest_prov_branch_snag_ub': x['irw_fw_harvest_prov_stem_snag_ob'].sum(),
            'fw_harvest_prov_ub': x['fw_harvest_prov_ub'].sum(),
            'fw_harvest_prov_ob': x['fw_harvest_prov_ob'].sum(),
            'fw_harvest_prov_merch_ub': x['fw_harvest_prov_merch_ub'].sum(),
            'fw_harvest_prov_merch_ob': x['fw_harvest_prov_merch_ob'].sum(),
            'fw_harvest_prov_other_ub': x['fw_harvest_prov_other_ub'].sum(),
            'fw_harvest_prov_other_ob': x['fw_harvest_prov_other_ob'].sum(),
            'fw_harvest_prov_stem_snag_ub': x['fw_harvest_prov_stem_snag_ub'].sum(),
            'fw_harvest_prov_stem_snag_ob': x['fw_harvest_prov_stem_snag_ob'].sum(),
            'fw_harvest_prov_branch_snag_ub': x['fw_harvest_prov_branch_snag_ub'].sum(),
            'fw_harvest_prov_branch_snag_ob': x['fw_harvest_prov_branch_snag_ob'].sum(),
            'total_fw_ub_provided': x['total_fw_ub_provided'].sum(),
            'total_fw_ob_provided': x['total_fw_ob_provided'].sum(),
            # fractions
            'total_fw_ub_in_total_harvest_ub_frac': (x['total_fw_ub_in_total_harvest_ub_frac'] * x['area']).sum() / x['area'].sum(),
            'irw_fw_ub_in_total_fw_ub_frac': (x['irw_fw_ub_in_total_fw_ub_frac'] * x['area']).sum() / x['area'].sum(),
            'fw_ub_in_total_fw_ub_frac': (x['fw_ub_in_total_fw_ub_frac'] * x['area']).sum() / x['area'].sum(),
            'irw_fw_merch_ub_in_irw_fw_ub_provided_frac': (x['irw_fw_merch_ub_in_irw_fw_ub_provided_frac'] * x['area']).sum() / x['area'].sum(),
            'fw_merch_ub_in_fw_ub_provided_frac': (x['fw_merch_ub_in_fw_ub_provided_frac'] * x['area']).sum() / x['area'].sum()    
        })
    ).reset_index()
    
    # Reset the index to create a new column for the year
    df_eu = df_eu.rename(columns={'index': 'year'})
    
    # Concatenate the original DataFrame with the new 'eu' DataFrame
    df_all = pandas.concat([df_all, df_eu], ignore_index=True)
    
    return df_all