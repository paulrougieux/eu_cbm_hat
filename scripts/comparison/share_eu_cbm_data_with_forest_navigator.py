#!/usr/bin/env python
"""Share EU CBM DATA for a given list of scenarios and a selection of countries

- Selected scenarios: reference
- Selected countries: IT, IE, CZ

A function that shares only the data for the given list of scenario
combinations and country names. For a given scenario combination combo yaml
file the function takes a scenario combo and shares all lines in all input
files that correspond to that scenario. For the selected countries country. It
saves the output files with the same data structure inside a destination
directory.

Usage as a command line script:

    cd ~/eu_cbm/eu_cbm_hat/scripts/comparison
    ipython -i share_eu_cbm_data_with_forest_navigator.py

Usage from python

    cd ~/eu_cbm/eu_cbm_hat/scripts/comparison
    ipython

    from share_eu_cbm_data_with_forest_navigator import share_one_csv_file
    from share_eu_cbm_data_with_forest_navigator import get_scenarios_from_combos
    from share_eu_cbm_data_with_forest_navigator import share_eu_cbm_data
    from share_eu_cbm_data_with_forest_navigator import share_common_data

    # Share country data
    share_eu_cbm_data(combo_names=["reference", "no_management"],
                      country_codes=["IT", "IE", "CZ"],
                      dest_dir="~/eu_cbm/eu_cbm_data_forest_navigator")
    # Share common data
    share_common_data(COMMON_FILES_TO_SHARE, dest_dir)

We only share the common files that are in the list in this script. For the
given list of countries.

See development notes under issue:

    no_management

"""

from pathlib import Path
from typing import Union, List
import shutil
import pandas as pd
import argparse
from eu_cbm_hat import eu_cbm_data_pathlib
from eu_cbm_hat.core.continent import continent

# Change these input parameters
COMMON_FILES_TO_SHARE = ["country_codes.csv", "reference_years.csv"]

def share_one_csv_file(
    orig_dir: Path,
    relative_path: str,
    dest_dir: Path,
    scenarios: Union[str, List[str]]
) -> None:
    """Share data for one file and filter for the given scenario(s).

    Parameters
    ----------
    orig_dir : Path
        The original directory path, a country directory within
        eu_cbm_data/countries.
    relative_path : str
        The relative path to the CSV file within the original directory.
    dest_dir : Path
        The destination directory path where the filtered file will be saved.
    scenarios : Union[str, List[str]]
        The scenario(s) to filter by. If a string, it will be converted to a
        list.

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
        print(f"No data in {orig_csv_file} not copying.")
        return
    if 'scenario' in df.columns and scenarios:
        df = df[df['scenario'].isin(scenarios)]
    if "scenario" in df.columns and scenarios is None:
        msg = "There is a scenario column in the file: "
        msg += f"{orig_csv_file}\n"
        msg += "Please define which scenarios to select."
        msg += f"Current value of scenarios: {scenarios}"
        raise ValueError(msg)
    dest_csv_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest_csv_file, index=False)


def get_scenarios_from_combos(combo_names):
    """Collect unique scenarios for each file type from the given combo names.

    Examples
    --------
     get_scenarios_from_combos(combo_names=["reference", "no_management"])
    """
    combo_configs = {name: continent.combos[name].config for name in combo_names}
    activities_files = ['inventory', 'events', 'growth_curves', 'transitions']
    other_files = ['events_templates', 'irw_frac_by_dist', 'harvest_factors', 'harvest']
    selected_scenarios_in_files = {}
    for file_name in activities_files + other_files:
        all_scenarios = set()
        for config in combo_configs.values():
            try:
                all_scenarios.update(config[file_name].values())
            except AttributeError:
                all_scenarios.update([config[file_name]])
        scenarios = list(all_scenarios)
        selected_scenarios_in_files[file_name] = scenarios
    return selected_scenarios_in_files


def share_eu_cbm_data(combo_names, country_codes, dest_dir):
    """Share EU CBM DATA for a given list of scenarios and a selection of countries

    Parameters
    ----------
    combo_names : str or list of str
        The scenario combo name(s), e.g., "reference"
    country_codes : list of str
        List of ISO country codes (e.g., ['IT', 'IE', 'CZ'])
    dest_dir : str or Path
        The destination directory path

    Examples
    --------
    share_eu_cbm_data(combo_names=["reference", "no_management"],
                      country_codes=["IT", "IE", "CZ"],
                      dest_dir="~/eu_cbm/eu_cbm_data_forest_navigator")
    """
    if isinstance(combo_names, str):
        combo_names = [combo_names]
    else:
        combo_names = combo_names
    if isinstance(country_codes, str):
        country_codes = [country_codes]
    dest_dir = Path(dest_dir).expanduser()
    scenario_files_map = get_scenarios_from_combos(combo_names)
    # Share country data
    for this_country in country_codes:
        print("\n\n")
        country_orig_dir = eu_cbm_data_pathlib / "countries" / this_country
        country_dest_dir = dest_dir / "countries" / this_country
        # Find all CSV files in the country directory
        csv_files = list(country_orig_dir.glob("**/*.csv"))
        for orig_csv_file in csv_files:
            relative_path = orig_csv_file.relative_to(country_orig_dir)
            # Ignore some files not defined in the reference yaml file
            if orig_csv_file.stem in ["disturbance_matrix_value", "events_templates_original"]:
                print(f"Ignoring {orig_csv_file}")
                continue 
            if orig_csv_file.stem in scenario_files_map.keys():
                scenarios = scenario_files_map[orig_csv_file.stem]
            else:
                scenarios = None
            print(orig_csv_file)
            print("Selected scenarios: {scenarios}\n")
            share_one_csv_file(
                orig_dir=country_orig_dir,
                relative_path=relative_path,
                dest_dir=country_dest_dir,
                scenarios=scenarios
            )

def share_common_data(files_to_share, dest_dir):
    """Share common input files for the given list of countries

    Parameters
    ----------
    files_to_share : list of str
        List of common file names to copy.
    dest_dir : Path
        The destination directory path

    Examples
    --------
    cd /home/paul/rp/eu_cbm/eu_cbm_hat/scripts/comparison
    ipython
    from share_eu_cbm_data_with_forest_navigator import share_common_data
    share_common_data()
    """
    common_orig_dir = eu_cbm_data_pathlib / "common"
    common_dest_dir = (Path(dest_dir) / "common").expanduser()
    for file_name in files_to_share:
        src_path = common_orig_dir / file_name
        dest_path = common_dest_dir / file_name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        print(src_path)
        print(dest_path)
        shutil.copy2(src_path, dest_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Share EU CBM DATA for given scenarios and countries.")
    parser.add_argument('--combo_names', nargs='+', default=['reference', 'no_management'],
                        help='List of scenario combo names (default: ["reference", "no_management"])')
    parser.add_argument('--country_codes', nargs='+', default=['IT', 'IE', 'CZ'],
                        help='List of ISO country codes (default: ["IT", "IE", "CZ"])')
    parser.add_argument('--dest_dir', default='~/eu_cbm/eu_cbm_data_forest_navigator',
                        help='Destination directory path (default: "~/eu_cbm/eu_cbm_data_forest_navigator")')
    args = parser.parse_args()

    # Share country data
    share_eu_cbm_data(combo_names=args.combo_names,
                      country_codes=args.country_codes,
                      dest_dir=args.dest_dir)

    # Share common data
    share_common_data(COMMON_FILES_TO_SHARE, args.dest_dir)


