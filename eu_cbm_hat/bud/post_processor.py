"""Post Processor for the bud object"""

from functools import cached_property
import pandas as pd
# from eu_cbm_hat.post_processor.sink import Sink
from eu_cbm_hat.post_processor import PostProcessor

class BudPostProcessor(PostProcessor):
    """
    Compute aggregates based on the pools and sink table output from the model

    Run the model:

        >>> import eu_cbm_hat as ch
        >>> from eu_cbm_hat.bud.test_data import copy_input_to_temp_dir
        >>> data_dir = copy_input_to_temp_dir()
        >>> bzz = ch.Bud(
        ...     data_dir=data_dir,
        ...     aidb_path=ch.eu_cbm_aidb_pathlib / "countries/ZZ/aidb.db"
        ... )
        >>> bzz.run()
        >>> bzz.post_processor.sink.df

    """

    def __init__(self, parent):
        # Call the runner.post_processor initialization method
        super().__init__(parent)
        irw_frac = pd.read_csv(self.parent.data_dir / "input/csv" / "irw_frac_by_dist.csv")
        # Duplicate irw_frac for every year to match standard CBM runner input format
        years = pd.DataFrame({'year': range(2000, 2101)})
        irw_frac = irw_frac.assign(key=1).merge(years.assign(key=1), on='key').drop('key', axis=1)
        # Convert site index to a string
        irw_frac["site_index"] = irw_frac["site_index"].astype(str)
        self.irw_frac = irw_frac

    def get_dist_description(self, pattern):
        """Get disturbance types which contain the given pattern in their name"""
        df = self.parent.input_data["disturbance_types"]
        selector = df["dist_desc_input"].str.contains(pattern, case=False)
        return df.loc[selector]
