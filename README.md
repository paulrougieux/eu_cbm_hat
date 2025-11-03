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


# Licence

This program is free software: you can redistribute it and/or modify it under the terms
of the European Union Public Licence, either version 1.2 of the License, or (at your
option) any later version. See [LICENCE.txt](LICENCE.txt) and [NOTICE.txt](NOTICE.txt)
for more information on the licence of components.


# Funding

This work was partially funded by DG Research and Innovation under the Administrative
Agreement DG RTD N° 013 KCB (LC-01591551) JRC Reference N ° 35895 NFP.


# Dependencies

* `libcbm` is a C++ library with python binding developed by the Canadian Forest
  Service. It is bundled into the libcbm_py python package available at
  https://github.com/cat-cfs/libcbm_py

* `eu_cbm_data` contains the model's input and output data located at
  https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_data . In 2022, this is a private
  repository subject to ongoing research.

* `eu_cbm_aidb` contains the "Archive Index Databases" in a separate repository located
  at https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_aidb


# Installation

If you have never used python before and if you are on Windows, you might want to
[install Anaconda](https://www.anaconda.com/) on your system, it will help you with
managing packages dependencies. You also need to [install
git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) in order to install
python packages from git repositories.

Install `eu_cbm_hat` using [pip](https://pip.pypa.io/en/stable/), the package installer
for python in the shell on Linux or Mac or in the **Anaconda prompt** on windows.

    pip install eu_cbm_hat
    # or
    python -m pip install eu_cbm_hat

Install libcbm using pip.

    python -m pip install https://github.com/cat-cfs/libcbm_py/archive/refs/heads/main.tar.gz

By default, the data is located in your home folder. You can display the default
location where the data should be with these commands in python:

    >>> import eu_cbm_hat
    >>> print(eu_cbm_hat.eu_cbm_data_dir)
    >>> print(eu_cbm_hat.eu_cbm_aidb_dir)

|                        | On Unix                 | On windows                              |
| ---------------------- | ----------------------- | --------------------------------------- |
| Data                   | `~/eu_cbm/eu_cbm_data/` | `C:\Users\user_name\eu_cbm\eu_cbm_data` |
| Archive Index Database | `~/eu_cbm/eu_cbm_aidb/` | `C:\Users\user_name\eu_cbm\eu_cbm_aidb` |

Please create the `eu_cbm` directory at the desired location on your system. The model
will work once these folders exist on your system. If you don't want to use the default
location, you can also define the environment variables `EU_CBM_DATA` and `EU_CBM_AIDB`
to tell the model where the data and AIDB are located.

At a python prompt, copy test data to your local `eu_cbm_data` folder (location defined
above in python in `eu_cbm_hat.eu_cbm_data_dir`):

    >>> from eu_cbm_hat.tests.copy_data import copy_test_data
    >>> copy_test_data()

**Load AIDBs and link them to eu_cbm_data**

The Archive Index Databases (AIDBs) are stored in a separate git repository that needs
to be linked with the eu_cbm_data repository. Clone the repository containing the AIDBs
inside your home folder in the parent directory of the path given by
`eu_cbm_hat.eu_cbm_aidb_dir`. Back to the shell (or conda console):

    cd eu_cbm
    git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_aidb.git

Before running the model, you need to create AIDB symlinks at a python prompt:

    >>> from eu_cbm_hat.core.continent import continent
    >>> for country in continent: country.aidb.symlink_all_aidb()


## Upgrade

Over time it's important to regularly upgrade the 2 packages with:

    python -m pip install --upgrade eu_cbm_hat
    python -m pip install --upgrade https://github.com/cat-cfs/libcbm_py/archive/refs/heads/1.x.tar.gz

You should also update the DATA and AIDB git repositories by pulling latest changes from
those repositories.

In case you need to install the latest development version of `eu_cbm_hat`, use the
`--upgrade` parameter and install from the main branch of the gitlab repository. That
the `--no-dependencies` argument avoids reinstalling all dependencies as well:

    python -m pip install --upgrade --force-reinstall --no-dependencies https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat/-/archive/main/eu_cbm_hat-main.tar.gz


## Installation for development purposes

Skip this section if you do not intend to change the code of the model. For development
purposes, these instruction leave the capability to modify the code of the model and
submit changes to the git repositories composing the model. Extensive installation
instructions are available for two different platforms:

* [Installation on Linux](docs/setup_on_linux.md)
* [Installation on Windows](docs/setup_on_windows.md)


# Running the model

Run the test country ZZ at a python prompt:

    from eu_cbm_hat.core.continent import continent
    runner = continent.combos['reference'].runners['ZZ'][-1]
    runner.num_timesteps = 30
    runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

See example of how to run the model for different countries in the `scripts/running`
directory.

## Run a scenario combination

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


## Read the model output

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


## Further process the output

Instantiate a runner object. Note: this can be done after a model run, once the model
has been run, no need to re-run the model at this point, since the output has been
saved to the `eu_cbm_data/output` directory. The `runner.post_processor` method will
read data from that directory.

    from eu_cbm_hat.core.continent import continent
    runner = continent.combos['reference'].runners['LU'][-1]

Compute the Net Annual Increment (NAI)

    nai_lu = runner.post_processor.nai.df_agg(["status"])

Compute harvest expected and provided,

    runner.post_processor.harvest.expected_provided("year")

Compute the sink.

    runner.post_processor.sink.df_agg("year")

The above post processing methods can be computed for one country individually. They can
also be computed for all countries together and saved in a parquet file for further
analysis and comparison between different scenario combinations. For a given scenario
such as "reference", save all post processing output for all countries to parquet files.
This function implements all post processing steps.

    >>> from eu_cbm_hat.post_processor.agg_combos import save_agg_combo_output
    >>> save_agg_combo_output("reference")

Further checks for information:

- Check wood density and bark fraction in all countries:

        from eu_cbm_hat.post_processor.agg_combos import get_df_all_countries
        wood_density_bark_all = get_df_all_countries(
            combo_name="reference",
            runner_method_name="post_processor.wood_density_bark_frac"
        )


## Testing

All dependencies are clearly stated in `.gitlab-ci.yml` and the `setup.py` files at the
root of the repository. In fact those 2 files are used to automatically install and test
the install  each time we make a change to the model. The test consist in unit tests as
well as running a mock country called "ZZ". You can see the output of these runs
(successful or not) in the CI-CD jobs page on gitlab.


## Model runs used in publications

- The model run used in the technical report

    - European Commission, Joint Research Centre, Rougieux, P., Pilli, R., Blujdea, V.,
    Mansuy, N. and Mubareka, S.B., Simulating future wood consumption and the impacts on
    Europe's forest sink to 2070, Publications Office of the European Union, Luxembourg,
    2024, https://data.europa.eu/doi/10.2760/17191, JRC136526.

    - Corresponds to the data at commit d7ddf2963666bc57360c6576e050e022d3b75e3f in
      branch run-ssp2-fair-v2023



# Definitions and specification

- A specification for an Harvest Allocation Tool (HAT) is available at
  [docs/harvest_allocation_specification.md](docs/harvest_allocation_specification.md)

- Input files (disturbances, yield, inventory) defined in `eu_cbm_data` contain scenarios for the activities (afforestation, deforestation, reforestation, disturbances in forest remaining forest, wood use specified in the silviculture and product_types.csv tables)



## Growth period

For the purpose of initializing the soil carbon pool, we use a different growth curve
called the "Init" growth curve. That growth curve takes into account previous harvest
and natural disturbances within the growth curve.

- Looking at the input inventory you will see a classifier called "growth period" which
  has the value "init" everywhere.

- See figure 3 of Pilli 2013 "Application of the CBM-CFS3 model to estimate Italy’s
  forest carbon budget, 1995–2020" for an explanation of the need to switch from an init
  growth period to a current growth period. The `Simulation.switch_period()` method
  changes the growth period from "Init" to "Cur". As a result all stands will have the
  value "Cur" for the groth_period classifier from inventory start year onwards. Note
  the inventory start year is specified in `runner.country.inventory_start_year`.


## Units

The main unit used inside CBM are in tons of carbon. But input yield curves are in m3 of
merchantable biomass per hectare. The harvest data is in m3 of biomass under bark.

See some of the unit conversion functions inside post_processor/convert.py for more
information on the units.


# Extra documentation

More documentation is available at:
https://bioeconomy.gitlab.io/eu_cbm/eu_cbm_hat/eu_cbm_hat.html

This documentation is simply generated in `.gitlab-ci.yml` with:

    $ pdoc -o public ./eu_cbm_hat

