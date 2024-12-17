"""
Workflow pipeline object to run libcbm by pointing it to a data directory. It
is a small self contained object that makes it possible to run test without
the need for the eu_cbm_data directory.

TODO :

    - replace print statements by proper logging

"""

import pathlib

from libcbm.input.sit import sit_cbm_factory
from libcbm.model.cbm.cbm_output import CBMOutput
from libcbm.storage.backends import BackendType
from libcbm.model.cbm import cbm_simulator
from libcbm.model.cbm.cbm_variables import CBMVariables


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
        self.data_dir = pathlib.Path(data_dir)

    @property
    def num_timesteps(self):
        """The number of time steps defaults to the last disturbance events.

        It can be overwritten by setting this value.
        """
        return 20

    def __repr__(self):
        return '%s object on "%s"' % (self.__class__, self.data_dir)

    def run(self):
        """
        Call `libcbm_py` to run the CBM simulation.
        The interaction with `libcbm_py` is decomposed in several calls to pass
        a `.json` config, a default database (also called aidb) and csv files.
        """
        db_path = pathlib.Path.home() / "eu_cbm/eu_cbm_aidb/countries/IE/aidb.db"
        # Create a SIT object #
        json_path = self.data_dir / "input/json/config.json"
        self.sit = sit_cbm_factory.load_sit(json_path, str(db_path))
        # Initialization #
        init_inv = sit_cbm_factory.initialize_inventory
        self.clfrs, self.inv = init_inv(self.sit)
        # This will contain results #
        self.cbm_output = CBMOutput(backend_type=BackendType.numpy)
        # Create a CBM object #
        with sit_cbm_factory.initialize_cbm(self.sit) as self.cbm:
            # Create a function to apply rule based events #
            create_proc = sit_cbm_factory.create_sit_rule_based_processor
            self.rule_based_proc = create_proc(self.sit, self.cbm)
            # Run #
            cbm_simulator.simulate(
                self.cbm,
                n_steps = self.num_timesteps,
                classifiers = self.clfrs,
                inventory = self.inv,
                pre_dynamics_func = self.dynamics_func,
                reporting_func = self.cbm_output.append_simulation_result,
            )
        return self.cbm_output

    def switch_period(self, cbm_vars: CBMVariables) -> CBMVariables:
        """
        If t=1, we know this is the first timestep, and nothing has yet been
        done to the post-spinup pools. It is at this moment that we want to
        change the growth curves, and this can be done by switching the
        classifier value of each inventory record.
        """
        # Print message #
        msg = "Carbon pool initialization period is finished." \
              " Now starting the `current` period.\n"
        print(msg)
        # The name of our extra classifier #
        key = 'growth_period'
        # The value that the classifier should take for all timesteps #
        val = "Cur"
        # Get the corresponding ID in the libcbm simulation #
        id_of_cur = self.sit.classifier_value_ids[key][val]
        # Modify the whole column of the dataframe #
        cbm_vars.classifiers[key].assign(id_of_cur)
        # Return #
        return cbm_vars

    def dynamics_func(self, timestep:int, cbm_vars: CBMVariables) -> CBMVariables:
        """
        See the simulate method of the `libcbm_py` simulator:

            https://github.com/cat-cfs/libcbm_py/blob/master/libcbm/
            model/cbm/cbm_simulator.py#L148
        """
        # Check if we want to switch growth period #
        if timestep == 1: cbm_vars = self.switch_period(cbm_vars)
        # Print a message #
        print(f"Time step {timestep} is about to run.")
        # Run the usual rule based processor #
        cbm_vars = self.rule_based_proc.pre_dynamics_func(timestep, cbm_vars)
        # Return #
        return cbm_vars



