""" Post processing of the EU_CBM_HAT scenario combinations output

See post_processor/agg_combos.py for documentation of the save_agg_combo_output

Usage:

    cd $HOME/repos/eu_cbm/eu_cbm_hat/scripts/post_processing
    # or on BDAP
    cd $HOME/eu_cbm/eu_cbm_hat/scripts/post_processing
    ipython -i process_scenario_combo.py -- --combo_names reference
    ipython -i process_scenario_combo.py -- --combo_names reference pikssp2 pikfair
    ipython -i process_scenario_combo.py -- --combo_names reference pikssp2_fel1 pikfair_fel1

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
