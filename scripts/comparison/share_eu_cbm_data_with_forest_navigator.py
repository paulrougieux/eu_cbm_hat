"""Share EU CBM DATA for a given list of scenarios and a selection of countries

- Selected scenarios: reference
- Selected countries: IT, IE, CZ

Create a python function that shares only the data for the given scenario yaml
file and country name. The function takes a scenario combo and shares all lines
in all input files that correspond to that scenario. For a given country. It
saves the output files with the same data structure inside a destination
directory.

    share_eu_cbm_data(scenario_combo="reference",
                      country_codes=["IT", "IE", "CZ"],
                      dest_dir="~/eu_cbm/eu_cbm_data_navigator")

We only share the common files that are in the list in this script. For the
given list of countries.

See development notes under issue: 

    no_management

"""

from pathlib import Path
import pandas as pd
import shutil

from eu_cbm_hat import eu_cbm_data_pathlib
from eu_cbm_hat.core.continent import continent
# Change these input parameters
DEST_DIR = Path("~/eu_cbm/eu_cbm_data_forest_navigator").expanduser()
COMMON_FILES_TO_SHARE = ["country_codes.csv", "reference_years.csv"]

def share_one_csv_file(orig_dir, relative_path, dest_dir, scenarios):
    """Share data for one file and filter for a list of scenario

    The orig_dir and dest_dir are country directories within
    eu_cbm_data/countries.

        (
    Examples
    --------

    cd /home/paul/rp/eu_cbm/eu_cbm_hat/scripts/comparison
    ipython

    from share_eu_cbm_data_with_forest_navigator import share_one_csv_file
    from eu_cbm_hat import eu_cbm_data_pathlib
    share_one_csv_file(orig_dir=eu_cbm_data_pathlib / "countries/IT",
                       relative_path="silv/irw_frac_by_dist.csv",
                       dest_dir="~/eu_cbm/eu_cbm_data_forest_navigator/countries/IT",
                       scenarios=["reference", "no_management"])

    """
    if isinstance(scenarios, str):
        scenarios = [scenarios]
    orig_dir = Path(orig_dir)
    dest_dir = Path(dest_dir)
    orig_csv_file = orig_dir / relative_path
    dest_csv_file = dest_dir / relative_path
    try:
        df = pd.read_csv(orig_csv_file)
    except pd.errors.EmptyDataError:
        return
    if 'scenario' in df.columns:
        df = df[df['scenario'].isin(scenarios)]
    dest_csv_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest_csv_file, index=False)


def share_country_data(combo_name, country_code):
    """Share country-specific data for a given scenario, filtering CSV files.

    This function searches for all CSV files in the country's data directory,
    filters rows where 'scenario' column matches the given scenario_combo,
    and saves the filtered data to the destination directory, preserving
    the subdirectory structure.

    Parameters
    country_code : st
        The ISO country code (e.g., 'IT') for which to share data.

    Examples
    --------
    cd /home/paul/rp/eu_cbm/eu_cbm_hat/scripts/comparison
    ipython
    from share_eu_cbm_data_with_forest_navigator import share_country_data
    share_country_data("reference", "IT")
    """
    country_orig_dir = eu_cbm_data_pathlib / "countries" / country_code
    country_dest_dir = DEST_DIR / "countries" / country_code

    # Load the scenario combo config from the yaml file into a dictionary
    combo_config = continent.combos[combo_name].config

    # Copy files
    relative_path = orig_path.relative_to(country_orig_dir)

    # Activities

    # For each combo config value create a relative path to the corresponding
    # csv file and associate a scenario name

    # For each csv file associate a scenario based on the values in the
    # scenario combination yaml file
    csv_files = [p for p in country_orig_dir.glob("**/*.csv")]

    # move the file for inventory management
    activity
    scenario = combo_config["inventory"]["mgmt"]
    orig_file = country_orig_dir / "mgmt" / "inventory.csv"



def share_common_data(country_codes, files_to_share):
    """Share common input files for the given list of countries

    Parameters
    ----------
    country_codes : list of str
        List of ISO country codes (not used in this implementation).
    files_to_share : list of str
        List of common file names to copy.

    Examples
    --------
    cd /home/paul/rp/eu_cbm/eu_cbm_hat/scripts/comparison
    ipython
    from share_eu_cbm_data_with_forest_navigator import share_common_data
    share_common_data()
    """
    common_orig_dir = eu_cbm_data_pathlib / "common"
    common_dest_dir = DEST_DIR / "common"

    for file_name in files_to_share:
        src_path = common_orig_dir / file_name
        dest_path = common_dest_dir / file_name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path)
