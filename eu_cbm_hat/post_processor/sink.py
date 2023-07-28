"""
The purpose of this script is to compute the sink

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
    >>> sinkbau =  sink_all_countries("pikbau", "year")
    >>> df_all = pandas.concat([sinkfair, sinkbau])
    >>> df_all.reset_index(inplace=True, drop=True)
    >>> df_all.sort_values("country", inplace=True)

"""

from typing import Dict, List, Union
import pandas
from tqdm import tqdm

from eu_cbm_hat.core.continent import continent
from eu_cbm_hat.post_processor.area import apply_to_all_countries

POOLS_DICT = {
    "living_biomass": [
        "softwood_merch",
        "softwood_other",
        "softwood_foliage",
        "softwood_coarse_roots",
        "softwood_fine_roots",
        "hardwood_merch",
        "hardwood_foliage",
        "hardwood_other",
        "hardwood_coarse_roots",
        "hardwood_fine_roots",
    ],
    "dom": [
        "above_ground_very_fast_soil",
        "above_ground_fast_soil",
        "above_ground_slow_soil",
        "below_ground_fast_soil",
        "medium_soil",
        "softwood_stem_snag",
        "hardwood_branch_snag",
        "softwood_branch_snag",
        "hardwood_stem_snag",
    ],
    "soil": [
        "below_ground_very_fast_soil",
        "below_ground_slow_soil",
    ],
}


def sink_one_country(
    combo_name: str,
    iso2_code: str,
    groupby: Union[List[str], str],
    pools_dict: Dict[str, List[str]] = None,
):
    """Sum the pools for the given country and add information on the combo
    country code

    The `groupby` argument specify the aggregation level. In addition to
    "year", one or more classifiers can be used for example "forest_type".

    The `pools_dict` argument is a dictionary mapping an aggregated pool name
    with the corresponding pools that should be aggregated into it. If you
    don't specify it, the function will used the default pools dict.

        >>> from eu_cbm_hat.post_processor.sink import sink_one_country
        >>> lu_sink_by_y_ft = sink_one_country("reference", "LU", groupby=["year", "forest_type"])
        >>> lu_sink_by_year = sink_one_country("reference", "LU", groupby="year")

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
    # TODO: normalise the sink by the area
    # In case of afforestation the stock change should take into account the change
    # of area. i.e. the stock change and sink need to be normalized by the area
    # - Compute the stock change per hectare for
    # - then remultiply by the area
    if pools_dict == None:
        pools_dict = POOLS_DICT
    if "year" not in groupby:
        raise ValueError("Year has to be in the group by variables")
    if groupby == "year":
        groupby = ["year"]
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    classifiers = runner.output.classif_df
    classifiers["year"] = runner.country.timestep_to_year(classifiers["timestep"])
    index = ["identifier", "timestep"]
    pools_list = list(
        set([item for sublist in pools_dict.values() for item in sublist])
    )
    df_wide = (
        runner.output["pools"]
        .merge(classifiers, "left", on=index)
        # Aggregate the given pools columns by the grouping variables
        .groupby(groupby)[pools_list]
        .sum()
        .reset_index()
    )
    # Sort by all variable first, then year last to compute the difference of pools
    groupby.remove("year")
    df_wide.sort_values(groupby + ["year"], inplace=True)
    # for key, value in
    for key in pools_dict:
        # Aggregate all pool columns to one pool value for this key
        df_wide[key + "_pool"] = df_wide[pools_dict[key]].sum(axis=1)
        # Compute the stock change
        if groupby:
            # If there are groupby variables (other than year), group before
            # computing the diff
            df_wide[key + "_stock_change"] = df_wide.groupby(groupby)[
                key + "_pool"
            ].transform(lambda x: x.diff())
        else:
            # If there is only year as a groupby variable compute the diff directly
            df_wide[key + "_stock_change"] = df_wide[key + "_pool"].diff()
        # Compute the sink
        df_wide[key + "_sink"] = df_wide[key + "_stock_change"] * -44 / 12
    # Place combo name, country code and country name as first columns
    df_wide["combo_name"] = runner.combo.short_name
    df_wide["iso2_code"] = runner.country.iso2_code
    df_wide["country"] = runner.country.country_name
    cols = list(df_wide.columns)
    cols = cols[-3:] + cols[:-3]
    # Remove the pools columns
    cols = [col for col in cols if col not in pools_list]
    return df_wide[cols]


def sink_all_countries(combo_name, groupby, pools_dict=None):
    """Sum flux pools and compute the sink

    Only return data for countries in which the model run was successful in
    storing the output data. Print an error message if the file is missing, but
    do not raise an error.

        >>> from eu_cbm_hat.post_processor.sink import sink_all_countries
        >>> sink = sink_all_countries("reference", "year")

    """
    df_all = apply_to_all_countries(
        sink_one_country, combo_name=combo_name, groupby=groupby, pools_dict=pools_dict
    )
    return df_all
