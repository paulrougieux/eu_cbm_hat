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

"""

