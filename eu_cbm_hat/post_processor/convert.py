"""Conversion functions"""

from eu_cbm_hat.constants import CARBON_FRACTION_OF_BIOMASS


def ton_carbon_to_m3_ub(df, input_var):
    """Convert tons of carbon to volume in cubic meter under bark

    The input data frame must contain the bark_frac and wood_density columns.
    """
    return (df[input_var] * (1 - df["bark_frac"])) / (
        CARBON_FRACTION_OF_BIOMASS * df["wood_density"]
    )


def ton_carbon_to_m3_ob(df, input_var):
    """Convert tons of carbon to volume in cubic meter over bark

    The input data frame must contain the wood_density column.
    """
    return df[input_var] / (
        CARBON_FRACTION_OF_BIOMASS * df["wood_density"]
    )


# addedd for outputs on softwood/con and hardwood/broad 
def ton_carbon_to_m3_ub_soft(df, input_var):
    """Convert tons of carbon to volume in cubic meter under bark

    The input data frame must contain the bark_frac and wood_density columns.
    """
    return (df[input_var] * (1 - df["bark_frac"])) / (
        CARBON_FRACTION_OF_BIOMASS * df["wood_density"]
    )

def ton_carbon_to_m3_ub_hard(df, input_var):
    """Convert tons of carbon to volume in cubic meter under bark

    The input data frame must contain the bark_frac and wood_density columns.
    """
    return (df[input_var] * (1 - df["bark_frac"])) / (
        CARBON_FRACTION_OF_BIOMASS * df["wood_density"]
    )

def ton_carbon_to_m3_ob_soft(df, input_var):
    """Convert tons of carbon to volume in cubic meter over bark

    The input data frame must contain the wood_density column.
    """
    return df[input_var] / (
        CARBON_FRACTION_OF_BIOMASS * df["wood_density"]
    )

def ton_carbon_to_m3_ob_hard(df, input_var):
    """Convert tons of carbon to volume in cubic meter over bark

    The input data frame must contain the wood_density column.
    """
    return df[input_var] / (
        CARBON_FRACTION_OF_BIOMASS * df["wood_density"]
    )
