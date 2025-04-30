"""Compare substitution scenarios

Note: see the distinction between a scenario combo and a subst_scenario in the
documentation further down below.
"""

import re
from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input


def compute_substitution(runner, subst_scenario):
    """Substitution scenarios with a reference and a comparison point

     Merge with the data from steel, cement and other materials.

     See the documentation of the compare_substitution function for how to
     compute the difference between the two substitution data frames.
    """

    # Load inflows
    df = runner.post_processor.hwp.build_hwp_stock_since_1990.copy()
    selected_cols = ["year", "sw_inflow", "wp_inflow", "pp_inflow"]
    df = df[selected_cols]
    # Load split data
    split_wp = hwp_common_input.split_wood_panels.copy()
    # Keep data for the selected country
    selector = split_wp["area"] == runner.country.country_name
    split_wp = split_wp.loc[selector]
    if not len(split_wp) == 1:
        msg = "There should not be more than one value for split_wp\n"
        msg += f"{split_wp}"
        raise ValueError(msg)
    # Split wood panels
    df["wp_fb_inflow"] = df["wp_inflow"] * split_wp["fwp_fibboa"].iloc[0]
    df["wp_pb_inflow"] = df["wp_inflow"] * split_wp["fwp_partboa"].iloc[0]
    # Rename the original inflow columns
    df.rename(columns=lambda x: re.sub(r"inflow", "inflow_0", x), inplace=True)
    # Load substitution parameters
    subst_params = hwp_common_input.subst_params.copy()
    selector = subst_params["subst_scenario"] == subst_scenario
    selector &= subst_params["country"] == runner.country.country_name
    subst_params_ref = subst_params.loc[selector]
    # Merge with substitution parameters
    df = df.merge(subst_params_ref, on="year", how="left")
    # Estimate the avoidance by substitution in wp based substitutes
    cols = subst_params_ref.columns
    frac_cols = cols[cols.str.contains("frac")]
    factor_cols = cols[cols.str.contains("factor")]
    # Check whether all fractions have a corresponding substitution factor
    f_check = [x.replace("frac", "subst_factor") for x in frac_cols]
    missing_factor_cols = set(f_check) - set(factor_cols.to_list())
    if missing_factor_cols:
        msg = "Some fraction columns do not have a corresponding factor column\n"
        msg += f"{missing_factor_cols}"
        raise ValueError(msg)

    # Add fuel wood inflows
    df_fw = runner.post_processor.hwp.ghg_emissions_fw
    col_map = {"tc_primary_fw": "fw_primary_inflow_0",
               "tc_secondary_fw": "fw_secondary_inflow_0"}
    df_fw.rename(columns=col_map, inplace=True)
    df = df.merge(df_fw[["year"] + list(col_map.values())], on="year", how="left")

    # For the substitution we consider only the secondary fuel wood
    for x in ["wp_pb", "wp_fb", "sw", "pp", "fw_primary", "fw_secondary"]:
        # Find which fractions are available for this product
        selected_frac_cols = frac_cols[frac_cols.str.contains(x)].to_list()
        # Create the inflow based on the available fractions and factors
        for frac in selected_frac_cols:
            new_inflow = frac.replace("frac", "inflow")
            factor = frac.replace("frac", "subst_factor")
            df[new_inflow] = df[f"{x}_inflow_0"] * df[frac] * df[factor]

    return df


def compare_substitution(df_ref, df):
    """Compare the substitution data frame to a reference data frame

    1. Compute the difference between the substitution scenario  and the reference
    2. Aggregate and sUm up values

    There is a distinction between :
        - a scenario combination when running CBM here the combos are called "reference" and "other_combo"
        - a HWP scenario here the subst_scenario arguments are called "reference" and "substitution"

    Example compute the difference between two HWP scenarios called "reference"
    and "substitution" between two different scenario combinations called
    "reference" and "other_combo" :

        >>> from eu_cbm_hat.core.continent import continent
        >>> from eu_cbm_hat.post_processor.hwp_substitution  import compare_substitution
        >>> from eu_cbm_hat.post_processor.hwp_substitution  import compute_substitution
        >>> runner_ref = continent.combos['reference'].runners['LU'][-1]
        >>> runner_other = continent.combos['other_combo'].runners['LU'][-1]
        >>> df_ref = compute_substitution(runner_ref, subst_scenario="reference")
        >>> df_subst = compute_substitution(runner_other, subst_scenario="substitution")
        >>> compare_substitution(subst_ref, subst_other)

    Example compute the difference between two HWP scenarios within the
    same reference combo:

        >>> from eu_cbm_hat.core.continent import continent
        >>> from eu_cbm_hat.post_processor.hwp_substitution  import compare_substitution
        >>> from eu_cbm_hat.post_processor.hwp_substitution  import compute_substitution
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> df_ref = compute_substitution(runner, subst_scenario="reference")
        >>> df_subst = compute_substitution(runner, subst_scenario="substitution")
        >>> # Comparison
        >>> compare_substitution(df_ref, df_subst)

    """
    # Select only the inflow columns
    selector = df_ref.columns.str.contains("inflow")
    # Except the original inflow columns
    selector &= ~df_ref.columns.str.contains("inflow_0")
    inflow_cols = df_ref.columns[selector].to_list()
    df_diff = df_ref[["year"] + inflow_cols].copy()
    # Compute the difference between inflows
    df_diff[inflow_cols] = df[inflow_cols] - df_ref[inflow_cols]
    # Rename to savings
    new_name = "savings"
    df_diff.rename(columns=lambda x: re.sub(r"inflow", new_name, x), inplace=True)
    # Sum up all the above per year
    cols = df_diff.columns[df_diff.columns.str.contains(new_name)]
    df_diff["total_savings"] = df_diff[cols].sum(axis=1)
    # Convert to CO2
    df_diff["total_savings_CO2"] = df_diff["total_savings"] * 44 / 12
    return df_diff




