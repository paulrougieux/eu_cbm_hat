#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# Third party modules #
import logging
from libcbm.input.sit import sit_cbm_factory
from libcbm.model.cbm import cbm_simulator
from libcbm.model.cbm.cbm_output import CBMOutput
from libcbm.model.cbm.cbm_variables import CBMVariables
from libcbm.storage.backends import BackendType


# First party modules #

# Internal modules #

# Constants #
create_proc = sit_cbm_factory.create_sit_rule_based_processor

###############################################################################
class Simulation(object):
    """This class will run a `libcbm_py` simulation."""

    def __init__(self, parent):
        # Default attributes #
        self.parent  = parent
        self.runner  = parent
        self.country = self.runner.country
        self.classif_list = self.country.orig_data.classif_list
        # Record if we ended with an error or not #
        self.error = None

    def __repr__(self):
        return '%s object code "%s"' % (self.__class__, self.runner.short_name)

    #--------------------------- Special Methods -----------------------------#
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
        self.parent.log.info(msg)
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
        self.parent.log.info(f"Time step {timestep} is about to run.")
        # Run the usual rule based processor #
        cbm_vars = self.rule_based_proc.pre_dynamics_func(timestep, cbm_vars)
        # Return #
        return cbm_vars

    #------------------------------- Methods ---------------------------------#
    # noinspection PyBroadException
    def __call__(self, interrupt_on_error=False):
        """
        Wrap the `run()` method by catching any type of exception
        and logging it. This is useful when running all countries one after
        each other and not wanting that process to be interrupted even if a few
        countries fail along the way.
        """
        try:
            self.run()
        except Exception:
            message = "Runner '%s' encountered an exception. See log file at %s"
            # Find the path to the log file if available
            # The first handler is standard error, the second handler is a file
            log_file_path = "unknown"
            for handler in self.runner.log.handlers:
                if isinstance(handler, logging.FileHandler):
                    log_file_path = handler.baseFilename
                    break
            self.runner.log.error(message % (self.runner.short_name, log_file_path))
            self.runner.log.exception("Exception", exc_info=True)
            self.error = True
            if interrupt_on_error: raise

    def run(self):
        """
        Call `libcbm_py` to run the actual CBM simulation after creating some
        objects.
        The interaction with `libcbm_py` is decomposed in several calls to pass
        a `.json` config, a default database (also called aidb) and csv files.
        """
        # Message #
        self.runner.log.info("Setting up the libcbm_py objects.")
        # The 'AIDB' path as it was called previously #
        db_path = self.runner.country.aidb.paths.db
        if not db_path:
            msg = "The database file at '%s' was not found."
            raise FileNotFoundError(msg % self.runner.country.aidb.paths.db)
        # Create a SIT object #
        json_path = str(self.runner.paths.json)
        self.sit = sit_cbm_factory.load_sit(json_path, str(db_path))
        # Do some initialization #
        init_inv = sit_cbm_factory.initialize_inventory
        self.clfrs, self.inv = init_inv(self.sit)
        # This will contain results #
        self.cbm_output = CBMOutput(backend_type=BackendType.numpy)
        # Create a CBM object #
        with sit_cbm_factory.initialize_cbm(self.sit) as self.cbm:
            # Create a function to apply rule based events #
            self.rule_based_proc = create_proc(self.sit, self.cbm)
            # Message #
            self.runner.log.info("Calling the cbm_simulator.")
            # Run #
            cbm_simulator.simulate(
                self.cbm,
                n_steps           = self.runner.num_timesteps,
                classifiers       = self.clfrs,
                inventory         = self.inv,
                pre_dynamics_func = self.dynamics_func,
                reporting_func    = self.cbm_output.append_simulation_result,
            )
        # If we got here then we did not encounter any simulation error #
        self.error = False
        # Return for convenience #
        return self.cbm_output

    def clear(self):
        """
        Remove all objects from RAM otherwise the kernel will kill the python
        process after a couple countries being run.
        """
        if hasattr(self, 'cbm'):            del self.cbm
        if hasattr(self, 'sit'):            del self.sit
        if hasattr(self, 'clfrs'):          del self.clfrs
        if hasattr(self, 'inv'):            del self.inv
        if hasattr(self, 'results'):        del self.results
        if hasattr(self, 'reporting_func'): del self.reporting_func
        if hasattr(self, 'cbm_output'):     del self.cbm_output
