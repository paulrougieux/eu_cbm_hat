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

from typing import Dict, List, Union
import numpy as np
import pandas

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

FLUXES_DICT = {
    "transfer_to_products": [
        "softwood_merch_to_product",
        "softwood_other_to_product",
        "softwood_stem_snag_to_product",
        "softwood_branch_snag_to_product",
        "hardwood_merch_to_product",
        "hardwood_other_to_product",
        "hardwood_stem_snag_to_product",
        "hardwood_branch_snag_to_product",
    ],
    "emissions_from_dom": ["decay_domco2_emission"],
    "direct_emissions_to_air": [
        "disturbance_bio_co2_emission",
        "disturbance_bio_ch4_emission",
        "disturbance_bio_co_emission",
    ],
}


def get_nf_soil_stock(df):
    """Get the slow soil pool content per hectare of non forested stands.

    Keep only stands that have never been disturbed in the simulation
    (time_since_land_class_change == -1), exclude NF stands that are the result
    of deforestation during the simulation period.
    """
    selector = df["status"].str.contains("NF")
    selector &= df["time_since_land_class_change"] == -1
    nf_soil = df.loc[selector].copy()
    nf_soil["nf_slow_soil_per_ha"] = nf_soil["below_ground_slow_soil"] / nf_soil["area"]
    # Group by region and climate and calculate the standard deviation
    groupby_soil = ["region", "climate"]
    nf_soil["std_dev"] = nf_soil.groupby(groupby_soil)["nf_slow_soil_per_ha"].transform(
        "std"
    )
    # Check that nf_slow_soil_per_ha always have the same value across grouping
    # variables
    selector = nf_soil["std_dev"] > 1e-2
    if any(selector):
        msg = "The NF non forested soil pool content per hectare"
        msg += " is not homogeneous for some region and climate groups."
        cols_to_show = ["year", "status", "region", "climate"]
        cols_to_show += [
            "time_since_land_class_change",
            "nf_slow_soil_per_ha",
            "std_dev",
        ]
        msg += f"{nf_soil[cols_to_show]}"
        raise ValueError(msg)
    # Aggregate smaller data frame with columns necessary for the join
    nf_soil_agg = nf_soil.groupby(groupby_soil)["nf_slow_soil_per_ha"].agg("mean")
    nf_soil_agg = nf_soil_agg.reset_index()
    return nf_soil_agg


def generate_all_combinations_and_fill_na(df, groupby):
    """Generate a DataFrame with all combinations of year, status, region, and
    climate.
    """
    groupby_area_diff = groupby.copy()
    # Prepare all combinations of groupby variables except year
    groupby_area_diff.remove("year")
    all_groups = df[groupby_area_diff].drop_duplicates()
    years = list(df["year"].unique())
    combi_dict = {
        "year": [y for y in years for _ in range(len(all_groups))],
    }
    for var in groupby_area_diff:
        combi_dict[var] = all_groups[var].tolist() * len(years)
    all_combinations = pandas.DataFrame(combi_dict)
    # Do a full join to make NA values apparent in order to compute the diff in
    # area or stock later
    df = df.merge(all_combinations, how="outer", on=["year"] + groupby_area_diff)
    df.fillna(0, inplace=True)
    df.sort_values(groupby_area_diff + ["year"], inplace=True)
    # Compute the area diff and check the diff sums to zero
    df["area_diff"] = df.groupby(groupby_area_diff)["area"].transform(
        lambda x: x.diff()
    )
    diff_sum = abs(df.groupby("year")["area_diff"].sum())
    assert all(diff_sum < 100)
    return df


def compute_sink(
    df: pandas.DataFrame,
    groupby: Union[List[str], str],
    pools_dict: Dict[str, List[str]] = None,
):
    """Compute the stock change and the sink

    Aggregate by the classifier for which it is possible to compute a
    difference in pools. During land use transition implementing afforestation
    and deforestation, some classifier sets may change, while other classifiers
    such as region and climate remain constant. It is only possible to compute
    the stock change along classifiers that remain constant.

    Normalise the sink by the area. For example in case of afforestation the
    stock change should take into account the change of area from t-1 to t.
    Steps to correct for the area change:

        - Group by ["year", "region", "climate", "status",
                    "land_class_change_in_current_year"] and sum pools
        - Aggregate all pool columns to one pool value for each key in the
          pools_dict dictionary
        - Compute the stock change per hectare
            S{t}/A{t} - S{t-1}/A{t-1}
        - Deduce NF soil pool when there is afforestation in the first year
        - Compute the CO2 eq. sink per hectare
        - Multiply the sink by the area at time t
        - Remove non forested land
        - Group by final grouping variables given in the groupby argument.

    See usage example in the function sink_one_country.

    """
    df = df.copy()
    # keep only time_since_land_class_change==1 to treat afforestation soil stock change from NF
    df["land_class_change_in_current_year"] = df["time_since_land_class_change"] == 1
    groupby_sink = [
        "year",
        "region",
        "climate",
        "status",
        "land_class_change_in_current_year",
    ]
    if not set(groupby).issubset(groupby_sink):
        msg = f"Can only group by {groupby_sink}. "
        msg += f"{set(groupby) - set(groupby_sink)}"
        msg += " not allowed as a groupby value."
        raise ValueError(msg)

    pools_list = list({item for sublist in pools_dict.values() for item in sublist})

    # Aggregate by the classifier for which it is possible to compute a
    # difference in pools.
    df_agg = df.groupby(groupby_sink)[pools_list + ["area"]].sum().reset_index()

    # Add the soil stock in NF stands (that have not been deforested in the simulation)
    nf_soil_agg = get_nf_soil_stock(df)
    df_agg = df_agg.merge(nf_soil_agg, on=["region", "climate"], how="left")
    # NF soil is only needed for the AR pools
    selector = df_agg["status"].str.contains("AR")

    df_agg = generate_all_combinations_and_fill_na(df_agg, groupby=groupby_sink)

    # Remove year from the grouping variables to compute the diff over years
    groupby_sink.remove("year")

    for key in pools_dict:
        # Aggregate all pool columns to one pool value for this key
        df_agg[key + "_pool"] = df_agg[pools_dict[key]].sum(axis=1)

        # Normalize stock per hectare
        df_agg[key + "_pool_per_ha"] = df_agg[key + "_pool"] / df_agg["area"]

        # Compute the stock change per hectare
        df_agg[key + "_stk_ch"] = df_agg.groupby(groupby_sink)[
            key + "_pool_per_ha"
        ].transform(lambda x: x.diff())

        # Deduce NF soil pool when there is afforestation in the first year
        if "soil" in key:
            selector = df_agg["status"].str.contains("AR")
            selector &= df_agg["land_class_change_in_current_year"]
            df_agg.loc[selector, key + "_stk_ch"] = (
                df_agg.loc[selector, key + "_pool_per_ha"]
                - df_agg.loc[selector, "nf_slow_soil_per_ha"]
            )

        # Compute the CO2 eq. sink per hectare
        df_agg[key + "_sink_per_ha"] = df_agg[key + "_stk_ch"] * -44 / 12

        # Multiply the sink by the area
        df_agg[key + "_sink"] = df_agg[key + "_sink_per_ha"] * df_agg["area"]

    # Remove non forested land
    selector = df_agg["status"].str.contains("NF")
    df_agg = df_agg.loc[~selector]

    # Aggregate the given pools columns by the final grouping variables Keep
    # the area information
    cols = df_agg.columns
    cols = cols[cols.str.contains("sink$")].to_list()
    df_agg_final = df_agg.groupby(groupby)[cols].agg("sum").reset_index()
    return df_agg_final


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
        >>> ie_sink_y = sink_one_country("reference", "IE", groupby="year")
        >>> ie_sink_ys = sink_one_country("reference", "IE", groupby=["year", "status"])
        >>> lu_sink_y = sink_one_country("reference", "LU", groupby="year")
        >>> lu_sink_yr = sink_one_country("reference", "LU", groupby=["year", "region"])
        >>> lu_sink_yrc = sink_one_country("reference", "LU", groupby=["year", "region", "climate"])

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
    if pools_dict is None:
        pools_dict = POOLS_DICT
    if "year" not in groupby:
        raise ValueError("Year has to be in the group by variables")
    if groupby == "year":
        groupby = ["year"]
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    classifiers = runner.output.classif_df
    classifiers["year"] = runner.country.timestep_to_year(classifiers["timestep"])
    index = ["identifier", "timestep"]

    pools_list = list({item for sublist in pools_dict.values() for item in sublist})

    # Data frame of pools content at the maximum disaggregated level by
    # identifier and timestep that will be sent to the other functions
    df = (
        runner.output["pools"].merge(classifiers, "left", on=index)
        # Add 'time_since_land_class_change' and 'time_since_last_disturbance'
        .merge(runner.output["state"], "left", on=index)
    )
    df_agg = compute_sink(df, groupby, pools_dict)
    # Place combo name, country code and country name as first columns
    df_agg["combo_name"] = runner.combo.short_name
    df_agg["iso2_code"] = runner.country.iso2_code
    df_agg["country"] = runner.country.country_name
    cols = list(df_agg.columns)
    cols = cols[-3:] + cols[:-3]
    # Remove the pools columns
    cols = [col for col in cols if col not in pools_list]
    return df_agg[cols]


def emissions_from_deforestation(
    combo_name: str,
    iso2_code: str,
    groupby: Union[List[str], str],
    fluxes_dict: Dict[str, List[str]] = None,
):
    """Emissions from deforested areas moving from forested to NF

    Deforestation emissions are only reported for the year when event happens.
    Indeed, a small amount of legacy emissions occur, as reflected by
    "decay_domco2_emission"evolution after deforestation for any identifier We
    considered it as nonrelevant, anyway atributable to post-deforestation land
    use. Deforestation emissions can be identified by dist_type = 7, OR,
    "status = "NF" and "time_since_land_class_change > 0" land transfers from
    occur ForAWS/NAWS, or even AR, to NF. join this df to sink df_all.

    Example use:

        >>> from eu_cbm_hat.post_processor.sink import emissions_from_deforestation
        >>> from eu_cbm_hat.post_processor.area import apply_to_all_countries
        >>> lu_def_em_y = emissions_from_deforestation("reference", "LU", groupby="year")
        >>> lu_def_em_yr = emissions_from_deforestation("reference", "LU", groupby=["year", "region"])
        >>> def_em_y = apply_to_all_countries(emissions_from_deforestation, combo_name="reference", groupby="year")

    """
    if fluxes_dict is None:
        fluxes_dict = FLUXES_DICT
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    classifiers = runner.output.classif_df
    classifiers["year"] = runner.country.timestep_to_year(classifiers["timestep"])
    index = ["identifier", "timestep"]

    fluxes_list = list({item for sublist in fluxes_dict.values() for item in sublist})

    # Data frame of pools content at the maximum disaggregated level by
    # identifier and timestep that will be sent to the other functions
    df = (
        runner.output["flux"].merge(classifiers, "left", on=index)
        # Add 'time_since_land_class_change'
        .merge(runner.output["state"], "left", on=index)
    )

    # Keep only deforestation events
    selector = df["time_since_land_class_change"] > 0
    df = df.loc[selector]

    for key in fluxes_dict:
        # Aggregate all pool columns to one pool value for this key
        df[key] = df[fluxes_dict[key]].sum(axis=1)

    cols = [key for key in fluxes_dict.keys()]

    # Aggreate
    df_agg = df.groupby(groupby)[cols].agg("sum").reset_index()

    return df_agg


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
