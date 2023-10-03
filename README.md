# EU-CBM-HAT

The forest carbon model `eu_cbm_hat` is a python package that enables the assessment of
forest CO2 emissions and removals under scenarios of forest management, natural
disturbances, forest-related land use changes.

EU-CBM-HAT depends on the [libcbm model](https://github.com/cat-cfs/libcbm_py) developed
by Forest Carbon Accounting team of the Canadian Forest Service. Both python modules use
[pandas data frames](https://pandas.pydata.org/) to transform and load data.


# Documentation

The model was described in a 2022 JRC Technical Report called [The JRC Forest Carbon
Model: description of
EU-CBM-HAT](https://publications.jrc.ec.europa.eu/repository/handle/JRC130609)

See also

- Installation instructions below

- Software documentation at
  https://bioeconomy.gitlab.io/eu_cbm/eu_cbm_hat/eu_cbm_hat.html


## Licence

This program is free software: you can redistribute it and/or modify it under the terms
of the European Union Public Licence, either version 1.2 of the License, or (at your
option) any later version. See [LICENCE.txt](LICENCE.txt) and [NOTICE.txt](NOTICE.txt)
for more information on the licence of components.


## Dependencies

* `libcbm` is a C++ library with python binding developed by the Canadian Forest
  Service. It is bundled into the libcbm_py python package available at
  https://github.com/cat-cfs/libcbm_py

* `eu_cbm_data` contains the model's input and output data located at
  https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_data . In 2022, this is a private
  repository subject to ongoing research.

* `eu_cbm_aidb` contains the "Archive Index Databases" in a separate repository located
  at https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_aidb


## Installation

If you have never used python before and if you are on Windows, you might want to
[install Anaconda](https://www.anaconda.com/) on your system, it will help you with
managing packages dependencies. You also need to [install
git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) in order to install
python packages from git repositories.

Install `eu_cbm_hat` using [pip](https://pip.pypa.io/en/stable/), the package installer
for python in the shell (or conda console).

    pip install eu_cbm_hat
    # or
    python -m pip install eu_cbm_hat

Install libcbm using pip. Note: currently only version 1 is supported. Update to version
2 is under discussion in [issue
53](https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat/-/issues/53):

    python -m pip install https://github.com/cat-cfs/libcbm_py/archive/refs/heads/1.x.tar.gz

Over time it's important to regularly upgrade the 2 packages with:

    python -m pip install --upgrade eu_cbm_hat
    python -m pip install --upgrade https://github.com/cat-cfs/libcbm_py/archive/refs/heads/1.x.tar.gz

In case you need to install the latest development version, use the --upgrade parameter
and install from the main branch of the gitlab repository:

    python -m pip install --upgrade --force-reinstall https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat/-/archive/main/eu_cbm_hat-main.tar.gz

By default, the data is located in your home folder. You can display the default
location where the data should be with these commands in python:

    >>> import eu_cbm_hat
    >>> eu_cbm_hat.eu_cbm_data_dir
    >>> eu_cbm_hat.eu_cbm_aidb_dir

|                        | On Unix                 | On windows                              |
| ---------------------- | ----------------------- | --------------------------------------- |
| Data                   | `~/eu_cbm/eu_cbm_data/` | `C:\Users\user_name\eu_cbm\eu_cbm_data` |
| Archive Index Database | `~/eu_cbm/eu_cbm_aidb/` | `C:\Users\user_name\eu_cbm\eu_cbm_aidb` |

The model will work once these folders exist on your system. Optionally, you can define
the environment variables `EU_CBM_DATA` and `EU_CBM_AIDB` to tell the model where the
data and AIDB are located.

Copy test data to your local `eu_cbm_data` folder (location defined above in python in
`eu_cbm_hat.eu_cbm_data_dir`):

    >>> from eu_cbm_hat.tests.copy_data import copy_test_data
    >>> copy_test_data()

Clone the repository containing the AIDB (with a deploy token) inside your home folder
in the parent directory of the path given by `eu_cbm_hat.eu_cbm_aidb_dir`. Back to the
shell (or conda console):

    git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_aidb.git

Before running the model, you need to create AIDB symlinks at a python prompt:

    >>> from eu_cbm_hat.core.continent import continent
    >>> for country in continent: country.aidb.symlink_all_aidb()


### Installation for development purposes

Skip this section if you do not intend to change the code of the model. For development
purposes, these instruction leave the capability to modify the code of the model and
submit changes to the git repositories composing the model. Extensive installation
instructions are available for two different platforms:

* [Installation on Linux](docs/setup_on_linux.md)
* [Installation on Windows](docs/setup_on_windows.md)


## Running the model

Run the test country ZZ at a python prompt:

    from eu_cbm_hat.core.continent import continent
    runner = continent.combos['reference'].runners['ZZ'][-1]
    runner.num_timesteps = 30
    runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)


### Run a scenario combination

Run a scenario combination for all EU countries at once (see the [documentation on
combos](https://bioeconomy.gitlab.io/eu_cbm/eu_cbm_hat/eu_cbm_hat/combos.html)
for how to specify them):

    cd $HOME/eu_cbm/eu_cbm_hat/scripts/running/
    ipython -i run_scenario_combo.py -- --combo_name reference --last_year 2050
    ipython -i run_scenario_combo.py -- --combo_name pikssp2 --last_year 2070
    ipython -i run_scenario_combo.py -- --combo_name pikfair --last_year 2070

Process the output data for a list of scenario combinations provided as an argument.
Compute the harvest expected and provided as well as the sink
in an aggregated way:

    cd $HOME/eu_cbm/eu_cbm_hat/scripts/post_processing
    ipython -i process_scenario_combo.py -- --combo_names reference pikssp2 pikfair


### Inspect the model output

Inspect the output of the model

    # Input events sent to libcbm
    events_input = runner.input_data["events"]
    # Events stored in the output including the ones related to the harvest
    # allocation tool HAT
    events_output = runner.output["events"]
    # Available volumes used by the Harvest Allocation Tool
    output_extras = runner.output.extras

    # Load tables without classifiers
    area = runner.output.load('area', with_clfrs=False)
    params = runner.output.load('parameters', with_clfrs=False)
    flux = runner.output.load('flux', with_clfrs=False)
    state = runner.output.load('state', with_clfrs=False)

    # Load classifiers with their actual values
    classifiers = runner.output.classif_df
    classifiers["year"] =  runner.country.timestep_to_year(classifiers["timestep"])

    # Merge tables
    index = ['identifier', 'year']
    flux_dist = (params
                 .merge(area, 'left', on = index) # Join the area information
                 .merge(flux, 'left', on = index)
                 .merge(state, 'left', on = index) # Join the age information
                 .merge(classifiers, 'left', on = index) # Join the classifiers
                 )


### Testing

All dependencies are clearly stated in `.gitlab-ci.yml` and the `setup.py` files at the
root of the repository. In fact those 2 files are used to automatically install and test
the install  each time we make a change to the model. The test consist in unit tests as
well as running a mock country called "ZZ". You can see the output of these runs
(successful or not) in the CI-CD jobs page on gitlab.


## Definitions and specification

- A specification for an Harvest Allocation Tool (HAT) is available at
  [docs/harvest_allocation_specification.md](docs/harvest_allocation_specification.md)

- Input files (disturbances, yield, inventory) defined in `eu_cbm_data` contain scenarios for the activities (afforestation, deforestation, reforestation, disturbances in forest remaining forest, wood use specified in the silviculture and product_types.csv tables)



## Extra documentation

More documentation is available at:
https://bioeconomy.gitlab.io/eu_cbm/eu_cbm_hat/eu_cbm_hat.html

This documentation is simply generated in `.gitlab-ci.yml` with:

    $ pdoc -o public ./eu_cbm_hat

