"""Functions to select HWP scenario objects part of the post processor

- Select a harvest wood product (HWP) scenario along with options for
  recycling, and trade assumptions. Returns a configured `post_processor.hwp`
  object for downstream simulation and result comparison.

- The substitution is performed in an post_processor/hwp_substitution.py An
  extra function that is independent of the post_processor hwp object and returns
  a data frame for comparison purposes.
     - def compute_substitution(runner, subst_scenario)
     - def compare_substitution(df_ref, df)


"""
from typing import Optional, Union
from eu_cbm_hat.core.continent import continent

def select_hwp_scenario(
    iso2_code: str,
    forest_mgmt_scenario: str,
    hwp_frac_scenario: str,
    n_years_dom_frac: int,
    no_export_no_import: bool,
    recycling: bool = True,
):
    """
    Select a harvest wood product (HWP) scenario along with options for recycling,
    and trade assumptions. Returns a configured `post_processor.hwp`
    object for downstream simulation and result comparison.

    Substitution should be run by compare_substitution in a next step.

    Parameters
    ----------
    iso2_code : str
        Two-letter ISO2 country code (e.g., "LU" for Luxembourg).
    forest_mgmt_scenario : str, optional
        Name of the forest management scenario (e.g., "reference", "intensive",
        etc.). It is a combo name used to select the corresponding runner for
        the given scenario combination runner in `continent.combos`.
    hwp_frac_scenario : str, optional
        Name of the HWP fraction scenario (e.g., "default", "more_sw").
        Defines allocation rules for harvested wood products.
    n_years_dom_frac : int, optional
        Number of years of historical domestic fraction data to be used for
        estimating HWP flow shares.
    no_export_no_import : bool, optional
        If True, sets all import/export correction factors to unity, effectively
        disabling cross-border trade effects in HWP estimations.
    recycling : bool, default=True
        If True, includes recycling processes in the HWP model.
        Representation may depend on the underlying implementation.

    Returns
    -------
    hwp : post_processor.hwp
        A configured HWP post-processor object with the chosen scenario settings.

    Examples
    --------
    Select two different HWP scenarios and compare outputs:

    >>> from eu_cbm_hat.post_processor.select_hwp_scenario import select_hwp_scenario
    >>> # Reference scenario
    >>> hwp_ref_frac = select_hwp_scenario(
    ...     iso2_code="LU",
    ...     forest_mgmt_scenario="reference",
    ...     hwp_frac_scenario="default",
    ...     n_years_dom_frac=3,
    ...     no_export_no_import=False,
    ...     recycling=True,
    ... )
    >>> # Scenario with more sawnwood allocation
    >>> hwp_more_sw = select_hwp_scenario(
    ...     iso2_code="LU",
    ...     forest_mgmt_scenario="reference",
    ...     hwp_frac_scenario="more_sw",
    ...     n_years_dom_frac=3,
    ...     no_export_no_import=False,
    ...     recycling=True,
    ... )
    >>> # Compare intermediate tables
    >>> print(hwp_ref_frac.prod_from_dom_harv_sim)
    >>> print(hwp_more_sw.prod_from_dom_harv_sim)
    >>> # Compare HWP sink results
    >>> print(hwp_ref_frac.stock_sink_results)
    >>> print(hwp_more_sw.stock_sink_results)

    In a further step you can compare 2 substitution scenarios with
    `compare_substitution`().

    """
    # Select the post processor HWP object
    hwp = continent.combos[forest_mgmt_scenario].runners[iso2_code][-1].post_processor.hwp
    # Define properties
    hwp.hwp_frac_scenario = hwp_frac_scenario
    hwp.n_years_dom_frac = n_years_dom_frac
    # Add recycling information or not
    hwp.add_recycling = recycling
    # Set export import factors to one
    hwp.no_export_no_import = no_export_no_import
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
    df["forest_mgmt_scenario"] = hwp.runner.combo.short_name
    # Place the last column first
    cols = df.columns.to_list()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]
    return df



