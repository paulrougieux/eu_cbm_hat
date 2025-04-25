"""Compare substitution scenarios"""
import re


def compare_substitution(df_ref, df):
    """Compare the substitution data frame to a reference data frame

    1. Compute the difference between the substitution scenario  and the reference
    2. Aggregate and sUm up values

    There is a distinction between :
        - a scenario combination when running CBM here the combos are called "reference" and "other_combo"
        - a HWP scenario here the hwp_scenario arguments are called "reference" and "substitution"

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner_ref = continent.combos['reference'].runners['LU'][-1]
        >>> runner_other = continent.combos['other_combo'].runners['LU'][-1]
        >>> subst_ref = runner_ref.post_processor.hwp.substitution(hwp_scenario="reference")
        >>> subst_other = runner_other.post_processor.hwp.substitution(hwp_scenario="substitution")
        >>> compare_substitution(subst_ref, subst_other)

    Example compute the difference between two HWP scenarios within the
    reference combo:

        >>> from eu_cbm_hat.core.continent import continent
        >>> from eu_cbm_hat.post_processor.hwp_substitution  import compare_substitution
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> df_ref = runner.post_processor.hwp.substitution(hwp_scenario="reference")
        >>> df_subst = runner.post_processor.hwp.substitution(hwp_scenario="substitution")
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
