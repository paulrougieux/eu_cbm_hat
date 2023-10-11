"""Aggregate scenario combination output and store them in the
`eu_cbm_data/output_agg` directory.

- Save data to parquet files.


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
import pandas

from eu_cbm_hat import eu_cbm_data_pathlib
from eu_cbm_hat.post_processor.area import apply_to_all_countries
from eu_cbm_hat.post_processor.area import area_by_status_one_country
from eu_cbm_hat.post_processor.harvest import harvest_exp_prov_all_countries
from eu_cbm_hat.post_processor.sink import sink_all_countries

# Define where to store the data
output_agg_dir = eu_cbm_data_pathlib / "output_agg"
output_agg_dir.mkdir(exist_ok=True)


def save_agg_combo_output(combo_name:str):
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
    # Area by year and status
    area_status = apply_to_all_countries(area_by_status_one_country, combo_name=combo_name)
    area_status.to_parquet(combo_dir / "area_by_year_status.parquet")


def read_agg_combo_output(combo_name:list, file_name:str):
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
