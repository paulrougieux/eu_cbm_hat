"""Concatenate Harvested Wood Products results from Roberto

Usage:

    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/post_processing/hwp_load_from_excel.py

The following script moves HWP data from many Excel files to one csv file in
~/eu_cbm/eu_cbm_data/output_agg/hwp

"""

import pandas
from eu_cbm_hat import eu_cbm_data_pathlib
hwp_country_dir = eu_cbm_data_pathlib / "output_agg/hwp/countries"


#######################################
# Load and concatenate country tables #
#######################################
hwp = pandas.DataFrame()
for file_path in hwp_country_dir.iterdir():
    df = pandas.read_excel(file_path)
    hwp = pandas.concat([hwp, df])

hwp.reset_index(drop=True, inplace=True)


# Clean column names
cols = hwp.columns
selected_cols = cols[~cols.str.contains("named")]
selector = ~hwp["year"].isna()
hwp = hwp.loc[selector, selected_cols].copy()
hwp.rename(columns={"(All)": "all"}, inplace=True)
hwp.rename(columns=lambda x: str(x).lower(), inplace=True)

# Place scenario and country first
cols = ['scenario', 'country', 'year', 'hwp_sink_bau', 'hwp_sink_plus', 'hwp_sink_minor', 'crf', 'all']
hwp = hwp[cols].copy()

# Change column types
for col in ['hwp_sink_bau', 'hwp_sink_plus', 'hwp_sink_minor', 'crf', 'all']:
    hwp[col] = pandas.to_numeric(hwp[col], errors="coerce")

for col in ['scenario', 'country']:
    hwp[col] = hwp[col].astype(str)

hwp["year"] = hwp["year"].astype(int)

# Sort values
hwp.sort_values(["scenario", "country", "year"], inplace=True)

#############################################################
# Write to a CSV file to be archived in eu_cbm_data, in git #
#############################################################
# Note this file was first put in eu_cbm_data/domestic_harvest/hwp But this
# resulted in an error due to the make_combined function in
# ~/repos/eu_cbm/eu_cbm_hat/eu_cbm_hat/info/harvest.py
#
#     FileNotFoundError: [Errno 2] No such file or directory: <FilePath object
#     "/home/paul/repos/eu_cbm/eu_cbm_data/domestic_harvest/hwp/irw_harvest.csv">
#
# That is why it was moved to output_agg/hwp

file_path = eu_cbm_data_pathlib / "output_agg/hwp/hwp_2023.csv"
hwp.to_csv(file_path, index=False)

