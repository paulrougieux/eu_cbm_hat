"""Post Processor for the bud object"""

from functools import cached_property

class BudPostProcessor():
    """
    Compute aggregates based on the pools and sink table output from the model
    """

    def __init__(self, parent):
        self.bud = parent

    @cached_property
    def pools(self):
        """Licbm output pools"""
        return self.bud.cbm_output.pools.to_pandas()

    @cached_property
    def flux(self):
        """Licbm output fluxes"""
        return self.bud.cbm_output.flux.to_pandas()


