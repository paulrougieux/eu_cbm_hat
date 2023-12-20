"""Diagnostic tables and plots

To analyse the model output.
"""

class Diagnostic:
    """Diagnostic tables and plots

    Usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> from matplotlib import pyplot as plt
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> runner.post_processor.diagnostic.plot_n_stands(by="status")
        >>> plt.show()

        >>> runner.post_processor.diagnostic.plot_n_stands(by="forest_type")
        >>> plt.show()

    Unique values of disturbance_type and last_disturbance_type

        >>> fluxes = runner.post_processor.fluxes.copy()
        >>> fluxes["time_since_dist"] = fluxes["time_since_last_disturbance"]
        >>> locator = fluxes["time_since_last_disturbance"] > 1
        >>> fluxes.loc[locator, "time_since_dist"] = "more"
        >>> # Count the number of rows for each unique combination of the selected cols
        >>> cols = ["time_since_dist", "disturbance_type", "last_disturbance_type"]
        >>> df = fluxes.value_counts(cols).reset_index().sort_values(cols)

    Therefore

    - the condition disturbance_type == 7

    - is equivalent to the condition time_since_last_disturbance == 1
      & last_disturbance_type == 7

    And the condition

    - disturbance_type==0

    - is almost equivalent to the condition time_since_last_disturbance >= 2
      except for the special case where disturbance_type==0 and
      last_disturbance_type ==2

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        self.country_name = self.runner.country.country_name
        self.pools = self.parent.pools
        self.fluxes = self.parent.fluxes

    def n_stands(self, groupby: str):
        """Number of stands in the model along the given grouping variables"""
        df = self.parent.pools
        df = df[[groupby, "year"]].value_counts().reset_index()
        return df

    def plot_n_stands(self, by: str):
        """Plot the number of stands in the model along the given classifier
        variable. Only one column name is allowed as the by variable.
        """
        df = self.n_stands(groupby=by)
        df = df.pivot(index="year", values="count", columns=by)
        title = "Number of stands in "
        title += f"{self.country_name} - {self.combo_name} combo"
        return df.plot(title=title)



