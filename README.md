# `libcbm_runner` version 0.2.2

`libcbm_runner` is a python package for dealing with the automation and running of a complex series of models involving forest growth, the European economy, carbon budgets and their interactions. It uses the `libcbm` model developed by Canada under the hood.

This python module uses pandas data frames to manipulate and store most data.


## Dependencies

* `libcbm` is a C++ library with python binding developed by the Canadian Forest Service. It is bundled into the libcbm_py python package available at https://github.com/cat-cfs/libcbm_py

* `libcbm_data` contains the model's input and output data located at https://gitlab.com/bioeconomy/libcbm/libcbm_data

* `libcbm_aidb` contains the "Archive Index Databases" in a separate repository located at https://github.com/xapple/libcbm_aidb


## Installation

Install `libcbm_runner` and HAT using [pip](https://pip.pypa.io/en/stable/), the package 
installer for python. The repository is currently private, but you can install the 
`libcbm_runner` package from python with a deploy token.

    pip install git+https://jrc:xyVzrCMS4fs7GRe7pZPq@gitlab.com/bioeconomy/libcbm/libcbm_runner.git

Optionally upgrade the package to a newer version

    pip install --upgrade git+https://jrc:xyVzrCMS4fs7GRe7pZPq@gitlab.com/bioeconomy/libcbm/libcbm_runner.git

Note that the deploy token will not be necessary once the package is public. This 
installation method will change, and the updated installation method will be made 
available in the repository: https://gitlab.com/bioeconomy/libcbm/libcbm_runner

Install libcbm using pip:

    pip install git+https://github.com/cat-cfs/libcbm_py.git

By default, the data is located in "~/repos/libcbm_data/" and the AIBD in 
“~/repos/libcbm_aidb/”. The model will work if you make sure these folders exist on your 
system. Optionally, you can define the following environment variables to tell the model 
where the data and AIDB are located. Shell commands to define the environment variables:

    export LIBCBM_DATA="path_on_your_computer/libcbm_data/"
    export LIBCBM_AIDB="path_on_your_computer/libcbm_aidb/"

Copy test data to your local `libcbm_data` folder (location defined above in the 
environment variable `LIBCBM_DATA`):

import shutil
from pathlib import Path
from libcbm_runner import module_dir, libcbm_data_dir
orig_path = Path(module_dir) / "tests/libcbm_data"
dest_path = Path(libcbm_data_dir)
# Create the data folder if it doesn't exist
dest_path.mkdir(exist_ok=True, parents=True)
# Copy ZZ test data to the libcbm_data directory
shutil.copytree(orig_path, dest_path)




Clone the repository containing the AIDB (with a deploy token)

    git clone https://jrc:9Bv2ZN9fWBgJaHe2jWxz@gitlab.com/bioeconomy/libcbm/libcbm_aidb.git


Before running the model, you need to create AIDB symlinks at a python prompt:

    from libcbm_runner.core.continent import continent
    for country in continent: country.aidb.symlink_all_aidb()


### Installation for development purposes

Skip this section if you do not intend to change the code of the model. For development 
purposes, these instruction leave the capability to modify the code of the model and 
submit changes to the git repositories composing the model. Extensive installation 
instructions are available for two different platforms:

* [Installation on Linux](docs/setup_on_linux.md)
* [Installation on Windows](docs/setup_on_windows.md)


## Running the model

Run the test country ZZ at a python prompt:

    from libcbm_runner.core.continent import continent
    runner = continent.combos['hat'].runners['ZZ'][-1]
    runner.num_timesteps = 30
    runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)


### Inspect the model output

Inspect the output of the model

    # Input events sent to libcbm
    events_input = runner.input_data["events"]
    # Events stored in the output
    events_output = runner.output.events
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

- Input files (disturbances, yield, inventory) defined in `libcbm_data` contain scenarios for the activities (afforestation, deforestation, reforestation, disturbances in forest remaining forest, wood use specified in the silviculture and product_types.csv tables)



## Extra documentation

More documentation is available at:

<http://xapple.github.io/libcbm_runner/libcbm_runner>

This documentation is simply generated with:

    $ pdoc --html --output-dir docs --force libcbm_runner
