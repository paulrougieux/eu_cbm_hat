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
from libcbm_runner.info.silviculture import keep_clfrs_without_question_marks
# Constants #


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

            docs/harvest_allocation_specification.md

        Information used during development included:

        * The example notebook of the `libcbm` package.

            https://github.com/cat-cfs/libcbm_py/blob/master/examples/
            disturbance_iterations.ipynb
        """
        # Check if we want to switch the growth period classifier #
        if timestep == 1: cbm_vars = self.switch_period(cbm_vars)

        # Retrieve the current year #
        self.year = self.country.timestep_to_year(timestep)

        # Optional debug messages #
        if debug: print(timestep, self.year, self.country.base_year)

        # Run the usual rule based processor #
        cbm_vars = self.rule_based_proc.pre_dynamics_func(timestep, cbm_vars)

        # Check if we are still in the historical period #
        # If we are still in the historical period HAT doesn't apply
        if self.year < self.country.base_year:
            return cbm_vars

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
#        stands[cols] = stands[cols].multiply(1000, axis="index")

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
        irw_frac = self.runner.silv.irw_frac.get_year(self.year)
        clfrs_noq = keep_clfrs_without_question_marks(irw_frac, clfrs)
        fluxes = fluxes.merge(irw_frac, how='left',
                              on=clfrs_noq + ["disturbance_type"],
                              suffixes=('_fluxes', ''))

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
        # TODO: rename these columns because they concern fluxes to products from
        # disturbances activities applied before HAT
        # salvage logging amount generated by HAT are *not* included here
        self.out_var('irw_salvage_act', tot_flux_irw_vol)
        self.out_var('fw_salvage_act',  tot_flux_fw_vol)

        # Get demand for the current year #
        query  = "year == %s" % self.year
        demand_irw_vol = self.runner.demand.irw.query(query)['value']
        demand_fw_vol  = self.runner.demand.fw.query(query)['value']

        # Convert to a cubic meter float value #
        demand_irw_vol = demand_irw_vol.values[0] * 1000
        demand_fw_vol  = demand_fw_vol.values[0]  * 1000

        # Calculate unsatisfied demand #
        remain_irw_vol = demand_irw_vol - tot_flux_irw_vol
        remain_fw_vol  = demand_fw_vol  - tot_flux_fw_vol
        self.out_var('remain_irw_vol', remain_irw_vol)
        self.out_var('remain_fw_vol',  remain_fw_vol)

        # If there is no unsatisfied demand, we stop here #
        if (remain_irw_vol <= 0) and (remain_fw_vol <= 0):
            return cbm_vars

        # To distribute remaining demand, first load event templates #
        events = self.runner.silv.events.get_year(self.year)

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
        clfrs_noq = keep_clfrs_without_question_marks(events, clfrs)
        df = pandas.merge(stands, events, how='inner', on=clfrs_noq,
                          suffixes=('_stands', ''))

        # Convert last_disturbance_type from the libcbm stands to the id used in events_templates input
        dist_map = self.runner.simulation.sit.disturbance_id_map
        df["last_disturbance_id"] = df["last_disturbance_type"].map(dist_map)
        df["last_disturbance_id"] = df["last_disturbance_id"].astype(int)

        # We will filter on ages, `last_dist_id` and `min_since_last_dist` #
        df = df.query("age >= sw_start")
        df = df.query("age <= sw_end")
        df = df.query("last_dist_id == -1 | "
                      "last_dist_id == last_disturbance_id")
        df = df.query("min_since_last_dist == -1 | "
                      "min_since_last_dist <= time_since_last_disturbance")

        # If we have no stands to disturb, go straight to next year #
        if df.empty: return cbm_vars

        # We will now join the flux's proportions for each disturbance #
        props = self.runner.fluxes.df
        cols = self.runner.fluxes.cols + ['disturbance_type']
        df = pandas.merge(df, props[cols], how='left', on='disturbance_type')

        # We will retrieve the harvest skew factors for the current year #
        harvest = self.runner.silv.harvest.get_year(self.year)

        # Only one of the columns matches the current year #
        harvest = harvest.rename(columns = {'value_%i' % self.year: 'skew'})
        cols = self.runner.silv.harvest.cols + ['product_created']

        # Keep only the columns that are not empty as join columns
        join_cols = []
        for col in cols:
            if not any(harvest[col].isna()):
                join_cols.append(col)
        df = pandas.merge(df, harvest[join_cols + ['skew']], how='inner', on=join_cols)
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

        # Save some columns of this dataframe as a CSV in the output #
        df['irw_avail'] = df['irw_vol'] / df['dist_interval_bias']
        df['fw_avail']  = df['fw_vol']  / df['dist_interval_bias']
        # Integrate the dist_interval_bias and the market skew #
        df['irw_pot'] = df['irw_vol'] * df['skew'] / df['dist_interval_bias']
        df['fw_pot']  = df['fw_vol']  * df['skew'] / df['dist_interval_bias']
        self.out_var('tot_irw_vol_pot', df['irw_pot'].sum())
        self.out_var('tot_fw_vol_pot',  df['fw_pot'].sum())

# include the "con/broad" ratio and give 100% priority of the final cuts 
# in consuming _avail 
# The ratios of con and broad in total would be defined in 'harvest_factors.csv?'

        # Now we will work separately with `irw_and_fw` vs `fw_only` #
        df_irw = df.query("product_created == 'irw_and_fw'").copy()
        df_fw  = df.query("product_created == 'fw_only'").copy()

        # Check `products_created` is correct and not lying #
        check_irw = df_irw.query("fw_vol == 0.0")
        check_fw  = df_fw.query("irw_vol != 0.0")
        assert check_irw.empty
        assert check_fw.empty

        # If there is no extra industrial roundwood needed, set to zero #
        if remain_irw_vol <= 0.0:
            remain_irw_vol = 0.0
        else:
            if df_irw['irw_vol'].sum() == 0.0:
                msg = "There is remaining irw demand this year, but there " \
                      "are no events that enable the creation of irw."
                raise Exception(msg)

        # Process salvage logging disturbances in priority if they are present
        # irw and fw potential from salvage logging disturbances
        salv = df_irw["last_dist_id"] != -1
        irw_salv_pot = df_irw.loc[salv, "irw_pot"].sum()
        fw_salv_pot = df_irw.loc[salv, "fw_pot"].sum()

        if any(salv):
            # Print a message #
            msg = f"Demand from the economic model {remain_irw_vol:.0f} m3. "
            msg += f"Potential amount available from salvage logging: "
            msg += f"{irw_salv_pot:.0f} m3 irw and {fw_salv_pot:.0f} m3 fw."
            self.parent.log.info(msg)

            # If the demand is greater than the potential, allocate only the potential
            irw_to_allocate = min(irw_salv_pot, remain_irw_vol)

            # Distribute evenly according to the potential irw volume produced
            # compute the proportion only for the salvage logging disturbances
            df_irw.loc[salv, "irw_norm"] = (df_irw.loc[salv, "irw_pot"] /
                                            df_irw.loc[salv, "irw_pot"].sum())

            # Calculate how much volume we need from each stand #
            df_irw.loc[salv, 'irw_need'] = irw_to_allocate * df_irw['irw_norm']
            assert math.isclose(df_irw.loc[salv, "irw_need"].sum(),
                                irw_to_allocate)

        # If salvage logging didn't satisfies all demand
        # Continue allocating disturbances
        if irw_salv_pot < remain_irw_vol:
            remain_irw_vol_after_salv = remain_irw_vol - irw_salv_pot
            # Distribute evenly according to the potential irw volume produced #
            df_irw.loc[~salv, "irw_norm"] = (df_irw.loc[~salv, "irw_pot"] /
                                             df_irw.loc[~salv, "irw_pot"].sum())

            # Calculate how much volume we need from each stand #
            df_irw.loc[~salv, "irw_need"] = (remain_irw_vol_after_salv * 
                                             df_irw.loc[~salv, "irw_norm"])
            assert math.isclose(df_irw.loc[~salv,"irw_need"].sum(),
                                remain_irw_vol_after_salv)

        # Check again whether the irw amount is fully allocated
        assert math.isclose(df_irw['irw_need'].sum(), remain_irw_vol)

        # Check the collateral fuel wood generated
        # How much is this volume as compared to the total volume possible #
# this is not needed in the output, it is confusing
        df_irw['irw_frac'] = df_irw['irw_need'] / df_irw['irw_vol']

        # How much firewood would this give us as a collateral product #
        df_irw['fw_colat'] = df_irw['irw_frac'] * df_irw['fw_vol']
# this FW seems an approximation, whu do not apply ratio of 1-IRW/IRW harvested? 
# where IRW are the fractions 

        # Subtract from remaining firewood demand #
        still_remain_fw_vol = remain_fw_vol - df_irw['fw_colat'].sum()
        self.out_var('still_remain_fw_vol', still_remain_fw_vol)

        # If there is no extra firewood needed, set to zero #
        if still_remain_fw_vol <= 0.0:
            still_remain_fw_vol = 0.0
        else:
            if df_fw['fw_vol'].sum() == 0.0:
                msg = "There is remaining fw demand this year, but there " \
                      "are no events that enable the creation of fw only."
                raise Exception(msg)

        # If there is still firewood to satisfy, distribute it evenly #
        df_fw['fw_norm'] = df_fw['fw_pot'] / df_fw['fw_pot'].sum()
        df_fw['fw_need'] = still_remain_fw_vol * df_fw['fw_norm']
        assert math.isclose(df_fw['fw_need'].sum(), still_remain_fw_vol)

        # Convert to mass (we don't need to care about source pools) #
        df_irw['amount'] = ((df_irw['irw_need'] + df_irw['fw_colat']) *
                            (0.49 * df_irw['wood_density']) /
                            (1 - df_irw['bark_frac']))
        df_fw['amount']  = (df_fw['fw_need'] *
                            (0.49 * df_fw['wood_density']) /
                            (1 - df_fw['bark_frac']))

        # Put the two dataframes back together #
        df = pandas.concat([df_irw, df_fw])

        # Filter out any events that have an amount of zero #
        df = df.query("amount != 0.0").copy()

        # Convert IDs back from the SIT standard to the user standard #
        df = self.conv_dists(df)
        df = self.conv_clfrs(df)


        df.insert(0, 'year', self.year)
        cols = ['year'] +  clfrs
        cols += ['disturbance_type', 'product_created', 'dist_interval_bias',
                 'using_id', 'sw_start', 'sw_end', 'hw_start', 'hw_end',
                 'min_since_last_dist', 'max_since_last_dist', 'last_dist_id',
                 'sort_type', 'efficiency', 'skew', 'wood_density',
                 'bark_frac', 'irw_avail', 'fw_avail',
                 'irw_pot', 'fw_pot', 'irw_norm', 'irw_need', 'irw_frac',
                 'fw_colat', 'amount', 'fw_norm', 'fw_need']
        self.runner.output.events = self.runner.output.events.append(df[cols])

        # Prepare the remaining missing columns for the events #
        df['measurement_type'] = 'M'
        df['step'] = timestep
        df = df.rename(columns={'disturbance_type': 'dist_type_name'})

        # Get only the right columns in the dataframe to send to `libcbm` #
        cols = self.runner.input_data['events'].columns
        df = df[cols].copy()

        # Create disturbances #
        dyn_proc = sit_cbm_factory.create_sit_rule_based_processor(
            self.sit,
            self.cbm,
            reset_parameters = False,
            sit_events = df
        )

        # Run the dynamic rule based processor #
        cbm_vars = dyn_proc.pre_dynamics_func(timestep, cbm_vars)

        # Print a message #
        msg = f"Time step {timestep} (year {self.year}) is about to finish."
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
        df['disturbance_type'] = df['disturbance_type'].map(id_to_id)
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
            # Keep question marks as is
            if df[classif_name].unique()[0] == "?":
                continue
            # Convert other values
            mapping = {v:k for k,v in str_to_id.items()}
            df[classif_name] = df[classif_name].map(mapping)
        # Return #
        return df

    def out_var(self, key, value):
        self.runner.output.extras.loc[self.year, key] = value
