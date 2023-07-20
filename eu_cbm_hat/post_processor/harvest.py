"""The purpose of this script is to compare expected and provided harvest

- Get expected harvest from the economic model
- Get provided harvest from the fluxes to products



Compute expected provided for total roundwood demand, as the sum of IRW and FW.

Usage:

    from eu_cbm_hat.core.continent import continent
    runner = continent.combos['reference'].runners['ZZ'][-1]
    runner.output["flux"]


"""

import pandas
from eu_cbm_hat.info.harvest import combined

def harvest_demand(selected_scenario:str)->pandas.DataFrame:
    """Get demand using eu_cbm_hat/info/harvest.py

    Usage:

        >>> from eu_cbm_hat.post_processor.harvest import harvest_demand
        >>> harvest_demand("pikfair")

    """
    irw = combined["irw"]
    irw["product"] = "irw_demand"
    fw = combined["fw"]
    fw["product"] = "fw_demand"
    df = pandas.concat([irw, fw]).reset_index(drop=True)
    index = ['scenario', 'iso2_code', 'year']
    df = df.pivot(index=index, columns="product", values="value").reset_index()
    df["rw_demand"] = df["fw_demand"] + df["irw_demand"]
    df = df.rename_axis(columns=None)
    return df.loc[df["scenario"] == selected_scenario]


def harvest_provided_one_country(combo_name, iso2_code):
    """Harvest provided in one country"""


def harvest_provided_all_countries(combo_name):
    """Harvest provided in all countries"""


def harvest_expected_provided(combo_name)

# Copied from Viorel's Notebook at
# https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_explore/-/blob/main/output_exploration/supply_vs_demand_total_volume.ipynb


# select only the identifiers which show fluxes to production
# fluxes_clean = fluxes.loc[(fluxes['softwood_merch_to_product']>0) |
#                           (fluxes['hardwood_merch_to_product']>0) |
#                      (fluxes['softwood_stem_snag_to_product']>0) |
#                      (fluxes['hardwood_stem_snag_to_product']>0) |
#                      (fluxes['softwood_other_to_product']>0) |
#                      (fluxes['hardwood_other_to_product']>0) |
#                      (fluxes['hardwood_branch_snag_to_product']>0) |
#                      (fluxes['hardwood_branch_snag_to_product']>0) ]
# 
# # area subject to disturbances which provide harvest for the calibration period
# fluxes_clean.iloc[[0,-1]]

#  convert C to volumes
# volume_flux =  fluxes_clean.merge(wd_coefs_data,
#                                   how = 'inner',
#                                   on=['forest_type','con_broad'])
# 
# # correct cbm output to underbark, get total volume_ub to prod,
# volume_flux ['volume_to_prod'] = 1/(1+ volume_flux  ['bark_frac']) * 2 * volume_flux  ['total_flux_cs']/volume_flux ['wood_density']
# 
# # per_ha vol to prod
# volume_flux ['volume_to_prod_per_ha'] = 1/(1+ volume_flux  ['bark_frac']) * 2 * volume_flux  ['tc_per_ha']/volume_flux ['wood_density']
# 
# len(volume_flux)#.iloc[[1,-1]]
