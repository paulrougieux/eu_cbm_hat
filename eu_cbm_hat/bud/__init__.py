"""
Small self contain runner-type object to run libcbm by pointing it to an input
data directory and an AIDB. It is a small self contained object that makes it
possible to run the libcbm model and the EU-CBM-HAT post processor (to compute
sink output for example) without the need for the EU-wide
eu_cbm_data directory.

TODO :

    - replace print statements by proper logging

"""

from typing import Union, Dict
from pathlib import Path
from functools import cached_property

# autopaths and plumbing dependencies from Lucas Sinclair
from autopaths.auto_paths import AutoPaths
from plumbing.logger import create_file_logger
from plumbing.timer import LogTimer

# libcbm imports
from libcbm.input.sit import sit_cbm_factory
from libcbm.model.cbm import cbm_simulator
from libcbm.model.cbm.cbm_output import CBMOutput
from libcbm.model.cbm.cbm_variables import CBMVariables
from libcbm.storage.backends import BackendType

# EU CBM HAT Runner imports
from eu_cbm_hat.info.internal_data import InternalData
from eu_cbm_hat.launch.create_json import CreateJSON

# EU CBM HAT Bud imports
from eu_cbm_hat.bud.associations import BudAssociations
from eu_cbm_hat.bud.input_data import BudInputData
from eu_cbm_hat.bud.output import BudOutput
from eu_cbm_hat.bud.output import BudSim
from eu_cbm_hat.bud.post_processor import BudPostProcessor


class Bud:
    """Workflow pipeline object to run libcbm and postprocessing

    A bud is attached to an input and output directory on your file system. The
    directory can be in an arbitrary location, it doesn't need to be in the
    eu_cbm_data path.

    Create a bud object to run the input data of a particular scenario sc1,
    with the given aidb path.

    bash

        mkdir /tmp/sc1

    Copy test input data to a temporary directory and run the bud object. It
    will save model output to that temporary directory.

        >>> import eu_cbm_hat as ch
        >>> from eu_cbm_hat.bud.test_data import copy_input_to_temp_dir
        >>> data_dir = copy_input_to_temp_dir()
        >>> bud = ch.Bud(
        ...     data_dir=data_dir,
        ...     aidb_path=ch.eu_cbm_aidb_pathlib / "countries/ZZ/aidb.db"
        ... )
        >>> bud.run()

    """

    # See core/runner.py if more paths are needed
    all_paths = """
    /logs/runner.log
    /input/json/config.json
    """

    def __init__(self, data_dir: Union[str, Path], aidb_path: Union[str, Path]):
        self.data_dir = Path(data_dir)
        self.aidb_path = Path(aidb_path)
        # Default number of simulation time steps.
        self.num_timesteps = 20
        # Check if the scenario directory contains input/csv
        if not (self.data_dir / "input/csv").exists():
            msg = "The data directory doesn't contain an input/csv subdirectory."
            msg += f"\ndata_dir: {data_dir}"
            raise FileNotFoundError(msg)
        #########################################################
        # Properties defined to be able to reuse runner methods #
        #########################################################
        # Most importantly the runner.post_processor methods
        self.short_name = self.data_dir.name
        self.paths = AutoPaths(str(self.data_dir), self.all_paths)
        self.simulation = self.sim
        self.timer = LogTimer(self.log)

    def __repr__(self):
        return '%s object on "%s"' % (self.__class__, self.data_dir)

    def timestep_to_year(self, timestep):
        """Dummy year values to be able to use runner.post_processor"""
        return timestep

    @property
    def input_data(self):
        """Input data"""
        return BudInputData(self)

    @property
    def associations(self):
        """Input data"""
        return BudAssociations(self)

    @property
    def create_json(self):
        """Input data"""
        return CreateJSON(self)

    @cached_property
    def sit(self):
        """Standard import tool object

        Examples
        --------
        >>> from eu_cbm_hat.bud import Bud
        >>> ref = Bud(scenarios_dir, aidb_path)
        >>> ref.sit.classifier_value_ids.items()

        """
        # Create the JSON configuration #
        self.create_json()
        json_path = str(self.paths.json)
        return sit_cbm_factory.load_sit(json_path, str(self.aidb_path))

    def run(self):
        """
        Call `libcbm_py` to run the CBM simulation.
        The interaction with `libcbm_py` is decomposed in several calls to pass
        a `.json` config, a default database (also called aidb) and csv files.
        """
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
                n_steps=self.num_timesteps,
                classifiers=self.clfrs,
                inventory=self.inv,
                pre_dynamics_func=self.dynamics_func,
                reporting_func=self.cbm_output.append_simulation_result,
            )
        # Save the results to disk #
        self.output.save()
        return self.cbm_output

    def switch_period(self, cbm_vars: CBMVariables) -> CBMVariables:
        """
        If t=1, we know this is the first timestep, and nothing has yet been
        done to the post-spinup pools. It is at this moment that we want to
        change the growth curves, and this can be done by switching the
        classifier value of each inventory record.
        """
        msg = (
            "Carbon pool initialization period is finished."
            " Now starting the `current` period.\n"
            f"Simulating {self.num_timesteps} time steps:"
        )
        print(msg)
        # The name of our extra classifier #
        key = "growth_period"
        # The value that the classifier should take for all timesteps #
        val = "Cur"
        # Get the corresponding ID in the libcbm simulation #
        id_of_cur = self.sit.classifier_value_ids[key][val]
        # Modify the whole column of the dataframe #
        cbm_vars.classifiers[key].assign(id_of_cur)
        # Return #
        return cbm_vars

    def dynamics_func(self, timestep: int, cbm_vars: CBMVariables) -> CBMVariables:
        """
        See the simulate method of the `libcbm_py` simulator:

            https://github.com/cat-cfs/libcbm_py/blob/master/libcbm/
            model/cbm/cbm_simulator.py#L148
        """
        # Check if we want to switch growth period
        if timestep == 1:
            cbm_vars = self.switch_period(cbm_vars)
        print(f"{timestep} ", end="", flush=True)
        # Run the rule based processor
        cbm_vars = self.rule_based_proc.pre_dynamics_func(timestep, cbm_vars)
        return cbm_vars

    @cached_property
    def output(self):
        """Save libcbm output or reload libcbm output"""
        return BudOutput(self)

    @cached_property
    def sim(self):
        """Attach simulation sit output at a sub-level"""
        return BudSim(self)

    @cached_property
    def post_processor(self):
        """Convert and summarize output data."""
        return BudPostProcessor(self)

    ######################################
    # Methods copied from core/runner.py #
    ######################################
    # TODO: Remove copy, inherit from a common base_runner class?
    @cached_property
    def log(self):
        """
        Each runner will have its own logger. By default we clear the log file
        when we start logging. This happens when you call this property for
        the first time. If you want to view the log file of a previous run,
        check the attribute `self.paths.log`.
        """
        # Pick console level #
        level = "error"
        if hasattr(self, "verbose"):
            if isinstance(self.verbose, bool):
                if self.verbose:
                    level = "debug"
            else:
                level = self.verbose
        # Create #
        logger = create_file_logger(
            self.short_name, self.paths.log, console_level=level
        )
        # Return #
        return logger
    
    @cached_property
    def internal(self):
        """
        Access and format data concerning the simulation as it is being
        run.
        """
        return InternalData(self)

