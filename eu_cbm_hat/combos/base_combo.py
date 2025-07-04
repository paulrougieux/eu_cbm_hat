#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair, Paul Rougieux and Viorel Blujdea.

JRC Biomass Project.
Unit D1 Bioeconomy.

"""

# Built-in modules #
from functools import cached_property
import re
import textwrap

# Third party modules #
import yaml, pandas
from p_tqdm import p_umap, t_map

# First party modules #
from autopaths import Path
from plumbing.timer import Timer

# Internal modules #
from eu_cbm_hat.constants import eu_cbm_data_dir
from eu_cbm_hat.core.runner import Runner
from eu_cbm_hat.cbm.dynamic import DynamicRunner

# Constant directory for all the data #
yaml_dir = eu_cbm_data_dir + "combos/"


def run_one_country(args):
    """Run a single country, allowing any errors with a broad except statement.

    This function should only be used by a Combination.run() method.
    """
    last_year, runner = args
    runner.num_timesteps = last_year - runner.country.inventory_start_year
    print(runner)
    try:
        # The argument interrupt_on_error=False deals with errors happening
        # during the actual libcbm run
        runner.run(verbose=True, interrupt_on_error=False)
    # Catching general exception in case there are other errors in the input
    # data preparation or pre processor
    except Exception as general_error:
        print(general_error)


def runner_log_summary(runner, patterns=None):
    """Return the summary of a past model run for the given runner

    Usage:

        >>> from eu_cbm_hat.core.continent import continent
        >>> from eu_cbm_hat.combos.base_combo import runner_log_summary
        >>> runner_lu = continent.combos['reference'].runners['LU'][-1]
        >>> print(runner_log_summary(runner_lu))

    """
    if patterns is None:
        patterns = ["error", "done", "elapsed", "disk", "total elapsed"]

    msg = f"\n * {runner.country.iso2_code} {runner.country.country_name}\n"

    if not runner.paths.log.exists:
        msg += f"No log file at: {runner.paths.log}\n"
    else:
        msg += f"{runner.paths.log}\n"
        with open(runner.paths.log, "r") as file:
            for line in file:
                if any(pattern in line.lower() for pattern in patterns):
                    msg += f"{line}"

    return msg


class Combination(object):
    """
    This object represents a combination of specific scenarios for different
    activities and includes any other customization of a given model run.

    Each Combination subclass must define a list of Runner instances as
    the <self.runners> property. This enables the complete customization of
    any Runner by the specific Combination instance.

    You can run a combo like this:

        >>> from eu_cbm_hat.core.continent import continent
        >>> combo = continent.combos['historical']
        >>> combo()

    You can run a specific runner from a given country like this:

        >>> from eu_cbm_hat.core.continent import continent
        >>> combo = continent.combos['historical']
        >>> r = combo.runners['LU'][-1]
        >>> r.run(True, True, True)


    Print information on the inventory and yield curve used in the management
    activity for this runner

      print("Scenario combinations")
      for key in ["inventory", "growth_curves", "events"]:
          print(key, ":", runner.combo.config[key])

    You can then check the output pools:

        >>> r.output.load('pools')
    """

    def __init__(self, continent, short_name=None):
        self.short_name = short_name
        # Save parent #
        self.continent = continent
        # The combos dir used for all output #
        self.output_dir = self.continent.output_dir
        # The base dir for our output #
        self.base_dir = Path(self.output_dir + self.short_name + "/")
        # The path to our specific YAML file #
        self.yaml_path = yaml_dir + self.short_name + ".yaml"

    def __repr__(self):
        return "%s object with %i runners" % (self.__class__, len(self))

    def __iter__(self):
        return iter(self.runners.values())

    def __len__(self):
        return len(self.runners.values())

    def __getitem__(self, key):
        """Return a runner based on a country code."""
        return self.runners[key]

    @cached_property
    def config(self) -> dict:
        """
        The values chosen by the user in the YAML file which decide on every
        scenario choice for every activity and silvicultural practice.
        """
        # Read it with a third party library #
        with open(self.yaml_path, "r") as handle:
            result = yaml.safe_load(handle)
        # Convert silvicultural choices to dataframes #
        key = "harvest"
        value = result[key]
        if not isinstance(value, str):
            df = pandas.DataFrame.from_dict(value, orient="index", columns=["scenario"])
            df = df.rename_axis("year").reset_index()
            result[key] = df
        # Return result #
        return result

    @cached_property
    def runners(self) -> dict:
        """
        A dictionary of country codes as keys with a list of runners as
        values.
        """
        accepted_runner_types = ["base_runner", "dynamic_runner"]

        # Error message to be reused by diverse errors
        msg = f"The yaml file at {self.yaml_path} "
        msg += "should contain a 'runner_type' field with values:"
        msg += "\nrunner_type: "
        msg += "\n# or\nrunner_type: ".join(accepted_runner_types)

        # If runner_type is not defined in the yaml file raise an error
        if "runner_type" not in self.config.keys():
            raise ValueError(msg)

        if self.config["runner_type"] not in accepted_runner_types:
            msg_2 = f"runner_type: {self.config['runner_type']} "
            msg_2 += "is not an accepted value.\n"
            raise ValueError(msg_2 + msg)

        # If it's defined as "base_runner", return base runners
        if self.config["runner_type"] == "base_runner":
            return {c.iso2_code: [Runner(self, c, 0)] for c in self.continent}

        # If it's defined as "dynamic_runner" return dynamic runners
        if self.config["runner_type"] == "dynamic_runner":
            return {c.iso2_code: [DynamicRunner(self, c, 0)] for c in self.continent}

    def __call__(self, parallel=False, timer=True):
        """Legacy code, use the .run() method instead

        A method to run a combo by simulating all countries.

        Compared to the run() method, this call also runs many steps, if the
        runner has many steps inside .
        """
        # Message #
        print("Running combo '%s'." % self.short_name)
        # Timer start #
        timer = Timer()
        timer.print_start()

        # Function to run a single country #
        def run_country(args):
            code, steps = args
            for runner in steps:
                return runner.run()

        # Run countries sequentially #
        if not parallel:
            result = t_map(run_country, self.runners.items())
        # Run countries in parallel #
        else:
            result = p_umap(run_country, self.runners.items(), num_cpus=4)
        # Timer end #
        timer.print_end()
        timer.print_total_elapsed()
        # Compile logs #
        self.compile_logs()
        # Return #
        return result

    def run(self, last_year: int, countries: list = None, parallel=True):
        """Run a scenario combination

        If the list of countries is not specified, run all countries. A
        convenient method that makes it possible to run all countries inside a
        combination of scenarios. If one country fails to run, the error will
        be kept in its log files but the other countries will continue to run.

        Note: this method makes use of the run_one_country() function above
        which will only run one step inside the country. An update to that
        function will be needed in case your simulation needs many steps. We
        typically only run one step normally. Here the meaning of step is not
        that of yearly time steps, but bigger steps in terms of being able to
        start and stop the model which were foreseen in a legacy version of the
        model.

        Usage:

            >>> from eu_cbm_hat.core.continent import continent
            >>> # Run the selected list of countries
            >>> continent.combos["reference"].run(2050, ['IT','ZZ'])
            >>> # Run all countries with parallel cpus
            >>> continent.combos["reference"].run(2050)
            >>> # Run sequentially (not in parallel)
            >>> continent.combos["reference"].run(2050, parallel=False)

        """
        if countries is None:
            countries = self.runners.keys()
        # List of tuples, each tuple will be passed as argument to the
        # function that runs one country.
        runner_items = [(last_year, self.runners[k][-1]) for k in countries]
        if parallel:
            result = p_umap(run_one_country, runner_items, num_cpus=10)
        else:
            result = t_map(run_one_country, runner_items)
        return result

    def compile_logs(self, step=-1):
        # Open file #
        summary = self.base_dir + "all_logs.md"
        summary.open(mode="w")
        # Write title #
        title = "# Summary of all log files #\n\n"
        summary.handle.write(title)
        # Loop over runners #
        for rs in self.runners.values():
            r = rs[step]
            summary.handle.write("\n## " + r.country.country_name)
            summary.handle.write(" (" + r.country.iso2_code + ")" + "\n\n")
            content = textwrap.indent(r.paths.log.contents, "    ")
            summary.handle.write(content)
        # Close #
        summary.close()
        # Message #
        msg = "Log files compiled at:\n\n%s\n"
        print(msg % summary)
        # Return #
        return summary

    def print_log_summary(self, patterns=None, short=False):
        """Print the summary of all runners in a scenario combination

        Change the patterns argument to display more information from the log
        files.

        Usage:

            >>> from eu_cbm_hat.core.continent import continent
            >>> continent.combos["reference"].print_log_summary()

        For example, to check for a specific log message containing the words
        'carbon' and 'salvage', call:

            >>> continent.combos["reference"].print_log_summary(['carbon', 'salvage'])

        """
        if isinstance(patterns, str):
            patterns = [patterns]
        country_logs = {}

        for country_code in self.runners.keys():
            if country_code == "ZZ":
                continue
            runner = self.runners[country_code][-1]
            try:
                country_logs[country_code] = runner_log_summary(
                    runner, patterns=patterns
                )
            except OSError as e:  # Sometimes the log file is unreadable
                country_logs[country_code] = str(e)
            if patterns is not None and "done" not in patterns:
                continue
            # Summary one line per country at the beginning
            msg = ""
            if "done" in country_logs[country_code].lower():
                for line in country_logs[country_code].split("\n"):
                    if "total elapsed time" in line.lower():
                        msg += str(re.findall("(elapsed time: .*)", line)[-1])
                    if "done" in line.lower():
                        msg += " " + line
                print(re.sub("\n", " ", msg))
            else:
                print(self.short_name, country_code, "No 'done' message.")

        if short:
            return

        print("\n--------------------------------------------------------------")
        print("-------------------- Details ---------------------------------")
        print("--------------------------------------------------------------")

        for country_code, log in country_logs.items():
            print(country_code, log)
