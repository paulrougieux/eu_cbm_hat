""" Post processing of the EU_CBM_HAT scenario combinations output

See post_processor/agg_combos.py for documentation of the save_agg_combo_output

Usage:

    cd $HOME/repos/eu_cbm/eu_cbm_hat/scripts/post_processing
    # or on BDAP
    cd $HOME/eu_cbm/eu_cbm_hat/scripts/post_processing
    ipython -i process_scenario_combo.py -- --combo_names reference
    ipython -i process_scenario_combo.py -- --combo_names reference pikssp2 pikfair
    ipython -i process_scenario_combo.py -- --combo_names reference pikssp2_fel1 pikfair_fel1

Separate processing to update a single data frame

    >>> from eu_cbm_hat.post_processor.agg_combos import apply_to_all_countries
    >>> from eu_cbm_hat.post_processor.agg_combos import nai_by_sf_one_country
    >>> from eu_cbm_hat.post_processor.agg_combos import output_agg_dir
    >>> combo = "pikssp2_fel1"
    >>> combo_dir = output_agg_dir / combo
    >>> nai_sf = apply_to_all_countries(nai_by_sf_one_country, combo_name=combo)
    >>> nai_sf.to_parquet(combo_dir / "nai_by_sf.parquet")

"""

import argparse
from eu_cbm_hat.post_processor.agg_combos import save_agg_combo_output

parser = argparse.ArgumentParser(
    description="Post processing of the EU_CBM_HAT scenario combinations"
)
parser.add_argument(
    "--combo_names", nargs="+", default=None, help="List of names of scenario combos"
)

shell_args = parser.parse_args()
COMBO_NAMES = shell_args.combo_names

for x in COMBO_NAMES:
    save_agg_combo_output(x)
