"""Share EU CBM DATA for one scenario only for a selection of countries

- Selected scenario: reference
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

# Additional HWP and climate modifier functionality

Not implemented now.

Additional input data for Harvested Wood Products computation and climate
modification will be shared later. These scenario input files are currently
still under development and testing:
- HWP
- Climate adjustment
"""

from pathlib import Path
import pandas as pd
from eu_cbm_hat import eu_cbm_data_pathlib

# Change these input parameters
DEST_DIR = Path("~/eu_cbm/eu_cbm_data_forest_navigator").expanduser()
COMMON_FILES_TO_SHARE = ["country_codes.csv", "reference_years.csv"]


def share_country_data(scenario_combo, country_code):
    """Share country-specific data for a given scenario, filtering CSV files.

    This function searches for all CSV files in the country's data directory,
    filters rows where 'scenario' column matches the given scenario_combo,
    and saves the filtered data to the destination directory, preserving
    the subdirectory structure.

    Parameters
    ----------
    scenario_combo : str
        The scenario name to filter rows on. Files without a 'scenario' column
        are copied entirely.
    country_code : str
        The ISO country code (e.g., 'IT') for which to share data.

    Examples
    --------
    cd /home/paul/rp/eu_cbm/eu_cbm_hat/scripts/comparison
    ipython
    from share_eu_cbm_data_with_forest_navigator import share_country_data
    share_country_data("reference", "IT")
    """
    country_input_dir = eu_cbm_data_pathlib / "countries" / country_code
    country_dest_dir = DEST_DIR / "countries" / country_code

    for csv_path in country_input_dir.glob("**/*.csv"):
        relative_path = csv_path.relative_to(country_input_dir)
        dest_path = country_dest_dir / relative_path
        try:
            df = pd.read_csv(csv_path)
        except pd.errors.EmptyDataError:
            continue
        if 'scenario' in df.columns:
            df = df[df['scenario'] == scenario_combo]
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(dest_path, index=False)


def share_common_data(country_codes, files_to_share):
    """Share common input files for the given list of countries"""
    pass
