"""Methods to save and/or reload libcbm output"""

from functools import cached_property
from eu_cbm_hat.info.output_data import OutputData

from autopaths.auto_paths import AutoPaths

class BudSim:
    """Dummy class to attach sit at a sub level similar to runner.simulation.sit
    """

    def __init__(self, parent):
        self.bud = parent

    @property
    def sit(self):
        """SIT"""
        return self.bud.sit

    @property
    def cbm_output(self):
        """SIT"""
        return self.bud.cbm_output

class BudOutput(OutputData):
    """libcbm simulation output

    Inherits from the runner OutputData object. Stores data in the same way.
    The data can be retrieved after a simulation run for example load the pool
    flux data frame with:

    bud.output.pool_flux

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent
        self.tables = ['area', 'classifiers', 'flux', 'parameters', 'pools', 'state']
        # Properties defined to be able to reuse runner methods
        # TODO: create a self.sim such that so that we can use methods of
        # info/output_data.py which inherits from info/internal_data.py
        # self.sim.sit = self.bud.sit
        self.paths = AutoPaths(str(self.parent.data_dir), self.all_paths)
        self.sim = self.parent.sim


