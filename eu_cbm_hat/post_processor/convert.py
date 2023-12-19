"""Conversion functions"""

from eu_cbm_hat import CARBON_FRACTION_OF_BIOMASS


def ton_carbon_to_m3_ub(df, input_var):
    """Convert tons of carbon to volume in cubic meter under bark"""
    return (df[input_var] * (1 - df["bark_frac"])) / (
        CARBON_FRACTION_OF_BIOMASS * df["wood_density"]
    )
