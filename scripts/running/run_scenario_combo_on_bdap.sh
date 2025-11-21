#!/bin/bash
# The purpose of this script is to run the given scenario combination on JRC's BDAP cluster

# It is better to keep as much of the logic as possible in python. But there
# are some steps such as starting the conda environment and moving to the
# relevant directory that are better done at the bash shell. If possible to
# move this to python and to parallelise then this is a future improvement that
# is worth pursuing.
#
# Usage: - make a symbolic link to this script in the home directory for ease
# of use.
#
#       ln -s $HOME/eu_cbm/eu_cbm_hat/scripts/running/run_scenario_combo_on_bdap.sh $HOME/run.sh
#
# - Call it
#
#       ./run.sh pikssp2
#
# - Transfer all aggregated output from a user directory to the shared directory
#
#     rsync -zav $HOME/eu_cbm/eu_cbm_data/output_agg /eos/jeodpp/data/projects/SUSBIOM-TRADE/transfer/eu_cbm_data
# 
# - Transfer a scenario combination's output to the shared directory (replace
#   scenario_combo_name with the scenario combination's name)
#
#     rsync -zav $HOME/eu_cbm/eu_cbm_data/output/scenario_combo_name /eos/jeodpp/data/projects/SUSBIOM-TRADE/transfer/eu_cbm_data/output
#

# Initialize conda for the bash shell 
source $(conda info --base)/etc/profile.d/conda.sh
conda activate eu_cbm_hat

cd $HOME/eu_cbm/eu_cbm_hat/scripts/running/
# Run countries individually to keep Italy alone
# For an unknown reason Italy's run fails to save the output data if run with other countries)
ipython run_scenario_combo.py -- --combo_name $1 --last_year 2070 --countries AT BE BG CZ DE DK EE ES FI FR GR HR HU
ipython run_scenario_combo.py -- --combo_name $1 --last_year 2070 --countries IE LT LU LV NL PL PT RO SE SI SK
ipython run_scenario_combo.py -- --combo_name $1 --last_year 2070 --countries IT

cd $HOME/eu_cbm/eu_cbm_hat/scripts/post_processing/
ipython process_scenario_combo.py -- --combo_names $1 

