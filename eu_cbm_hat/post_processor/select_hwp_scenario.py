"""Functions to select HWP scenario objects part of the post processor

TODO_1: Define how to add "recycling" and "substitution" arguments to the select_hwp_scenario method.

TODO_2: IF POSSIBLE: Thse are hardcoded and maybe we should pass them as arguments to the select_hwp_scenario method. 
        Define how to add following arguments to the select_hwp_scenario method:  
        
        # # Number of common years to be used to compute the fractions of semifinished to logs
        self.n_years_dom_frac = 3
        # Add recycling information or not
        self.add_recycling = True
        # Set export import factors to one
        self.no_export_no_import = False

- Currently the "recycling" scenario changes the  recycled_wood_factor and
  recycled_paper_factor based on the same scenario column called
  hwp_frac_scenario, the same as the hwp_frac scenario. So this is redundant
  with the hwp_frac argument.

- The susbtitution is performed in an extra function that is independent of
  the post_processor hwp object and returns a data frame for comparison purposes.

"""
from eu_cbm_hat.core.continent import continent

def select_hwp_scenario(
    iso2_code,
    forest_mngm_scenario="reference",
    hwp_frac_scenario="default"):
    """Select a scenario combination, HWP scenario, recycling and susbstitution
    scenario n and return a post_processor.hwp object.

    For example compare scenarios results and also display intermediate
    computation tables:

        >>> from eu_cbm_hat.post_processor.select_hwp_scenario import select_hwp_scenario
        >>> # Select scenarios
        >>> hwp_refd = select_hwp_scenario(iso2_code="LU", combo="reference", hwp_frac="default")
        >>> hwp_more_sw = select_hwp_scenario(iso2_code="LU", combo="reference", hwp_frac="more_sw")
        >>> # Intermediate tables
        >>> print(hwp_refd.prod_from_dom_harv_sim)
        >>> print(hwp_more_sw.prod_from_dom_harv_sim)
        >>> # Print results
        >>> print(hwp_refd.stock_sink_results)
        >>> print(hwp_more_sw.stock_sink_results)

    """

    if forest_mngm_scenario is None:
        forest_mngm_scenario="reference",
    if hwp_frac_scenario is None:
        hwp_frac_scenario ="default"
    # Select the post processor HWP object
    hwp = continent.combos[forest_mngm_scenario].runners[iso2_code][-1].post_processor.hwp
    # Define properties
    hwp.hwp_frac_scenario = hwp_frac_scenario
    return hwp


def stock_sink_results(**kwargs):
    """Result data frame for the given scenario combination and HWP scenario.

    Return the output data frame of the stock_sink_results method. Add the name
    of all scenarios as a column name.

    For example compare results tables:

        >>> from eu_cbm_hat.post_processor.select_hwp_scenario import stock_sink_results
        >>> hwp_refd = stock_sink_results(iso2_code="LU", combo="reference", hwp_frac="default")
        >>> hwp_more_sw = stock_sink_results(iso2_code="LU", combo="reference", hwp_frac="more_sw")

    """
    hwp = select_hwp_scenario(**kwargs)
    df = hwp.stock_sink_results
    df["forest_mngm_scenario"] = hwp.runner.combo.short_name
    # Place the last column first
    cols = df.columns.to_list()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]
    return df



