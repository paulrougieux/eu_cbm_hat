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

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        self.country_name = self.runner.country.country_name
        self.pools = self.parent.pools
        self.fluxes = self.parent.fluxes

    def plot_n_stands(self, by:str):
        """Plot the number of stands in the model along the given classifier
        variable
        """
        df = self.parent.pools
        df = df[[by, "year"]].value_counts().reset_index()
        df = df.pivot(index="year", values="count", columns=by)
        title = "Number of stands in "
        title += f"{self.country_name} - {self.combo_name} combo"
        return df.plot(title=title)
