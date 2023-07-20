"""
The purpose of this script is to compute the sink

The following code summarises the flux_pool output for each country.

For each year in each country:
- aggregate the living biomass pools
- compute the stock change
- multiply by -44/12 to get the sink.


Usage example. Get the biomass sink for 2 scenarios:

    >>> from eu_cbm_hat.post_processor.sink import biomass_sink_all_countries
    >>> import pandas
    >>> living_biomass_pools = [
    >>>     "softwood_merch",
    >>>     "softwood_other",
    >>>     "softwood_foliage",
    >>>     "softwood_coarse_roots",
    >>>     "softwood_fine_roots",
    >>>     "hardwood_merch",
    >>>     "hardwood_foliage",
    >>>     "hardwood_other",
    >>>     "hardwood_coarse_roots",
    >>>     "hardwood_fine_roots",
    >>> ]
    >>> # Replace these by the relevant scenario combinations
    >>> sinkfair = biomass_sink_all_countries("pikfair", "year", living_biomass_pools)
    >>> sinkbau =  biomass_sink_all_countries("pikbau", "year", living_biomass_pools)
    >>> df_all = pandas.concat([sinkfair, sinkbau])
    >>> df_all.reset_index(inplace=True, drop=True)
    >>> df_all.sort_values("country", inplace=True)

"""

from typing import Union, List
import pandas
from tqdm import tqdm

from eu_cbm_hat.core.continent import continent


def biomass_sink_one_country(
    combo, iso2_code, groupby: Union[List[str], str], pools: List[str]
):
    """Sum the pools for the given country and add information on the combo
    country code

    In addition to "year", one or more classifiers can be used as join variables

        >>> from eu_cbm_hat.post_processor.sink import biomass_sink_one_country
        >>> living_biomass_pools = [
        >>>     "softwood_merch",
        >>>     "softwood_other",
        >>>     "softwood_foliage",
        >>>     "softwood_coarse_roots",
        >>>     "softwood_fine_roots",
        >>>     "hardwood_merch",
        >>>     "hardwood_foliage",
        >>>     "hardwood_other",
        >>>     "hardwood_coarse_roots",
        >>>     "hardwood_fine_roots",
        >>> ]
        >>> lu_sink_by_year = biomass_sink_one_country("reference", "LU", groupby="year", pools=living_biomass_pools)
        >>> index = ["year", "forest_type"]
        >>> lu_sink_by_y_ft = biomass_sink_one_country("reference", "LU", groupby=index, pools=living_biomass_pools)

    """
    runner = continent.combos[combo].runners[iso2_code][-1]
    classifiers = runner.output.classif_df
    classifiers["year"] = runner.country.timestep_to_year(classifiers["timestep"])
    index = ['identifier', 'timestep']
    df_wide = (
        runner.output["pools"]
        .merge(classifiers, "left", on=index)
        # Aggregate the given pools columns by the grouping variables
        .groupby(groupby)[pools]
        .sum()
    )
    # Aggregate all pool columns to one value and compute the diff
    s = df_wide.sum(axis=1).diff()
    df = s.reset_index()
    df.rename(columns={0:"stock_change"}, inplace=True)
    df["sink"] = df["stock_change"] * -44 / 12
    df["combo"] = runner.combo.short_name
    df["iso2_code"] = runner.country.iso2_code
    df["country"] = runner.country.country_name
    return df


def biomass_sink_all_countries(combo, groupby, pools):
    """Sum flux pools and compute the sink
    TODO: replace combo by combo_name

    Only return data for countries in which the model run was successful in
    storing the output data. Print an error message if the file is missing, but
    do not raise an error.

    """
    df_all = pandas.DataFrame()
    country_codes = continent.combos[combo].runners.keys()
    for key in tqdm(country_codes):
        try:
            df = biomass_sink_one_country(combo, key, groupby=groupby, pools=pools)
            df_all = pandas.concat([df, df_all])
        except FileNotFoundError as e_file:
            print(e_file)
    df_all.reset_index(inplace=True, drop=True)
    return df_all
