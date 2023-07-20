"""The purpose of this script is to compare expected and provided harvest

- Get expected harvest from the economic model
- Get provided harvest from the fluxes to products

"""







# select only the identifiers which show fluxes to production

fluxes_clean = fluxes.loc[(fluxes['softwood_merch_to_product']>0) |
                          (fluxes['hardwood_merch_to_product']>0) |
                     (fluxes['softwood_stem_snag_to_product']>0) |
                     (fluxes['hardwood_stem_snag_to_product']>0) |
                     (fluxes['softwood_other_to_product']>0) |
                     (fluxes['hardwood_other_to_product']>0) |
                     (fluxes['hardwood_branch_snag_to_product']>0) |
                     (fluxes['hardwood_branch_snag_to_product']>0) ]

# area subject to disturbances which provide harvest for the calibration period
fluxes_clean.iloc[[0,-1]]
