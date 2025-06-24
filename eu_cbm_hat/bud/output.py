"""Methods to save and/or reload libcbm output"""
from eu_cbm_info.output_data import OutputData

class BudSim:
    """Dummy class to attach sit at a sub level similar to runner.simulation.sit
    """

    def __init__(self, parent):
        self.bud = parent

    def sit(self):
        """SIT"""
        return self.bud.sit

class BudOutput(OutputData):
    """libcbm simulation output"""

    def __init__(self, parent):
        self.bud = parent
        self.tables = ['area', 'classifiers', 'flux', 'parameters', 'pools', 'state']
        # TODO: create a self.sim such that so that we can use methods of
        # info/output_data.py which inherits from info/internal_data.py
        # self.sim.sit = self.bud.sit

    def save(self):
        """Save libcbm output to parquet files on disk

        One parquet file for each of the tables:
        ['area', 'classifiers', 'flux', 'parameters', 'pools', 'state']

        """

        for t in self.tables:
            print(self.bud.cbm_output[t].head())

