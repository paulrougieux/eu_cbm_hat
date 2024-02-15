
# Introduction

The purpose of this document is to describe the EU-CBM-HAT workflow.


[[_TOC_]]


## Timeline



           inventory       calibration                      Simulation
           start year       period          base year         period
        ------ | --------------------------- | ------------------------------>

        Init   |   Current
        growth |   growth
        curve  |   curve
                                             |
                      activities/mgmt        |   silv/events_templates.csv
                      events                 |   events



# EU CBM DATA

Structure of EU CBM DATA



 - combos  common  countries  domestic_harvest  output  output_agg  plot  README.md  tmp


## Country input data

Here is an example of all the country input data for Finland

    paul@castanea:~/rp/eu_cbm/eu_cbm_data/countries/FI$ tree
    .
    ├── activities
    │   ├── afforestation
    │   │   ├── events.csv
    │   │   ├── growth_curves.csv
    │   │   ├── inventory.csv
    │   │   └── transitions.csv
    │   ├── deforestation
    │   │   ├── events.csv
    │   │   ├── growth_curves.csv
    │   │   ├── inventory.csv
    │   │   └── transitions.csv
    │   ├── mgmt
    │   │   ├── events.csv
    │   │   ├── growth_curves.csv
    │   │   ├── inventory.csv
    │   │   └── transitions.csv
    │   ├── nd_nsr
    │   │   ├── events.csv
    │   │   ├── growth_curves.csv
    │   │   ├── inventory.csv
    │   │   └── transitions.csv
    │   └── nd_sr
    │       ├── events.csv
    │       ├── growth_curves.csv
    │       ├── inventory.csv
    │       └── transitions.csv
    ├── common
    │   ├── age_classes.csv
    │   ├── classifiers.csv
    │   └── disturbance_types.csv
    ├── config
    │   ├── aidb.db -> /home/paul/repos/eu_cbm/eu_cbm_aidb/countries/FI/aidb.db
    │   └── associations.csv
    └── silv
        ├── disturbance_matrix_value.csv
        ├── events_templates.csv
        ├── harvest_factors.csv
        ├── irw_frac_by_dist.csv
        └── vol_to_mass_coefs.csv

The 5 directories in `activities` define fixed input files for the simulation

    - afforestation
    - deforestation
    - mgmt management
    - nd_nsr natural disturbance non stand replacing
    - nd_sr natural disturbance stand replacing

For a given `scenario` these files will be combined into one file.
For example all these files

    ./activities/mgmt/events.csv
    ./activities/nd_nsr/events.csv
    ./activities/nd_sr/events.csv
    ./activities/deforestation/events.csv
    ./activities/afforestation/events.csv

Will be combined into one `events.csv` file sent to libcbm.


These files are valid both for the calibration period and the simulation period.


The common and config files are not going to change during the simulation

    ├── common
    │   ├── age_classes.csv
    │   ├── classifiers.csv
    │   └── disturbance_types.csv
    ├── config
    │   ├── aidb.db -> /home/paul/repos/eu_cbm/eu_cbm_aidb/countries/FI/aidb.db
    │   └── associations.csv


## From scenario input data to the data fed to libcbm

The scenario input data, is defined in terms of rows  you add new rows into these csv files and you save the new rows under a new scenario name.

`/eu_cbm_data/countries/FI$ open activities/afforestation/events.csv`



| scenario  | status | forest_type | region | mgmt_type | mgmt_strategy | climate | con_broad | site_index | growth_period | sw_start | sw_end | measurement_type | dist_type_name | amount_2021 | amount_2022 | amount_2023 |
|-----------|--------|-------------|--------|-----------|---------------|---------|-----------|------------|---------------|----------|--------|------------------|----------------|-------------|-------------|-------------|
| reference | NF     | NF_OB       | ?      | ?         | ?             | ?       | broad     | 1          | Cur           | 0        | 200    | A                | 8              | 741         | 741         | 741         |
| scenario_1   | NF     | NF_OB       | ?      | ?         | ?             | ?       | broad     | 1          | Cur           | 0        | 200    | A                | 8              | 452         | 451         | 462         |

In the yaml scenario combination file at `eu_cbm_data/combos/reference.yaml`

    events:
      afforestation: reference

If the "reference" scenario is selected for that file, the runner will take only the rows containing the reference scenario and feed them to libcbm.


See input for libcbm below. The structure of one imput file for example looks like this:


`/eu_cbm_data/output/reference/FI/0/input/csv/events.csv`


| status | forest_type | region | mgmt_type | mgmt_strategy | climate | con_broad | site_index | growth_period | sw_start | sw_end | measurement_type | amount | dist_type_name | step |
|--------|-------------|--------|-----------|---------------|---------|-----------|------------|---------------|----------|--------|------------------|--------|----------------|------|
| NF     | NF_OB       | ?      | ?         | ?             | ?       | broad     | 1          | Cur           | 0        | 200    | A                | 741    | 8              | 12   |
| NF     | NF_OB       | ?      | ?         | ?             | ?       | broad     | 1          | Cur           | 0        | 200    | A                | 741    | 8              | 13   |
| NF     | NF_OB       | ?      | ?         | ?             | ?       | broad     | 1          | Cur           | 0        | 200    | A                | 741    | 8              | 14   |


## creating new scenarios

See also the combo documentation on how to create new scenario combinations at [eu_cbm_hat/eu_cbm_hat/combos.html](https://bioeconomy.gitlab.io/eu_cbm/eu_cbm_hat/eu_cbm_hat/combos.html).

Using the yaml configuration files in eu_cbm_data/combos it's possible to associate a different scenario for each different input files, and for some input files even a different scenario for each year.

If you require more flexibilityn, it's possible to instantiate a child class of the scenario combination object, using a mechanism similar to the dynamic runner for example activated
throught the `runner_type` key in the yaml file:

    runner_type: dynamic_runner

This will trigger the following lines of codes in `eu_cbm_hat/combos/base_combo.py`:

        # If it's defined as "dynamic_runner" return dynamic runners
        if self.config["runner_type"] == "dynamic_runner":
            return {c.iso2_code: [DynamicRunner(self, c, 0)] for c in self.continent}

For example to see the cotent of the yaml files from an active runner, call `runner.combo.config`:

    from eu_cbm_hat.core.continent import continent
    runner = continent.combos['reference'].runners['LU'][-1]
    runner.combo.config


The dynamic runner is defined in `eu_cbm_hat/cbm/dynamic.py`.


# Preparation of input for libcbm




# Output data

Output data for a country for example `eu_cbm_data/output/reference/LU/0` looks like

    ├── input
    │   ├── csv
    │   └── json
    ├── logs
    │   └── runner.log
    └── output
        └── csv


## Input actually fed to libcbm

This is saved before the simulation start into a directory in output.
Example of this structure


    eu_cbm_data/output/reference/LU/0/input$ tree
    .
    ├── csv
    │   ├── age_classes.csv
    │   ├── classifiers.csv
    │   ├── disturbance_types.csv
    │   ├── events.csv
    │   ├── growth_curves.csv
    │   ├── inventory.csv
    │   └── transitions.csv
    └── json
        └── config.json

### libcbm csv input files

Each of the csv file can be explained in the technical report, or the calibration
report, or the CBM CFS3 technical documentation.


### JSON file

Defines several mappings.


- A mapping between dictionary keys and csv file location

        "events": {
            "type": "csv",
            "params": {
                "path": "/home/paul/repos/eu_cbm/eu_cbm_data/output/reference/LU/0/input/csv/events.csv"
            }




- A mapping between eco boundaries in our data and the eco boundaries names in the
Archive Index Database '(AIDB) also called "CBM defaults" now in libcbm.


- A mapping between disturbance types in our data and in the AIDB.


- A mapping between forest types (species) in our data in the AIDB for example

>       "species": {
>           "species_classifier": "forest_type",
>           "species_mapping": [
>               {
>                   "user_species": "Spruce (FI)",
>                   "default_species": "PA (FI)"
>               },
>               {
>                   "user_species": "Scots pine (FI)",
>                   "default_species": "PS (FI)"},
>               }

For example here, the `"user_species": "Scots pine (FI)"` maps to row 10 iof the file
`csv/classifiers.csv`

    2,PS,Scots pine (FI)

You will find the `"PS (FI)"` in the AIDB (also called CBM defaults) table `species_tr`.


# Post processing






