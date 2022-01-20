---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.13.4
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

# Introduction

## What is a specification

The purpose of this notebook is to draft the Harvest Allocation Tool (HAT) in the form of a software requirements specification.

Quotes from [the wikipedia page](https://en.wikipedia.org/wiki/Software_requirements_specification):

> "Software requirements specification establishes the basis for an agreement between customers and contractors or suppliers on how the software product should function [...]. Software requirements specification is a rigorous assessment of requirements before the more specific system design stages, and its goal is to reduce later redesign. It should also provide a realistic basis for estimating product costs, risks, and schedules."

> "The software requirements specification document lists sufficient and necessary requirements for the project development. To derive the requirements, the developer needs to have clear and thorough understanding of the products under development. This is achieved through detailed and continuous communications with the project team and customer throughout the software development process."

Other resources:

- Stack Overflow blog (2020) [A practical guide to writing technical specs](https://stackoverflow.blog/2020/04/06/a-practical-guide-to-writing-technical-specs/)

- Joel on software (2000) [Painless functional specifications part 1 Why bother?](https://www.joelonsoftware.com/2000/10/02/painless-functional-specifications-part-1-why-bother/)

The original draft of the specification was written in July 2021 found here: [eu_harvesting_allocation_tool.docx](../models/libcbm/eu_harvesting_allocation_tool_21072021.docx)

## Pool list

There is a finite number of carbon pools in the libcbm model. They are the following:

       'softwood_merch',              'softwood_foliage',
       'softwood_coarse_roots',       'softwood_fine_roots',
       'softwood_stem_snag',          'softwood_branch_snag',
       'softwood_other',
       'hardwood_merch',              'hardwood_foliage',   
       'hardwood_coarse_roots',       'hardwood_fine_roots',
       'hardwood_stem_snag',          'hardwood_branch_snag',
       'hardwood_other',
       'above_ground_very_fast_soil', 'below_ground_very_fast_soil',
       'above_ground_fast_soil',      'below_ground_fast_soil',
       'above_ground_slow_soil',      'below_ground_slow_soil'
       'co2', 'ch4', 'co', 'no2', 'medium_soil', 'products',

**Definitions**:

* **merch**: The merchantable standing stock is a collection of two pools within the CBM model. The merchantable stock is split into: `hardwood_merch` and `softwood_merch`. Every stand has one of these pools set to zero and the other pool increases at every time step based on a growth function.


## Pools and limitation

The libcbm-based reimplementation of CBM-CFS3 unfortunately is not flexible enough for the users to define their own additional pools. This is a pity because we require more pools than just `products`. We would need a pool for `products_irw` and another pool for `products_fw`. Since this is not possible, we are going to do our own accounting separately to track separate fuelwood and industrial roundwood fluxes.

Note that there is another version of `libcbm` that would allow one to add new pools, but it would require a complete reimplementation of other features present in CBM-CFS3 which we consider to be too time-consuming at this point. This is found in the codebase `libcbm_py` under the `moss` module.

**Definitions**:

* **irw**: Industrial round wood. It corresponds to a virtual pool that libcbm is unable to track, but that we will track. It should represent high quality wood, e.g. potential logs.

* **fw**: Firewood or fuelwood. It corresponds to a virtual pool that libcbm is unable to track, but that we will track. It should represent firewood and also other wood components used for combustion.

Unlike the other pools in `libcbm`, for our purposes, the virtual pools will not carry over from one year to another. In essence, they are set back to zero at every new timestep. We just need them to sum the fluxes going to them.


## Fluxes and limitation

The `libcbm` model does not report in its state variable the fluxes between pools that happen in a timestep. A simple dataframe with two columns `source_pool` (the 'origin pool') and `destination_pool` (the 'sink pool') simply does not exist. What the user can do to obtain information about fluxes, is to specify one or many flux aggregates that will then be tracked and reported by the model.

**Definitions**:

* A flux aggregate is a movement of one or several source pools to one or several destination pools.

* A simple flux has a single source pool and a single destination pool.

**Rules**:

* Every stand can only be disturbed by one disturbance event every timestep (limitation of libcbm).

* Every disturbance can be associated to one or many flux aggregates.

**Units**:

* Fluxes are expressed in tons of carbon per year.

* Pools are expressed in tons of carbon.


## Demand units

* The demand value is expressed as thousands of cubic meters under bark.

* The demand from the economic model can vary according to a scenario. Each economic scenario is placed in a different directory under `repos/libcbm_data/common/gftmx/reference/xyz.csv`.

* For every year and every country, there are two values. These two values are `demand_irw_vol` and `demand_fw_vol`.

* NB: The values that are fed into the economic model originate from the faostat forestry production data for the historical period.


## Historical period

The HAT mechanisms only apply to the `simulation_period`. In the `historical_period` all disturbances are predetermined in the repository `libcbm_data` and none are generated dynamically.

NB: The variable `sim_base_year` must remain flexible. It is defined in `country.py`.


## Definition of stands

A stand is described by:

• a unique combination of classifier
• age
• time since last disturbance and last dist id.

Each stand that is eligible (based on age rules and disturbance return interval)
has a potential maximum volume that generates movements from the
merchantable pool, snag pool and owc pool to the products pool.



## Disturbance target amount for measurement type M


Assumption concerning a single or multiple stands

(1) every disturbance would affect a single stand

(2) every disturbances affects several stands

--> HAT implements option 2. The age of stands information dissappears because HAT aggregates available volume accross unique classifiers and dist id before distributing the irw demand.

Now there are also several ways for a disturbance to work:

(A) If a disturbance asks for 10kg and ends up targeting several stands, take 10kg from each

(B) If a disturbance asks for 10kg and ends up targeting several stands, take 10kg in
    total while distributing evenly across all targets

(C) If a disturbance asks for 10kg and ends up targeting several stands, take 10kg in
    total from a specific one (the oldest one, or the youngest one)
    
--> HAT implements option C, we leave it to libcbm to choose the eligible stands accross the age range through the sort_rules.

This is further confounded by another ambiguity:

(X) When a disturbances asks for 10kg, does that mean 10kg of carbon taken evenly from all the pools of the stands?

(Y) When a disturbances asks for 10kg, does that mean 10kg of carbon taken from a
    specific pool? But there is no where in the disturbance file where you can specify a
    pool id, so is it the merchantable pool? And if so does it pick between
    hardwood_merch and softwood_merch automatically?

(Z) When a disturbances asks for 10kg, does that mean 10kg of carbon moved to a specific
    pool? But there is no where in the disturbance file where you can specify a pool id,
    so is it the products pool?

--> We checked in January 2022 and resolved the ambiguity. Option Z is taking place in the model. 

Note: The CBM user manual available at: https://cfs.nrcan.gc.ca/publications?id=39768
Defines the target amount of disturbances as such page 150 (page 176 of the pdf):

> "Target Amount Amount of area, amount of merchantable carbon, or proportion of records to disturb"

This is misleading for disturbances of type "M", because the actual target is the amount of **movements to the products pool**. We tested this and in addition to the merchantable pool, when we define movements from the standing snags pool or from the other wood components to the product pools, we observe that the requested amount is distributed across those pools.


# Simulation period run

## Disturbances

* `A`: Area. Always in hectares.
* `P`: Proportion of areas. Always in fractions of 1.
* `M`: Mass. Always in tons of carbon.

## Volume Limitation

Volume disturbances don't exist as far as the `libcbm` model is concerned.

Unfortunately, we can only know how much area and how much mass every stand contains as `libcbm` is volume blind. It's always up to us to convert between mass and volume amount, creating again the need to do our own accounting separately to the model.


## Iterative limitation

Unfortunately, the `libcbm` model does not update its state variables (stands, area, pools, etc.) in an iterative fashion. This means that once a disturbance is applied in a given year, its effects are not seen in the dataframes containing all the information about the forest's state until the current timestep is concluded. Only at the beginning of the next timestep, the results are finally visible in the user exposed variables (but it's too late to emit new disturbances).

This limits our ability to dynamically respond and adapt to events that happen in the same year (such as harvesting only what is missing to satisfy a given goal). To counter this we plan to use the function `cbm.what_if_end_here()` that does the same process of concluding the current timestep, albeit on a copy of the state, enabling us to retrieve the results that would normally be accessible only on the next year, while still remaining in the current year to emit new disturbances. This incurs a computational cost which is mostly negligible, while also incurring a small technical cost.


## The files `events.csv`

These files contain disturbances that occur in the historical period, but they can also contain disturbances that occur in the simulation period. For both the `historical` period and the `simulation` period, these disturbances can be of any type.

We will apply the `A`, `P` and `M` based disturbances from all of the `events.csv` input files for the current year first, before any dynamically generated disturbances are applied.

In essence, the ecological idea behind this structure is to have (in the first version of HAT) natural disturbances in the `events.csv` file, and anthropogenic disturbances generated dynamically.


## Ordering limitation

The `libcbm` implementation guarantees that one stand can only be disturbed once in every timestep. However, it doesn't conserve any ordering of disturbances, and internally sorts the list of events the user passes by the value of the default `dist_id` before applying them.

Happily, since the standing stock is usually an order of magnitude larger than the size of the natural or anthropogenic disturbances, we can consider that the order in which disturbances are applied is not important. Therefore, there will be no prioritization required among the types of disturbances in their application. There will be a defined order however concerning their creation.


## Track fluxes

We want to track the fluxes from the following pools going to the `products` (tons of carbon) pool:

    'softwood_merch', 'softwood_other', 'softwood_stem_snag', 'softwood_branch_snag',
    'hardwood_merch', 'hardwood_other', 'hardwood_stem_snag', 'hardwood_branch_snag',

NB: In the file `notebooks/libcbm/aidb_dist_matrices.md` we illustrate the absence of movements from branch snags to the products pool. However, there is a movement to the `co2` pool (this might be a hack?).

The aggregated fluxes from each of the source pools of interest to the `products` pool are: 

- `softwood_merch_to_product`
- `softwood_other_to_product`
- `softwood_stem_snag_to_product`
- `softwood_branch_snag_to_product`
- `hardwood_merch_to_product`
- `hardwood_other_to_product`
- `hardwood_stem_snag_to_product`
- `hardwood_branch_snag_to_product`


## The files `irw_demand.csv` and `fw_demand.csv`

We load demand targets from the files `irw_demand.csv` and `fw_demand.csv` for the given scenarios specified in a combination. The demand for each time step is contained in various demand files originating from the economic model called Global Forest Trade Model (GFTM). Currently, the files are in `libcbm_data/demand/scenario_name/` and are named `irw_demand.csv` or `fw_demand.csv`.


## Determine remaining demand

We would like to determine the remaining demand for both types of wood/demand: `remaining_irw_vol` and `remaining_fw_vol`.

To do this we must start tracking fluxes in the current year (that were generated by `events.csv`) to calculate the numeric contents of our two missing virtual pools. In effect, we decide that some fluxes are split between the two pools while others are entirely going to only one pool.

To determine the proportion of fluxes going to both virtual pools we need to load the file `irw_frac_by_dist.csv`.

To know how much goes to `products_irw_tc` and how much goes to `products_fw_tc` we need to know flux amounts by:

* The classifiers.
* The disturbance type (`generic_50`, `clearcut_slash` etc.).
* The source pool (`softwood_merch`, `hardwood_other`, etc.).

The destination pool is not important here because it is always `products_tc`.


## The file `irw_frac_by_dist.csv`

Therefore, we load the file `irw_frac_by_dist.csv` which has columns:

     scenario,classifier_1,...,classifier_8,dist_type_id,dist_type_name,source_1,source_2,...,source_8

The values contained in each row `source_x` are the fraction going to `products_irw`. Hence, one minus that number is what goes to `products_fw`.

QA/QC procedure: both of the columns "dist_type_id", "dist_type_name" have to be internally consistent.


## The file `vol_to_mass_coefs.csv`

To determine the proportions actually going to the `products_irw_tc` or `products_fw_tc` pools we will also consider coefficients such as the bark fraction, so that the `products_irw_tc` virtual pool does not end up containing any of the carbon that was considered part of the tree's bark. Indeed, `libcbm` does not track this and includes bark by default with no option to turn it off.
 
The wood density and the bark factor are variable according to `classifier_5` called `forest_type`  which indicates the main tree species. This information is found in the file `vol_to_mass_coefs.csv`. This file has columns:

    forest_type, wood_density, bark_frac
    PA,         400,           0.15

## The subtraction

The values are obtained by sum, volume conversion and subtraction using the files listed above:

```python
    remaining_irw_vol = demand_irw_vol - sum(flux_products_tc * frac_irw * (1 - bark_frac) / (0.49 * wood_density))
    remaining_fw_vol  = demand_fw_vol  - sum(flux_products_tc * frac_fw  * (1 - bark_frac) / (0.49 * wood_density))
```

If nothing is specified in a variable name, we assume volume in cubic meters as a unit. Mass amounts need to be specified in the variable name with the suffix `_tc`.


## Create disturbances with `events_templates.csv`

If both the values of `remaining_irw` and `remaining_fw` are negative then we don't provide any extra disturbances for the current time step. Otherwise, if `remaining_irw` is positive then we create new disturbances dynamically to satisfy it. The satisfaction of `remaining_fw` occurs last.

Disturbances that create `products_irw` fluxes will always create `products_fw` fluxes simultaneously. These disturbances are recognized by having `product_created` == `irw_and_fw`. Later when we want to satisfy `products_fw` we will use only disturbances with `product_created` == `fw_only`.

Every single stand in the total standing stock can only be affected by maximum one of the disturbances defined in `events_templates`. This file contains disturbance templates which are not specified in terms of `M`, `A` or `P`, because the disturbances generated by HAT are always in tons of carbon. In other words, to create a concrete disturbance one will always specify `M` for `measurement_type`.

Indeed, any given predefined disturbance template is only applied to a specific set of classifiers and age range, as well as a `min_since_last`, ensuring that for every stand only one or zero disturbances can affect them.

(We could potentially do a quality assurance computation here.)

The `events_templates.csv` has almost the same columns as `events.csv`.

* In addition to the `scenario`, `product_created`, `dist_interval_bias`, and `dist_type_name` columns.
* And without the `measurement_type`, `amount`, `timestep` columns.

Resulting in:

    scenario,classifier_1,...,classifier_8,product_created,dist_interval_bias,[using_id,...,efficiency]

The name of the disturbance is useless and removed after loading.

## Join and filter

We are ready to join the dataframe from `events_templates.csv` with the dataframe from `cbm.results.pools` (obtained hopefully from `cbm.what_if_end_here()`).

* Every row in "event_templates" is expected to have at least one matching stand in the current "inventory". The opposite is not true, every row in "inventory" does not have to have a match in "events_template". Hence, some stands are left for conservation or biodiversity purposes.

* The column `min_since_last` require a special treatment, one should filter entries that do not match the criteria `time_since_last < min_since_last`.

* Same goes for the age range, via the columns `min_age`, `max_age`.


## Custom fractions of eligible stock

New disturbances should be distributed onto the standing stock in the proportion of availability.

To accomplish this, the strategy is to take all stands that are still eligible and virtually disturb them in their entire area to determine how much volume `products_irw_vol` would be produced (hypothetically, without actually applying any disturbance).

To do this we have to retrieve the corresponding disturbance matrices based on the `dist_type` column, and extract the vector that contains the fluxes in tons of carbon going towards the products pool. In addition, we need to join with the dataframe `irw_frac_by_dist.csv` to determine how much goes to the virtual `products_irw_tc`.

We would thus obtain an entry for every stand here for an imagined `harvest_vol` of 200:

    stand_id,silv_dist,potential_irw,frac_irw,harvest_vol
    1,7,98880000,0.7,140
    2,None,0,0
    3,16,1655500,0.3,60
    
Where `frac_irw` is the normalization of `potential_irw` and `harvest_vol` is `remaining_irw` multiplied by `frac_irw`.

With this system, every disturbance in the file `events_templates.csv` will be applied at every timestep (unless there are no stands eligible for a given disturbance).

In addition, we decide to divide the `potential_irw` by the column `dist_interval_bias` in order to favor species that can be cut often.


## The file `harvest_factors.csv`

Once this dataframe is generated we will update the columns `frac_irw` (and of course `harvest_vol`) based on an additional market factor found in `harvest_factors.csv`. This file has different values for every timestep and for the classifiers `forest_type` and `region` and `management_type`. Example structure of the csv file:

    scenario,product_created,forest_type,mgmt_type,dist_type_id,value_2020,...,value_2100
    historical,irw_and_fw,10,FS,broad,8,1,1,...,1
    historical,fw_only,11,QA,con,2,1,1,...,1

Whatever information is supplied here is in effect additional information to the event templates. We simply use a separate file because we want the harvest modification factor to be time dependent.

As long as all classifier combinations are specified in `harvest_factors.csv` we can safely join it with the dataframe produced above, after normalizing columns `value_x` so that they sum to one. Finally, multiplying column `frac_irw` with column `value_x` and normalizing the result. Finally, updating column `harvest_vol`.

Later, we would like to conserve in the output the values of stock before applying the harvest factors. This can be post-computed on the output.


## Satisfying both demands

We always satisfy `remaining_irw` fully even if it causes an overflow of `remaining_fw`.

Finally, if `remaining_fw` is still positive after satisfying `remaining_irw`, we satisfy it, by using disturbances that only produce fluxes towards `products_fw`. In this manner an overflow in `remaining_irw` can only be generated by predetermined disturbances in `events.csv` never by dynamically generated disturbances.


## Unsatisfied disturbances

If a requested disturbance is not completed by the model, we raise a silenceable Exception.


# Output to be reported

We would like to record the values `remaining_irw` and `remaining_fw` for every year in a separate file. In addition, we want to report the values that intervene in this subtraction. This means 6 scalars per year.

Also, in order to later modify the file `harvest_factors.csv`, we would like to have the `irw_vol` stock distribution over all stands previous to the application the market bias factor.


# Future

Salvage logging can be limited by the fact that a stand can only be disturbed once by timestep, requiring the creation of disturbance combinations, directly in the AIDB instead of dynamically.
