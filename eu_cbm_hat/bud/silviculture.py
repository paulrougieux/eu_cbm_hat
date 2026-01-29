from functools import cached_property
from pathlib import Path
import pandas as pd


class SilvicultureCoefs():
    """Load wood density bark fraction coefficients"""
    def __init__(self, parent):
        self.parent = parent
        file_name = "vol_to_mass_coefs.csv"
        csv_path = self.parent.parent.data_dir / "input/csv" / file_name
        if not csv_path.exists():
            raise FileNotFoundError(f"the file name {file_name} is necessary for the computation of HWP. Please add it at {csv_path}.")
        self.raw = pd.read_csv(csv_path)


class BudSilviculture():
    """Patch silvictulture object to use HWP in bud"""
    def __init__(self, parent):
        self.parent = parent

    @cached_property
    def coefs(self):
        """Wood density and bark fraction data"""
        return SilvicultureCoefs(self)

