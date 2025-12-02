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
from eu_cbm_hat import eu_cbm_data_pathlib
from eu_cbm_hat.core import continent

# Change these input parameters
DEST_DIR = Path("~/eu_cbm/eu_cbm_data_forest_navigator").expanduser()
COMMON_FILES_TO_SHARE = ["country_codes.csv", "reference_years.csv"]


def share_country_data(scenario_combo, country_code): 
    """shares only the data for the given scenario yaml file and country name.
    This is not just about copying a file, it needs to filter the rows for the
    given scenario combination."""
    country_input_dir = eu_cbm_data_pathlib / "countries" / country_code
    country_dest_dir = DEST_DIR / "countries" / country_code
    # Glob search CSV files in the country_input_dir
    # for each csv file:
    #      If they have a scenario column filter scenario==scenario_combo input parameter
    #      Write it to the destinatio dir, respecting the sub directory structure



def share_common_data(country_codes, files_to_share):
    """Share common input files for the given list of countries"""
