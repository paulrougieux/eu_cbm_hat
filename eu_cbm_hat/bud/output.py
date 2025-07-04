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
    """libcbm simulation output"""

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

    # def save(self):
    #     """Save libcbm output to parquet files on disk

    #     One parquet file for each of the tables:
    #     ['area', 'classifiers', 'flux', 'parameters', 'pools', 'state']

    #     """

    #     for t in self.tables:
    #         print(self.bud.cbm_output[t].head())

