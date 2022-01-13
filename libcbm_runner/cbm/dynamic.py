#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #
import copy

# Third party modules #
import pandas

# First party modules #
from plumbing.cache import property_cached
from libcbm.input.sit import sit_cbm_factory
from libcbm.model.cbm import cbm_variables

# Internal modules #
from libcbm_runner.cbm.simulation import Simulation
from libcbm_runner.core.runner import Runner

# Constants #

###############################################################################
class DynamicRunner(Runner):
    """
    Replaces the standard Simulation object with a DynamicSimulation instead.
    """

    @property_cached
    def simulation(self):
        """The object that can run `libcbm` simulations."""
        return DynamicSimulation(self)

###############################################################################
class DynamicSimulation(Simulation):
    """
    This class inherits from the standard Simulation object, and adds
    new functionality. It enables the running of dynamic simulations which
    can specify their disturbances just-in-time as the model is running.
    This is in contrast to standard simulations which must have all
    disturbances predefined before the model run.
    """

    # These are the dataframe (as attributes) returned by `cbm.step()` #
    df_names = ['classifiers', 'parameters', 'inventory',
                'state', 'flux', 'pools']

    # These are the source pools we want to track fluxes from #
    sources = ['softwood_merch',       'hardwood_merch',
               'softwood_other',       'hardwood_other',
               'softwood_stem_snag',   'hardwood_stem_snag',
               'softwood_branch_snag', 'hardwood_branch_snag']

    #--------------------------- Special Methods -----------------------------#
    def dynamics_func(self, timestep, cbm_vars, debug=True):
        """
        First apply predetermined disturbances, then apply demand
        specific to harvesting. The full specification for the "Harvest
        Allocation Tool" (H.A.T.) is described in:

             ../specifications/libcbm_hat_spec.md

        Information used during development included:

        * The example notebook of the `libcbm` package.

            https://github.com/cat-cfs/libcbm_py/blob/master/examples/
            disturbance_iterations.ipynb
        """
        # Check if we want to switch the growth period classifier #
        if timestep == 1: cbm_vars = self.switch_period(cbm_vars)

        # Retrieve the current year #
        year = self.country.timestep_to_year(timestep)

        # Optional debug messages #
        if debug: print(timestep, year, self.country.base_year)

        # Run the usual rule based processor #
        cbm_vars = self.rule_based_proc.pre_dynamics_func(timestep, cbm_vars)

        # Check if we are still in the historical period #
        if year < self.country.base_year: return cbm_vars

        # Copy cbm_vars and hypothetically end the timestep here #
        end_vars = copy.deepcopy(cbm_vars)
        end_vars = cbm_variables.prepare(end_vars)
        end_vars = self.cbm.step(end_vars)

        # Check we always have the same sized dataframes #
        get_num_rows = lambda name: len(getattr(end_vars, name))
        assert len({get_num_rows(name) for name in self.df_names}) == 1

        # Concatenate dataframes together by columns into one big df #
        stands = pandas.concat([getattr(end_vars, name)
                                for name in self.df_names], axis=1)

        # Check that the 'Input' column is always one and remove #
        assert all(stands['Input'] == 1.0)
        stands = stands.drop(columns='Input')

        # Get the columns that contain either pools or fluxes #
        cols = list(end_vars.flux.columns) + list(end_vars.pools.columns)
        cols.pop(cols.index('Input'))

        # Fluxes and pools are scaled to tonnes per one hectare so fix it #
        stands[cols] = stands[cols].multiply(stands['area'], axis="index")
        stands[cols] = stands[cols].multiply(1000, axis="index")

        # Get the classifier columns along with `disturbance_type` #
        cols = self.runner.silv.irw_frac.cols

        # Get only eight interesting fluxes, summed also by dist_type #
        fluxes = stands.query("disturbance_type != 0")
        fluxes = fluxes.groupby(cols)
        fluxes = fluxes.agg({s + '_to_product': 'sum' for s in self.sources})
        fluxes = fluxes.reset_index()

        # Join the `irw` fractions with the fluxes going to `products` #
        irw_frac = self.runner.silv.irw_frac.get_year(year)
        fluxes = fluxes.merge(irw_frac, how='left', on=cols)

        # Join the wood density and bark fraction parameters also #
        coefs = self.runner.silv.coefs.df
        fluxes = fluxes.merge(coefs, how='left', on=['forest_type'])

        # Calculate the total `flux_irw` and `flux_fw` for this year #
        def tot_flux_to_vol(irw=True):
            # Convert all fluxes' fraction to volume #
            tot = [fluxes[s + '_to_product'] *
                   (fluxes[s] if irw else (1 - fluxes[s])) *
                   (1 - fluxes['bark_frac']) /
                   (0.49 * fluxes['wood_density'])
                   for s in self.sources]
            # Sum to a scalar #
            return sum([s.sum() for s in tot])

        # The argument is False for firewood and True for roundwood #
        tot_flux_irw_vol = tot_flux_to_vol(irw=True)
        tot_flux_fw_vol  = tot_flux_to_vol(irw=False)

        # Get demand for the current year #
        query  = "year == %s" % year
        demand_irw_vol = self.runner.demand.irw.query(query)['value']
        demand_fw_vol  = self.runner.demand.fw.query(query)['value']

        # Convert to a cubic meter float value #
        demand_irw_vol = demand_irw_vol.values[0] * 1000
        demand_fw_vol  = demand_fw_vol.values[0]  * 1000

        # Calculate unsatisfied demand #
        self.remain_irw_vol = demand_irw_vol - tot_flux_irw_vol
        self.remain_fw_vol  = demand_fw_vol  - tot_flux_fw_vol

        # If there is no unsatisfied demand, we stop here #
        if (self.remain_irw_vol <= 0) and (self.remain_fw_vol <= 0):
            return cbm_vars

        # To distribute remaining demand, first load event templates #
        events = self.runner.silv.events.get_year(year)

        # Get the classifier columns #
        cols = list(self.country.orig_data.classif_names.values())

        # Check that every event template has at least one stand to match it #
        if year == self.country.base_year + 9999999999:
            df = pandas.merge(stands, events, how='right', on=cols)
            df = df.query("_merge == 'right_only'")
            if not df.empty:
                msg = "The following events in '%s' have no matching stand.\n"
                msg = msg % self.runner.silv.events.csv_path
                msg = msg + df[cols].to_string()
                raise Exception(msg)

        # We will left-join the current stands with the events templates.
        # We validate that merge keys are unique in the right dataset with the
        # option `many_to_one` so that no stands are duplicated by the merge.
        df = pandas.merge(stands, events, how='left', on=cols,
                          validate='many_to_one')

        # Stands that did not get an event associated after the merge
        # are left alone and considered part of conservation efforts.
        df = df.query("_merge != 'left_only'")
        df = df.drop(columns='_merge')

        # Join the `irw` fractions with the fluxes going to `products` #
        #inv = fluxes.merge(irw_frac, how='left', on=cols)

        # Debug test #
        if timestep == 19:
            end_vars = copy.deepcopy(cbm_vars)
            end_vars = cbm_variables.prepare(end_vars)
            end_vars = self.cbm.step(end_vars)
            print(end_vars)
            1/0

        # Return #
        return cbm_vars

    #---------------------------- Exploration --------------------------------#
    def test(self, timestep, cbm_vars):
        # Check the timestep #
        if timestep == 12:
            print('test')

        # Info sources ? #
        # prod has columns:
        # Index(['DisturbanceSoftProduction', 'DisturbanceHardProduction',
        #        'DisturbanceDOMProduction', 'Total'])
        # Aggregate of fluxes,
        prod = self.cbm.compute_disturbance_production(cbm_vars, density=False)
        print(prod)

        # Sit events has columns:
        # Index(['total_eligible_value', 'total_achieved', 'shortfall',
        #        'num_records_disturbed', 'num_splits', 'num_eligible',
        #        'sit_event_index'],
        #        dtype = 'object')#
        print(self.rule_based_proc.sit_event_stats_by_timestep)

        # This is just the same as the input events.csv #
        print(self.sit.sit_data.disturbance_events)

        # This doesn't contain the current timestep, only past ones
        print(self.results.state)

        # Return #
        return cbm_vars

###############################################################################
class ExampleHarvestProcessor:
    """
    This class can dynamically generate disturbance events using an
    event template to meet the specified production target.

    This class was copied and adapted from the following notebook:

        https://github.com/cat-cfs/libcbm_py/blob/master/examples/
        disturbance_iterations.ipynb
    """

    def __init__(self, sit, cbm, production_target):
        # Base attributes #
        self.sit = sit
        self.cbm = cbm
        # User attributes #
        self.production_target = production_target
        # List to accumulate information #
        self.dynamic_stats_list     = []
        self.base_production_totals = []
        # Function shortcuts #
        self.calc_prod = self.cbm.compute_disturbance_production
        self.create_proc = sit_cbm_factory.create_sit_rule_based_processor
        # Extras #
        self.base_processor = self.create_proc(self.sit, self.cbm)

    sit_events_path = "~/repos/sinclair/work/freelance_clients/ispra_italy/" \
                      "repos/libcbm_py/libcbm/resources/test/cbm3_tutorial2" \
                      "/disturbance_events.csv"

    def get_event_template(self):
        """Return a prototypical disturbance event ready to be customized."""
        # Make dataframe #
        df = pandas.read_csv(self.sit_events_path).iloc[[0]]
        # Reset #
        df = df.reset_index(drop=True)
        # Return #
        return df

    def pre_dynamics_func(self, timestep, cbm_vars):
        """
        Use a production target (tonnes C) to apply across all years.
        This will be partially met by the base tutorial2 events,
        then fully met by a second dynamically generated event.
        """
        # Get CBM variables #
        cbm_vars = self.base_processor.pre_dynamics_func(timestep, cbm_vars)

        # Compute the total production resulting from the sit_events
        # bundled in the tutorial2 dataset.
        production_df = self.calc_prod(cbm_vars, density=False)
        total_production = production_df["Total"].sum()

        # Append #
        self.base_production_totals.append([timestep, total_production])

        # Subtract #
        remaining_production = self.production_target - total_production

        # If the target is already met we stop here #
        if remaining_production <= 0: return cbm_vars

        # Otherwise we create a dynamic event #
        dynamic_event = self.get_event_template()
        dynamic_event["disturbance_year"] = timestep
        dynamic_event["target_type"]      = "M"
        dynamic_event["target"]           = remaining_production

        # See the documentation:
        # `libcbm.input.sit.sit_cbm_factory.create_sit_rule_based_processor`
        dynamic_processor = self.create_proc(
            self.sit,
            self.cbm,
            reset_parameters = False,
            sit_events = dynamic_event
        )

        # Apply the disturbance #
        cbm_vars = dynamic_processor.pre_dynamics_func(timestep, cbm_vars)

        # Merge #
        df = dynamic_processor.sit_event_stats_by_timestep[timestep]
        df = df.merge(
            dynamic_event,
            left_on     = "sit_event_index",
            right_index = True
        )

        # Append #
        self.dynamic_stats_list.append(df)

        # Return CBM variables #
        return cbm_vars

    #----------------------------- Reporting ---------------------------------#
    def get_base_process_stats(self):
        """
        Gets the stats for all disturbances in:
        `sit.sit_data.disturbance_events`.
        """
        # Get stats #
        stats_df = pandas.concat(
            self.base_processor.sit_event_stats_by_timestep.values()
        )
        # Merge #
        df = stats_df.merge(
            self.sit.sit_data.disturbance_events,
            left_on     = "sit_event_index",
            right_index = True
        )
        # Return #
        return df

    def base_prod_totals_to_df(self):
        # Make dataframe #
        df = pandas.DataFrame(
            columns = ["timestep", "total_production"],
            data    = self.base_production_totals
        )
        # Return #
        return df

    def dynamic_proc_stats_to_df(self):
        # Make dataframe #
        df = pandas.concat(self.dynamic_stats_list).reset_index(drop=True)
        # Return #
        return df