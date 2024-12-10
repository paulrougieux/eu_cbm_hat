"""
Workflow pipeline object to run libcbm by pointing it to a data directory. It
is a small self contained object that makes it possible to run test without
the need for the eu_cbm_data directory.

"""


class Bud:
    """Workflow pipeline object to run libcbm and postprocessing

    A bud is attached to an input and output directory on your file system. The
    directory can be in an arbitrary location, it doesn't need to be in the
    eu_cbm_data path.

    Create a bud object to run the input data of a particular scenario sc1

        >>> from eu_cbm_hat.bud import Bud
        >>> sc1 = Bud("/tmp/sc1")

    """

    def __init__(self, data_dir):
        self.data_dir = data_dir

    def __repr__(self):
        return '%s object on "%s"' % (self.__class__, self.data_dir)



