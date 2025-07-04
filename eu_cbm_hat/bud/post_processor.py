"""Post Processor for the bud object"""

from functools import cached_property
# from eu_cbm_hat.post_processor.sink import Sink
from eu_cbm_hat.post_processor import PostProcessor

class BudPostProcessor(PostProcessor):
    """
    Compute aggregates based on the pools and sink table output from the model

    Run the model:

        >>> import eu_cbm_hat as hat
        >>> data_dir = hat.module_dir_pathlib / "tests/bud_data"
        >>> bzz = Bud(
        ...     data_dir=hat.module_dir_pathlib / "tests/bud_data",
        ...     aidb_path=eu_cbm_data_pathlib.parent / "eu_cbm_aidb/countries/ZZ/aidb.db"
        ... )
        >>> bzz.run()
        >>> bzz.post_processor.sink.df

    """

    def __init__(self, parent):
        # Call the runner.post_processor initialization method
        super().__init__(parent)

    def get_dist_description(self, pattern):
        """Get disturbance types which contain the given pattern in their name"""
        df = self.parent.input_data["disturbance_types"]
        selector = df["dist_desc_input"].str.contains(pattern, case=False)
        return df.loc[selector]
