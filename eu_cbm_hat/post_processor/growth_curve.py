"""Load and display growth curves for all countries"""

import pandas
from functools import cached_property

class GrowthCurve:
    """Extract information on growth curves

    Example use:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.growth_curve.df

    Get the growth curves for all countries

        >>> from eu_cbm_hat.post_processor.agg_combos import get_df_all_countries
        >>> growth_curve_all = get_df_all_countries(
        >>>     combo_name="reference",
        >>>     runner_method_name="post_processor.growth_curve.df"
        >>> )
 
    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name

    @cached_property
    def df_wide(self):
        """Growth curves in wide format with age classes in columns, similar to
        CBM input"""
        df = self.runner.input_data["growth_curves"]
        return df

    @cached_property
    def df(self):
        """Growth curves in long format"""
        index = self.parent.classifiers_list
        cols = self.df_wide.columns
        cols = cols[cols.str.contains("vol")]
        df = self.df_wide.melt(id_vars=index, value_vars=cols, var_name="age_class", value_name="merch_stock")
        df["age_class"] = df["age_class"].str.replace("vol", "")
        df["age_class"] = pandas.to_numeric(df["age_class"])
        return df





