#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair, Paul Rougieux and Viorel Blujdea.

JRC Biomass Project.
Unit D1 Bioeconomy.


# Introduction

There are 3 ways to run the Carbon Budget Model with eu_cbm_hat:

1. Using a [runner](eu_cbm_hat/core/runner.html) created from simulation tools
  in the [core](eu_cbm_hat/core.html) directory. This runner has been developed
  since 2019. It requires a comprehensive data structure for EU countries to be
  defined in an eu_cbm_data directory. An example of the directory structure is
  visible in the test subdirectory for a fictitious country called ZZ.

2. Using a smaller runner called a [bud]() object. This approach has been added
  in 2025. A bud is a  much simpler object that feeds a simpler data directory to
  libcbm. It can use the same post-processor methods as the runner.

3. Using another runner called crcf made for the simulations of Carbon Removal and
  Carbon Farming.. Introduced in 2025, this is not documented yet. See the source
  code in the crcf directory.


# Common methods used by all runner types

- Paths to data directories are defined in
  [constants](eu_cbm_hat/constants.html). Other variables necessary for
  computations such as the carbon fraction of biomass are also defined there.

- The [post_processor](eu_cbm_hat/post_processor.html) transforms CBM output
  fluxes and pools tables into final result tables.

    - [sink](eu_cbm_hat/post_processor/sink.html) computes the carbon sink in
      tons of CO2 equivalent

    - [stock](eu_cbm_hat/post_processor/stock.html) computes stock indicators

    - [hwp](eu_cbm_hat/post_processor/hwp.html) estimates Harvested Wood
      Products inflows and outflows to compute the HWP sink.


# Runner methods

- A runner processes data in several steps.

    - [orig_data](eu_cbm_hat/info/orig_data.html) contains the original data
      for a country. There are many scenarios for inventory, growth (yield), and
      disturbances.

    - [aidb](eu_cbm_hat/info/aidb.html) contains the Archive Index Database
      (with soil parameters and biomass expansion factors)

    - [input_data](eu_cbm_hat/info/input_data.html) contains the actual input
      data sent to libcbm for one and only one combination of scenarios.

    - [output_data](eu_cbm_hat/info/output_data.html) contains the output
      fluxes and pools after the libcbm simulation run.

    - The ouput data is then used by the
      [post_processor](eu_cbm_hat/post_processor.html) see below.

- During the simulation time step, various modifications can be made to the growth or disturbances:

    - The Harvest Allocation Tool implemented in [cbm.dynamic](eu_cbm_hat/cbm/dynamic.html)
      provides the capability for dynamic disturbance allocation depending on the
      evolution of the stock. It also deals with salvage logging after natural
      disturbances.

    - [cbm.climate_growth_modifier](eu_cbm_hat/cbm/climate_growth_modifier.html)
      can modify forest growth at each time step in order to simulate the impact
      of climate variables such as draught on forest growth. The input data for
      this is derived from NPP measures or simulations.

- Scenario combinations are loaded in
  [eu_cbm_hat.combos](eu_cbm_hat/combos.html). They are defined as `.yaml` files
  in `eu_cbm_data/combos`.


# Bud methods

[Bud]() is a small self contain runner-type object to run libcbm by pointing it to an input
data directory and an AIDB. It is a small self contained object that makes it
possible to run the libcbm model and the EU-CBM-HAT post processor (to compute
sink output for example) without the need for the EU-wide
eu_cbm_data directory.

The data is processed in these steps:

- [input_data](eu_cbm_hat/bud/input_data.html)

- [output](eu_cbm_hat/bud/output.html)

- further processed in the [bud
  post_processor](eu_cbm_hat/bud/post_processor.html) which inherits all methods
  from the main [post_processor](eu_cbm_hat/post_processor.html), for example
  methods to compute the stock, sink and hwp mentioned in the common methods
  section above.


# CRCF methods

Runner made for simulations of Carbon Removal and Carbon Farming. This type of
object is not documented yet. Look at the source code in the crcf directory.


"""

# Special variables
__version__ = "2.0.1"

# Import constants first (no circular dependency)
from eu_cbm_hat.constants import (
    project_name,
    project_url,
    CARBON_FRACTION_OF_BIOMASS,
    module_dir,
    module_dir_pathlib,
    repos_dir,
    git_repo,
    eu_cbm_data_dir,
    eu_cbm_data_pathlib,
    eu_cbm_aidb_dir,
    eu_cbm_aidb_pathlib,
)


# Lazy import mechanism - only imports when actually accessed
def __getattr__(name):
    if name == "Bud":
        from eu_cbm_hat.bud import Bud

        return Bud
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "bud",
    "cbm",
    "combos",
    "constants",
    "core",
    # Don't include "crcf" because it depends on `eu_cbm_crl`
    # which is not available.
    "info",
    "launch",
    "plot",
    "post_processor",
    "pump",
    "qaqc",
    "tests",
]
