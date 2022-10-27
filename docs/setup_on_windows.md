# Installation

This guide shows how to set up the `libcbm_data` and `eu_cbm_hat` projects together on a Windows system to run the 26 EU carbon budget simulations with `libcbm_py` automatically.

## Install Python 3

Run this command from an administrator shell if you don't already have python:

    $ choco install -y python3 --version=3.9.7

It requires the chocolatey package manager from https://chocolatey.org for windows. At the end, you will have to reboot.
Finally, check the version in a new shell:

    $ python -V

## Install dependencies

Run this command from an administrator shell to get gits:

    $ choco install -y git

## Clone repos

The next step is to clone the needed git repositories.
Run these commands from an administrator PowerShell:

    $ New-Item -ItemType Directory -Path $HOME/repos
    $ cd $HOME/repos
    $ git clone https://github.com/cat-cfs/libcbm_py.git
    $ git clone https://gitlab.com/bioeconomy/libcbm/eu_cbm_hat.git
    $ git clone https://gitlab.com/bioeconomy/libcbm/libcbm_data.git
    $ git clone https://gitlab.com/bioeconomy/libcbm/eu_cbm_aidb.git

## Install python packages

Use pip from an administrator shell:

    $ pip install autopaths
    $ pip install plumbing
    $ pip install simplejson
    $ pip install numexpr
    $ pip install tqdm
    $ pip install p_tqdm


## Upgrade dependencies if needed

    for example plumbing
    pip install --upgrade plumbing

Set a specific variant of pandas to avoid warnings about the frame.append method as 
documented in https://github.com/cat-cfs/libcbm_py/issues/27

    pip install --upgrade pandas==1.3.5

See also issue https://gitlab.com/bioeconomy/libcbm/eu_cbm_hat/-/issues/38 

## Set environment variables

Set the environment variable that tells python where the modules are located:

    $ SETX PYTHONPATH "$HOME/repos/eu_cbm_hat;$HOME/repos/libcbm_py"

Set the environment variable that tells `eu_cbm_hat` where the simulation data is located:

    $ SETX LIBCBM_DATA "$HOME\repos\libcbm_data"

Set the environment variable that tells `eu_cbm_hat` where the special AIDBs are located:

    $ SETX EU_CBM_AIDB "$HOME\repos\eu_cbm_aidb"

## Symlink AIDBs

Create symlinks for these special files (requires administrator privileges):

    $ ipython -i -c "from eu_cbm_hat.core.continent import continent as ct; print([c.aidb.symlink_all_aidb() for c in ct])"

## Run one country

Run a given country from the historical scenario.

You can use these commands in python:

    >>> from eu_cbm_hat.core.continent import continent
    >>> scenario = continent.scenarios['historical']
    >>> runner_libcbm = scenario.runners['LU'][-1]
    >>> runner_libcbm.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

## Run all countries

To run a full scenario, proceed as so:

     >>> from eu_cbm_hat.core.continent import continent
     >>> scen = continent.scenarios['historical']
     >>> scen()

## More information

You can refer to [this guide](setup_on_linux.md#Run) for the next steps.
