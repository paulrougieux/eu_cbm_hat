"""The core components of the model are: `eu_cbm_hat.core.country`,
`eu_cbm_hat.core.continent` and `eu_cbm_hat.core.runner`. A runner is
associated to one country and runs the model for a specific combination of
input files called a scenario combination. The continent object contains a
dictionary of all scenario combinations documented at  `eu_cbm_hat.combos`. The
continent and scenario combination objects can be used together to create a
runner object for the test country `ZZ` as follows:

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['hat'].runners['ZZ'][-1]
"""
