#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #
import copy, math

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
    def dynamics_func(self, timestep, cbm_vars, debug=False):
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
        remain_irw_vol = demand_irw_vol - tot_flux_irw_vol
        remain_fw_vol  = demand_fw_vol  - tot_flux_fw_vol

        # If there is no unsatisfied demand, we stop here #
        if (remain_irw_vol <= 0) and (remain_fw_vol <= 0):
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

        # If we have no stands to disturb, go straight to next year #
        if df.empty: return cbm_vars

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

        # Group our event candidates on classifiers and disturbance ID #
        grp_cols = cols + ['product_created']

        # All these columns must have unique values for a given age range #
        unique_cols = [col for col in events.columns if col not in grp_cols]
        unique_cols += ['skew', 'wood_density', 'bark_frac']

        # Keep all required columns after the aggregation and sum volumes #
        agg_cols = {col: 'unique' for col in unique_cols}
        agg_cols['irw_vol'] = 'sum'
        agg_cols['fw_vol']  = 'sum'

        # Group-by and aggreagte so that age classes merge together #
        df = df.groupby(grp_cols)
        df = df.aggregate(agg_cols)
        df = df.reset_index()

        # Explode the uniques and check the number of rows does not change #
        orig_len = len(df)
        df = df.explode(unique_cols)
        assert len(df) == orig_len

        # Integrate the dist_interval_bias and the market skew #
        df['irw_pot'] = df['irw_vol'] * df['skew'] / df['dist_interval_bias']
        df['fw_pot']  = df['fw_vol']  * df['skew'] / df['dist_interval_bias']

        # Now we will work separately with `irw_and_fw` vs `fw_only` #
        df_irw = df.query("product_created == 'irw_and_fw'").copy()
        df_fw  = df.query("product_created == 'fw_only'").copy()

        # Check `products_created` is correct and not lying #
        check_irw = df_irw.query("fw_vol == 0.0")
        check_fw  = df_fw.query("irw_vol != 0.0")
        assert check_irw.empty
        assert check_fw.empty

        # Distribute evenly according to the potential irw volume produced #
        df_irw['irw_norm'] = df_irw['irw_pot'] / df_irw['irw_pot'].sum()

        # Calculate how much volume we need from each stand #
        df_irw['irw_need'] = remain_irw_vol * df_irw['irw_norm']
        assert math.isclose(df_irw['irw_need'].sum(), remain_irw_vol)

        # How much is this volume as compared to the total volume possible #
        df_irw['irw_frac'] = df_irw['irw_need'] / df_irw['irw_vol']

        # How much firewood would this give us as a collateral product #
        df_irw['fw_colat'] = df_irw['irw_frac'] * df_irw['fw_vol']

        # Subtract from remaining firewood demand #
        still_miss_fw_vol = remain_fw_vol - df_irw['fw_colat'].sum()

        # If there is no extra firewood needed, set to zero #
        if still_miss_fw_vol <= 0.0:
            still_miss_fw_vol = 0.0
        else:
            if df_fw['fw_vol'].sum() == 0.0:
                msg = "There is remaining fw demand this year, but there " \
                      "are no events that enable the creation of fw only."
                raise Exception(msg)

        # If there is still firewood to satisfy, distribute it evenly #
        df_fw['fw_norm'] = df_fw['fw_pot'] / df_fw['fw_pot'].sum()
        df_fw['fw_need'] = still_miss_fw_vol * df_fw['fw_norm']
        assert math.isclose(df_fw['fw_need'].sum(), still_miss_fw_vol)

        # Convert to mass (we don't need to care about source pools) #
        df_irw['amount'] = ((df_irw['irw_need'] + df_irw['fw_colat']) *
                            (0.49 * df_irw['wood_density']) /
                            (1 - df_irw['bark_frac']))
        df_fw['amount']  = (df_fw['fw_need'] *
                            (0.49 * df_fw['wood_density']) /
                            (1 - df_fw['bark_frac']))

        # Put the two dataframes back together #
        df = pandas.concat([df_irw, df_fw])

        # Prepare the remaining missing columns for the events #
        df['measurement_type'] = 'M'
        df['step'] = timestep
        df = df.rename(columns={'disturbance_type': 'dist_type_name'})

        # Get only the right columns in the dataframe to send to `libcbm` #
        cols = self.runner.input_data['events'].columns
        events = df[cols].copy()

        # Convert IDs back from the SIT standard to the user standard #
        events = self.conv_dists(events)
        events = self.conv_clfrs(events)

        # Create disturbances #
        dyn_proc = sit_cbm_factory.create_sit_rule_based_processor(
            self.sit,
            self.cbm,
            reset_parameters = False,
            sit_events = events
        )

        # Run the dynamic rule based processor #
        cbm_vars = dyn_proc.pre_dynamics_func(timestep, cbm_vars)

        # Debug test #
        if timestep == 16:
            print("Timestep 16")

        # Record values for safe keeping in the output #
        record = {'remain_irw_vol':    remain_fw_vol,
                  'remain_fw_vol':     remain_fw_vol,
                  'still_miss_fw_vol': still_miss_fw_vol,
                  'tot_irw_vol_pot':   df['irw_pot'].sum(),
                  'tot_fw_vol_pot':    df['fw_pot'].sum()}

        # Save them in a dataframe owned by the output object #
        for k,v in record.items():
            self.runner.output.extras.loc[year, k] = v

        # Print a message #
        msg = f"Time step {timestep} (year {year}) is about to finish."
        self.parent.log.info(msg)

        # Return #
        return cbm_vars

    #--------------------------- Other Methods -------------------------------#
    def conv_dists(self, df):
        """
        Convert the disturbance IDs from their internal simulation IDs that
        are defined by SIT into the user defined equivalent string.
        """
        # Get the conversion mapping #
        id_to_id = self.runner.simulation.sit.disturbance_id_map
        # Apply the mapping to the dataframe #
        df['dist_type_name'] = df['dist_type_name'].map(id_to_id)
        # Return #
        return df

    def conv_clfrs(self, df):
        """
        Convert the classifier IDs from their internal simulation IDs that
        are defined by SIT into the user defined equivalent string.
        """
        # Get all the conversion mappings, for each classifier #
        all_maps = self.runner.simulation.sit.classifier_value_ids.items()
        # Apply each of them to the dataframe #
        for classif_name, str_to_id in all_maps:
            mapping = {v:k for k,v in str_to_id.items()}
            df[classif_name] = df[classif_name].map(mapping)
        # Return #
        return df

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