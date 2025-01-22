"""Run the Reference scenario combo in V2 and V2

Using the symbolic link defined in scripts/running/run_on_bdap.sh, make sure
that the repository switch works correctly before running the second scenario.

    cd $HOME
    ipython ~/eu_cbm/eu_cbm_hat/scripts/conversion/libcbmv2/switch_git_repos.py -- --version 1
    ./run.sh reference.py
    ipython ~/eu_cbm/eu_cbm_hat/scripts/conversion/libcbmv2/switch_git_repos.py -- --version 2
    ./run.sh refence_v2.py

Run only one country

    ipython ~/eu_cbm/eu_cbm_hat/scripts/conversion/libcbmv2/switch_git_repos.py -- --version 1
    ipython ~/eu_cbm/eu_cbm_hat/scripts/running/run_lu.py
    ipython ~/eu_cbm/eu_cbm_hat/scripts/conversion/libcbmv2/switch_git_repos.py -- --version 2
    ipython ~/eu_cbm/eu_cbm_hat/scripts/running/run_lu.py
    # Try another scenario
    cd $HOME/eu_cbm/eu_cbm_hat/scripts/running/
    ipython run_scenario_combo.py -- --combo_name pikssp2_fel1 --last_year 2070 --countries LU

Run the reference2 scenario with libcbm version 2 for a list of countries

    ipython ~/eu_cbm/eu_cbm_hat/scripts/conversion/libcbmv2/switch_git_repos.py -- --version 2
    cd $HOME/eu_cbm/eu_cbm_hat/scripts/running/
    ipython run_scenario_combo.py -- --combo_name reference_v2 --last_year 2050 --countries AT CZ DE DK EE ES FI IE IT LT LU LV NL RO SI SK
    ipython run_scenario_combo.py -- --combo_name reference_v2 --last_year 2050 --countries IT

"""

