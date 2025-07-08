"""Associate 'AdminBoundary', 'EcoBoundary', 'Species', 'DisturbanceType' names
with the names used in the Archive Index Database (AIDB).
"""


from functools import cached_property
from eu_cbm_hat.launch.associations import Associations

class BudAssociations(Associations):
    """
    This class parses the file "associations.csv" and returns
    a dictionary useful to produce the JSON for consumption by
    libcbm.

    Steps:
        - Read associations.csv in a data frame (relic of CBMCFS3)
        - Prepare a dictionary mapping 'AdminBoundary', 'EcoBoundary',
          'Species', 'DisturbanceType' names with the names used in the Archive
          Index Database (AIDB).

    Usage:

        >>> import eu_cbm_hat as ch
        >>> from eu_cbm_hat.bud.test_data import copy_input_to_temp_dir
        >>> data_dir = copy_input_to_temp_dir()
        >>> bzz = ch.Bud(
        ...     data_dir=data_dir,
        ...     aidb_path=ch.eu_cbm_aidb_pathlib / "countries/ZZ/aidb.db"
        ... )
        >>> bzz.associations.df
        >>> bzz.associations.all_mappings
        >>> bzz.create_json.content

    """

    @cached_property
    def df(self):
        """
        Load the CSV from the bud input data path.
        """
        return self.parent.input_data["associations"]

