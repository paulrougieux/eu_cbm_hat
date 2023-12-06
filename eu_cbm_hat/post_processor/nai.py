"""
The purpose of this script is to compute the Net Annual Increment for one country
"""

from functools import cached_property

class NAI:
    """Compute the net annual increment$


        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['reference'].runners['LU'][-1]

        >>> runner.post_processor.nai.df

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        self.pools = self.parent.pools
        self.fluxes = self.parent.fluxes

    @cached_property
    def df(self):
        """Net Annual Increment at the most detailed level"""

    def df_agg(self, groupby):
        """Net Annual Increment grouped by the given grouping variables"""

