"""
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
from typing import List, Union
from eu_cbm_hat.core.continent import continent
from eu_cbm_hat.post_processor.area import apply_to_all_countries


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

    """
    df_all = apply_to_all_countries(
        sink_one_country, combo_name=combo_name, groupby=groupby
    )
    return df_all
