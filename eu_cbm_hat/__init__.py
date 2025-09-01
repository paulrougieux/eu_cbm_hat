#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair, Paul Rougieux and Viorel Blujdea.

JRC Biomass Project.
Unit D1 Bioeconomy.


# Introduction

This documentation describes EU-CBM-HAT an adaptation of the Carbon Budget
Model (CBM) for EU countries, with the addition of a Harvest Allocation Tool
(HAT). `eu_cbm_hat` is a python package that enables the assessment of forest
CO2 emissions and removals under scenarios of forest management, natural
disturbances and forest-related land use changes. For more information on the
structure of the model and the research questions that have been analysed see
the section on related publication below.

EU-CBM-HAT depends on a software library called
[libcbm](https://github.com/cat-cfs/libcbm_py). libcbm was developed and is
maintained by the Forest carbon accounting team of Natural Resources Canada.
The `eu_cbm_hat` package was developed on top of this library by the Joint
Research Centre (JRC) of the European Commission to add capabilities such
as: scenario processing, a data structure for EU counties, a harvest allocation
tool, growth modification and estimates of the harvested wood products sink.
eu_cbm_hat is publicly available on the python package index at
[https://pypi.org/project/eu-cbm-hat](https://pypi.org/project/eu-cbm-hat). The
source code is available openly on
[https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat](https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat)
and the documentation you are currently reading is available at
[https://bioeconomy.gitlab.io/eu_cbm/eu_cbm_hat/eu_cbm_hat.html](https://bioeconomy.gitlab.io/eu_cbm/eu_cbm_hat/eu_cbm_hat.html).


There are 3 ways to run the model:

1. Using a [runner](eu_cbm_hat/core/runner.html) created from simulation tools
  in the [core](eu_cbm_hat/core.html) directory. This runner has been developed
  since 2019. It requires a comprehensive data structure for EU countries to be
  defined in an eu_cbm_data directory. An example of the directory structure is
  visible in the test subdirectory for a fictitious country called ZZ.

2. Using a smaller runner called a [bud]() object. This approach has been added
  in 2025. A bud is a  much simpler object that feeds a simpler data directory to
  libcbm. It can use the same post-processor methods as the runner.

3. Using another runner called crcf made for the simulations of Carbon Removal and
  Carbon Farming. Introduced in 2025, this is not documented yet. See the source
  code in the crcf directory.


# Common methods used by all runner types

- Paths to data directories are defined in
  [constants](eu_cbm_hat/constants.html). Other variables necessary for
  computations such as the carbon fraction of biomass are also defined there.

- During the libcbm simulation time step, various modifications can be made to
  the growth or disturbances:

    - The Harvest Allocation Tool implemented in [cbm.dynamic](eu_cbm_hat/cbm/dynamic.html)
      provides the capability for dynamic disturbance allocation depending on the
      evolution of the stock. It also deals with salvage logging after natural
      disturbances.

    - [cbm.climate_growth_modifier](eu_cbm_hat/cbm/climate_growth_modifier.html)
      can modify forest growth at each time step in order to simulate the impact
      of climate variables such as draught on forest growth. The input data for
      this is derived from NPP measures or simulations.

- The [post_processor](eu_cbm_hat/post_processor.html) transforms CBM output
  fluxes and pools tables into final result tables.

    - [sink](eu_cbm_hat/post_processor/sink.html) computes the carbon sink in
      tons of CO2 equivalent

    - [stock](eu_cbm_hat/post_processor/stock.html) computes stock indicators

    - [hwp](eu_cbm_hat/post_processor/hwp.html) estimates Harvested Wood
      Products inflows and outflows to compute the HWP sink.


# Runner methods

- Scenario combinations are defined as `.yaml` files in `eu_cbm_data/combos`.
  When initiating a runner, the content of its yaml file is loaded in
  [eu_cbm_hat.combos](eu_cbm_hat/combos.html). It defines the scenario used for
  all input files. Some input files can change scenario every year, other files
  are defined for the entirety of the simulation length.

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


# Bud methods

[Bud]() is a small self contain runner-type object to run libcbm by pointing it to an input
data directory and an AIDB. It is a small self contained object that makes it
possible to run the libcbm model and the EU-CBM-HAT post processor (to compute
sink output for example) without the need for the EU-wide
eu_cbm_data directory.

The data is processed by sub modules:

- [input_data](eu_cbm_hat/bud/input_data.html) prepares the input data for libcbm.

- [output](eu_cbm_hat/bud/output.html) handles the output data.

- The output data is further processed in the [bud
  post_processor](eu_cbm_hat/bud/post_processor.html) which inherits all methods
  from the main [post_processor](eu_cbm_hat/post_processor.html), for example
  methods to compute the stock, sink and hwp mentioned in the common methods
  section above.


# CRCF methods

Runner made for simulations of Carbon Removal and Carbon Farming. This type of
object is not documented yet. Look at the source code in the crcf directory.


# Related Publications

In chronological order.

- Kurz WA, Dymond CC, White TM, Stinson G, Shaw CH, Rampley GJ, Smyth C,
  Simpson BN, Neilson ET, Trofymow JA, Metsaranta J. **CBM-CFS3: a model of
  carbon-dynamics in forestry and land-use change implementing IPCC standards**.
  Ecological modelling. 2009 Feb 24;220(4):480-504.
  https://doi.org/10.1016/j.ecolmodel.2008.10.018

  - This is the main publication describing the Carbon Budget Model structure.
    It is a previous version called CBM-CFS3.


- Roberto Pilli, Giacomo Grassi, Werner A. Kurz, Carolyn E. Smyth, Viorel
  Blujdea, **Application of the CBM-CFS3 model to estimate Italy's forest carbon
  budget, 1995–2020,** Ecological Modelling, Volume 266, 2013, Pages 144-171,
  ISSN 0304-3800, https://doi.org/10.1016/j.ecolmodel.2013.07.007.

    - This paper used a previous version called CBM-CFS3. Figure 3 in the paper
      explains the need to switch from an init (historical) growth period to a
      current growth period. The
      [Simulation.switch_period](eu_cbm_hat/cbm/simulation.html#Simulation.switch_period)
      method changes the growth period from "Init" to "Cur". As a result all
      stands will have the value "Cur" for the growth_period classifier from
      inventory start year onwards. Note the inventory start year is stored in
      `runner.country.inventory_start_year` and defined in
      [Country.set_years](eu_cbm_hat/core/country.html#Country.set_years).

- Pilli, Roberto, Blujdea, Viorel N.B., Rougieux, Paul, Grassi, Giacomo,
  Mubareka, Sarah Betoul, 2024 Volume, increment, and aboveground biomass data
  series and biomass conversion and expansion factors for the main forest types
  of EU Member States Annals of Forest Science This collection reports the
  standing stock volume, increment, aboveground biomass, and biomass conversion
  and expansion factors attributed to 222 forest types and 48 different
  management types, representative of 25 EU Member States. Dataset
  https://zenodo.org/records/11387301. Article
  https://doi.org/10.1186/s13595-024-01256-5

- Blujdea, V., Rougieux, P., Sinclair, L., Morken, S., Pilli, R., Grassi, G.,
  Mubareka, S. and Kurz, W., **The JRC Forest Carbon Model: description of
  EU-CBM-HAT**, EUR 31299 EN, Publications Office of the European Union,
  Luxembourg, 2022, ISBN 978-92-76-58867-2, doi:10.2760/244051, JRC130609.
  https://publications.jrc.ec.europa.eu/repository/handle/JRC130609

- Pilli, R., Blujdea, V.N., Rougieux, P., Grassi, G. and Mubareka, S.B., **The
  calibration of the JRC EU Forest Carbon Model within the historical period 2010 - 2020**,
  Publications Office of the European Union, Luxembourg, 2024,
  doi:10.2760/222407, JRC135639. https://dx.doi.org/10.2760/222407

- Rougieux, P., Pilli, R., Blujdea, V., Mansuy, N. and Mubareka, S.B.,
  **Simulating future wood consumption and the impacts on Europe`s forest sink to
  2070**, Publications Office of the European Union, Luxembourg, 2024,
  doi:10.2760/17191, JRC136526.
  https://publications.jrc.ec.europa.eu/repository/handle/JRC136526


"""

# Special variables
__version__ = "2.1.0"

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
