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

    # These are the equivalent names in the libcbm dataframes #
    sources_cbm = ['SoftwoodMerch',      'HardwoodMerch',
                   'SoftwoodOther',      'HardwoodOther',
                   'SoftwoodStemSnag',   'HardwoodStemSnag',
                   'SoftwoodBranchSnag', 'HardwoodBranchSnag']

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

        # The age and land_class columns appears twice #
        renaming = {'age':        'inv_start_age',
                    'land_class': 'inv_start_land_class'}
        end_vars.inventory = end_vars.inventory.rename(columns=renaming)

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

        # Get the classifier columns #
        clfrs = list(self.country.orig_data.classif_names.values())

        # Get the classifier columns along with `disturbance_type` #
        cols = clfrs + ["disturbance_type"]

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

        # Take only the stands that have not been disturbed yet #
        stands = stands.query("disturbance_type == 0")
        stands = stands.drop(columns = 'disturbance_type')

        # Keep only columns of interest from our current stands #
        interest = clfrs + ['time_since_last_disturbance',
                            'last_disturbance_type', 'age'] + self.sources_cbm
        stands = stands[interest]

        # Rename the pools to their snake case equivalent #
        stands = stands.rename(columns = dict(zip(self.sources_cbm,
                                                  self.sources)))

        # We will merge the current stands with the events templates #
        df = pandas.merge(stands, events, how='inner', on=clfrs)

        # We will filter on ages, `last_dist_id` and `min_since_last_dist` #
        df = df.query("age >= sw_start")
        df = df.query("age <= sw_end")
        df = df.query("last_dist_id == -1 | "
                      "last_dist_id == last_disturbance_type")
        df = df.query("min_since_last_dist == -1 | "
                      "min_since_last_dist <= time_since_last_disturbance")

        # We will now join the flux's proportions for each disturbance #
        props = self.runner.fluxes.df
        cols = self.runner.fluxes.cols + ['disturbance_type']
        df = pandas.merge(df, props[cols], how='left', on='disturbance_type')

        # We will retrieve the harvest skew factors for the current year #
        harvest = self.runner.silv.harvest.get_year(year)

        # Only one of the columns matches the current year #
        harvest = harvest.rename(columns = {'value_%i' % year: 'skew'})
        cols = self.runner.silv.harvest.cols + ['product_created']
        df = pandas.merge(df, harvest[cols + ['skew']], how='inner', on=cols)

        # We will add the fractions going to `irw` and `fw` #
        mapping  = {pool: pool + '_irw_frac' for pool in self.sources}
        irw_frac = irw_frac.rename(columns = mapping)
        cols     = clfrs + ["disturbance_type"]
        df       = df.merge(irw_frac, how='left', on=cols)

        # Join the wood density and bark fraction parameters also #
        df = df.merge(coefs, how='left', on=['forest_type'])

        # Calculate the two volumes that would be produced by the events #
        def vol_by_source(row, source, irw):
            frac = row[source + '_irw_frac']
            frac = frac if irw else 1 - frac
            return (row[source] *
                    row[source + '_prod_prop'] *
                    frac *
                    (1/row['dist_interval_bias']) *
                    row['skew'] *
                    (1 - row['bark_frac']) /
                    (0.49 * row['wood_density']))

        def mass_to_volume(row):
            irw_vol = (vol_by_source(row, s, True)  for s in self.sources)
            fw_vol  = (vol_by_source(row, s, False) for s in self.sources)
            return {'irw_vol': sum(irw_vol),
                    'fw_vol':  sum(fw_vol)}

        # Add two columns `irw_vol` and `fw_vol` to the dataframe #
        vols = df.apply(mass_to_volume, axis=1, result_type='expand')
        df = pandas.concat([df, vols], axis='columns')

        # If there is no irw demand just set to zero for calculation #
        if self.remain_irw_vol < 0: self.remain_irw_vol = 0

        # Distribute demand in volume evenly #
        irw_norm = self.remain_irw_vol / df['irw_vol'].sum()
        df['irw_vol_ask'] = df['irw_vol'] * irw_norm
        df['fw_vol_ask']  = df['fw_vol']  * irw_norm

        # Now we will work separately with `irw_and_fw` vs `fw_only` #
        df_irw = df.query("product_created == 'irw_and_fw'")
        df_fw  = df.query("product_created == 'fw_only'")

        # Check `products_created` is correct and not lying #
        check_irw = df_irw.query("fw_vol == 0.0")
        check_fw  = df_fw.query("irw_vol != 0.0")
        assert check_irw.empty
        assert check_fw.empty

        # How much firewood would this give us as a collateral product #
        fwi = df_fw.index
        df.loc[fwi, 'fw_vol_ask'] = 0.0
        self.remain_fw_vol -= df_irw['fw_vol_ask'].sum()

        # If there is still firewood to satisfy, distribute it evenly #
        if self.remain_fw_vol > 0.0:
            if df_fw['fw_vol'].sum() == 0.0:
                msg = "There is remaining fw demand this year, but there " \
                      "are no events that enable the creation of fw only."
                raise Exception(msg)
            fw_norm = self.remain_fw_vol / df_fw['fw_vol'].sum()
            df.loc[fwi, 'fw_vol_ask'] = df.loc[fwi, 'fw_vol'] * fw_norm

        # Then convert back to mass #
        def mass_to_volume(row):
            irw_vol = (vol_by_source(row, s, True)  for s in self.sources)
            fw_vol  = (vol_by_source(row, s, False) for s in self.sources)
            return {'irw_vol': sum(irw_vol),
                    'fw_vol':  sum(fw_vol)}
str 

        irw    = df_irw.index
        fw     = df_fw.index

        # Debug test #
        if timestep == 19:
            end_vars = copy.deepcopy(cbm_vars)
            end_vars = cbm_variables.prepare(end_vars)
            end_vars = self.cbm.step(end_vars)
            print(end_vars)

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

        # Otherwise, we create a dynamic event #
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