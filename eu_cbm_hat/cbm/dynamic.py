#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair, Paul Rougieux and Viorel Blujdea.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #
import copy, math
import warnings

# Third party modules #
import pandas

# First party modules #
from plumbing.cache import property_cached
from libcbm.input.sit import sit_cbm_factory
from libcbm.model.cbm.cbm_variables import CBMVariables

# Internal modules #
from eu_cbm_hat.cbm.simulation import Simulation
from eu_cbm_hat.cbm.cbm_vars_to_df import cbm_vars_to_df
from eu_cbm_hat.core.runner import Runner
from eu_cbm_hat.info.silviculture import keep_clfrs_without_question_marks
from eu_cbm_hat.info.silviculture import keep_clfrs_without_question_marks_by_dist
from eu_cbm_hat.cbm.climate_growth_modifier import GrowthModifier


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

    To see the simulation object:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['hat'].runners["ZZ"][-1]
        >>> runner.simulation.sources

    Compare to another scenario with skew by clear cut and thinning disturbances

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['skewfcth'].runners["ZZ"][-1]

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
        First apply predetermined disturbances, then apply harvest
        specific to harvesting. The full specification for the "Harvest
        Allocation Tool" (H.A.T.) is described in:

            docs/harvest_allocation_specification.md

        Information used during development included:

        * The example notebook of the `libcbm` package.

            https://github.com/cat-cfs/libcbm_py/blob/master/examples/
            disturbance_iterations.ipynb

        The `stands` data frame used in `dynamics_func` is a
        concatenation of the classifiers, parameters, inventory, state, flux
        and pools data frames from end vars which is the result of a simulation
        of the stand state at the **end** of the time step. Thanks to
        `end_vars = copy.deepcopy(cbm_vars)` followed by
        `end_vars = self.cbm.step(end_vars)`.

        """
        # Check if we want to switch the growth period classifier #
        if timestep == 1: cbm_vars = self.switch_period(cbm_vars)

        # Retrieve the current year #
        self.year = self.country.timestep_to_year(timestep)

        # Optional debug messages #
        if debug: print(timestep, self.year, self.country.base_year)

        # Run the usual rule based processor #
        cbm_vars = self.rule_based_proc.pre_dynamics_func(timestep, cbm_vars)

        # Climate adjustment consists in updating the growth multiplier column
        # in the CBM state table. Perform the update only if
        # runner.combo.config["climate_adjustment_model"] is not 'default'
        msg = "Climate adjustment model: "
        msg += f"{self.runner.clim_adjust.model}"
        self.parent.log.debug(msg)
        if not self.runner.clim_adjust.model == "default":
            cbm_vars = self.growth_modifier.update_state(year=self.year, cbm_vars=cbm_vars)

        msg = f"Time step {timestep} (year {self.year})."
        self.parent.log.info(msg)

        # Check if we are still in the historical period #
        # If we are still in the historical period HAT doesn't apply
        if self.year < self.country.base_year:
            return cbm_vars

        # Copy cbm_vars and hypothetically end the timestep here #
        end_vars = copy.deepcopy(cbm_vars)
        end_vars = self.cbm.step(end_vars)

        # Check that the number of lines at the beginning and end of the time
        # step are the same. Important in case we change the state data frame to
        # ensure they are the same data frame. (we should also check the key order)
        n_begin = len(cbm_vars_to_df(cbm_vars, "state"))
        n_end = len(cbm_vars_to_df(end_vars, "state"))
        if not n_begin == n_end:
            msg = "The number of lines at the beginning of the time step"
            msg += f"{n_begin}."
            msg += "Doesn't match the number of lines at the end of the time step"
            msg += "{n_end}."
            raise ValueError(msg)

        # Check that all data frames in cbm_vars have the same size #
        get_num_rows = lambda name: getattr(end_vars, name).n_rows
        assert len({get_num_rows(name) for name in self.df_names}) == 1

        # Concatenate dataframes together by columns into one big df #
        stands = pandas.concat([cbm_vars_to_df(end_vars,name)
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

        # Get the classifier columns along with `disturbance_type` #
        cols = self.classif_list + ["disturbance_type"]

        # Get only eight interesting fluxes, summed also by dist_type #
        fluxes = stands.query("disturbance_type != 0")
        fluxes = fluxes.groupby(cols)
        fluxes = fluxes.agg({s + '_to_product': 'sum' for s in self.sources})
        fluxes = fluxes.reset_index()

        # Join the `irw` fractions with the fluxes going to `products` #
        irw_frac = self.runner.silv.irw_frac.get_year(self.year)
        # Dynamic merge index of non-empty columns to be used when merging
        # Classifier columns can be fully empty either `?` or `NA` values.
        # These unused columns should be removed from the merge index.
        clfrs_noq = keep_clfrs_without_question_marks(irw_frac, self.classif_list)
        cols_to_product = [s + "_to_product" for s in self.sources]
        sum_flux_before_merge = fluxes[cols_to_product].sum().sum()
        fluxes = fluxes.merge(irw_frac, how='left',
                              on=clfrs_noq + ["disturbance_type"],
                              suffixes=('', '_irw_frac_1'))
        assert sum_flux_before_merge == fluxes[cols_to_product].sum().sum()

        # Check that irw frac is defined for all stands that have fluxes to products
        missing_irw_frac = fluxes[self.sources].isna().any(axis=1)
        has_flux_to_prod =  fluxes[cols_to_product].sum(axis=1)>1
        selector = missing_irw_frac & has_flux_to_prod
        if any(selector):
            fluxes2 = self.conv_clfrs(fluxes.copy())
            irw_frac2 = self.conv_clfrs(irw_frac.copy())
            msg = "Industrial roundwood fractions defined in irw_frac_by_dist.csv "
            msg += "do not have irw fractions for the following classifiers:\n"
            msg += f"{fluxes2[selector]}"
            raise ValueError(msg)

        # Join the wood density and bark fraction parameters also #
        coefs = self.runner.silv.coefs.df
        fluxes = fluxes.merge(coefs, how='left', on=['forest_type'])
        assert sum_flux_before_merge == fluxes[cols_to_product].sum().sum()

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

        # Fluxes to products from disturbances activities applied before HAT
        # salvage logging amount generated by HAT are *not* included here
        self.out_var('irw_predetermined', tot_flux_irw_vol)
        self.out_var('fw_predetermined',  tot_flux_fw_vol)

        # Get harvest for the current year #
        query  = "year == %s" % self.year
        harvest_irw_vol = self.runner.harvest.irw.query(query)['value']
        harvest_fw_vol  = self.runner.harvest.fw.query(query)['value']

        # Convert to a cubic meter float value #
        harvest_irw_vol = harvest_irw_vol.values[0] * 1000
        harvest_fw_vol  = harvest_fw_vol.values[0]  * 1000

        # add columns with harvests
        self.out_var('harvest_irw_vol', harvest_irw_vol)
        self.out_var('harvest_fw_vol',  harvest_fw_vol)

        # Calculate unsatisfied harvest #
        remain_irw_vol = harvest_irw_vol - tot_flux_irw_vol
        remain_fw_vol  = harvest_fw_vol  - tot_flux_fw_vol
        self.out_var('remain_irw_harvest', remain_irw_vol)
        self.out_var('remain_fw_harvest',  remain_fw_vol)

        # If there is no unsatisfied harvest, we stop here #
        if (remain_irw_vol <= 0) and (remain_fw_vol <= 0):
            return cbm_vars

        # To distribute remaining harvest, first load event templates #
        events = self.runner.silv.events.get_year(self.year)

        # Take only the stands that have not been disturbed yet #
        stands = stands.query("disturbance_type == 0")
        stands = stands.drop(columns = 'disturbance_type')

        # Keep only columns of interest from our current stands #
        interest = self.classif_list + ['time_since_last_disturbance',
                            'last_disturbance_type', 'age'] + self.sources_cbm
        stands = stands[interest]

        # Rename the pools to their snake case equivalent #
        stands = stands.rename(columns = dict(zip(self.sources_cbm,
                                                  self.sources)))

        # We will merge the current stands with the events templates #
        # - filter events for that disturbance only in a df called events_one_dist
        # - check the classifiers without questionn marks inside events_one_dist 
        # - merge stands with events_one_dist stands =
        #   stands.merge(events_one_dist, on=classif_no_qu). Note now we **cannot
        #   do an inner merge** because this would keep only values from the
        #   first disturance in the list. We do a left merge instead.
        # - filter out rows which have NA values in disturbance_type, that
        #   means there are no defined envents template for these rows
        def display_time():
            from datetime import datetime
            now = datetime.now()
            return f"{now:%H:%M:%S}.{now.microsecond // 1000:03d}"
        self.parent.log.debug(f"Before stands merge with dist template: {display_time()}")
        classif_agg = keep_clfrs_without_question_marks_by_dist(events, self.classif_list)
        df = pandas.DataFrame()

        # Merge events and stands on a disturbance specific basis. Because some
        # classifier might be present or not depending on the disturbance.
        for dist in events["disturbance_type"].unique():
            # Events template for one disturbance
            events_one_dist = events.loc[events["disturbance_type"] == dist].copy()
            selector = classif_agg["disturbance_type"] == dist
            selector &= ~classif_agg["has_na"]
            clfrs_noq = classif_agg.loc[selector]["classifier"].to_list()
            # Remove the unused classifier columns from events template
            unused_classif = list(set(self.classif_list) - set(clfrs_noq))
            events_one_dist.drop(columns=unused_classif, inplace=True)
            # Keep only the stands which have this unique combination of
            # Classifiers through an inner merge
            stands_one_dist_merged = stands.merge(events_one_dist, on=clfrs_noq, how="inner")
            df = pandas.concat([df, stands_one_dist_merged])
        df = df.reset_index(drop=True)
        self.parent.log.debug(f"Stands merge with dist template finished: {display_time()}")

        # Convert last_disturbance_type from the libcbm stands to the id used in events_templates input
        dist_map = self.runner.simulation.sit.disturbance_id_map
        df["last_disturbance_id"] = df["last_disturbance_type"].map(dist_map)
        df["last_disturbance_id"] = df["last_disturbance_id"].astype(int)

        ################################
        # Filter eligible disturbances #
        ################################
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

        # Add the fractions going to `irw` and `fw` #
        mapping  = {pool: pool + '_irw_frac' for pool in self.sources}
        irw_frac = irw_frac.rename(columns = mapping)
        cols     = self.classif_list + ["disturbance_type"]
        
        # Merge with IRW fractions on classifiers that are not NA
        clfrs_noq = keep_clfrs_without_question_marks(irw_frac, self.classif_list)
        df = df.merge(irw_frac, how='left',
                      on=clfrs_noq + ["disturbance_type"],
                      suffixes=('', '_irw_frac_2'))

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
        unique_cols += ['wood_density', 'bark_frac']

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

        # Compute availability
        df['irw_avail'] = df['irw_vol'] / df['dist_interval_bias']
        df['fw_avail']  = df['fw_vol']  / df['dist_interval_bias']

        # If there is no extra industrial roundwood needed, set to zero #
        if remain_irw_vol <= 0.0:
            remain_irw_vol = 0.0
        else:
            if df['irw_vol'].sum() == 0.0:
                msg = "There is remaining IRW harvest this year, but there " \
                      "are no events that enable the creation of irw."
                raise Exception(msg)
        #msg = f"IRW harvest {remain_irw_vol:.0f} m3."
        #self.parent.log.info(msg)

        ######################
        # Harvest allocation #
        ######################
        # 1. Salvage logging disturbances
        #    - generate IRW and FW as a collateral
        #    - based on the normalized value of irw_avail
        # 2. Normal silviculture disturbances
        #    - generate IRW and FW as a collateral
        #    - based on the normalized value of irw_avail including a skew factor
        #    - the skew factor leads to a reshuffling of the harvest proportion by
        #      grouping variables such as by coniferous and broadleaves
        #      (but this is flexible as it depends only on the columns that are
        #      filled in the harvest_factors.csv file)
        # 3. Fuel wood only disturbances
        #    - generate FW only
        #    - based on the normalized value of irw_avail
        # Separate the disturbances data frame between
        # salvage logging, `irw_and_fw` and `fw_only`
        salv = (df["last_dist_id"] != -1) & (df["product_created"] == "irw_and_fw")
        silv = (df["last_dist_id"] == -1) & (df["product_created"] == "irw_and_fw")
        fw_only = (df["product_created"] == "fw_only")
        df_irw_salv = df.loc[salv].copy()
        df_irw_silv = df.loc[silv].copy()
        df_fw  = df.loc[fw_only].copy()

        # Check that all rows are covered once and only once by the sub data frames
        alloc_check = (salv.astype(int) + silv + fw_only) == 1
        if not all(alloc_check):
            msg = "Some disturbances are present in more than one category"
            msg += f"\n{df.loc[alloc_check]}"
            raise Exception(msg)
        assert all(salv | silv | fw_only)
        assert(len(df) == len(df_irw_salv) + len(df_irw_silv) + len(df_fw))
        
        # Check `products_created` is correct and not lying #
        check_irw = df_irw_silv.query("fw_vol == 0.0")
        check_fw = df_fw.query("irw_vol != 0.0")
        if not check_irw.empty:
            cols = ["forest_type", "disturbance_type", "product_created"]
            cols += ["irw_avail", "fw_avail"]
            msg = "Some rows have zero values for the fuel wood column.\n"
            msg += f"{check_irw[cols]}"
            raise ValueError(msg)
        assert check_fw.empty

        # Process salvage logging disturbances in priority if they are present
        if any(salv):
            # irw and fw potential from salvage logging disturbances
            irw_salv_avail = df_irw_salv["irw_avail"].sum()
            fw_salv_avail = df_irw_salv["fw_avail"].sum()
            # Print a message #
            msg = "Potential amount available from salvage logging: "
            msg += f"{irw_salv_avail:.0f} m3 IRW and "
            msg += f"{fw_salv_avail:.0f} m3 fw (colateral of IRW)."
            self.parent.log.info(msg)

            # If the harvest is greater than the potential, allocate only the potential
            irw_to_allocate = min(irw_salv_avail, remain_irw_vol)

            # Distribute evenly according to the potential irw volume produced
            # compute the proportion only for the salvage logging disturbances
            df_irw_salv["irw_norm"] = (df_irw_salv["irw_avail"] /
                                            df_irw_salv["irw_avail"].sum())

            # Calculate how much volume we need from each stand #
            df_irw_salv['irw_need'] = irw_to_allocate * df_irw_salv['irw_norm']
            assert math.isclose(df_irw_salv["irw_need"].sum(),
                                irw_to_allocate)
        else:
            irw_salv_avail = 0
            fw_salv_avail = 0

        # Save salvage logging in output
        self.out_var('irw_salv_avail', irw_salv_avail)
        self.out_var('fw_salv_avail', fw_salv_avail)

        # If salvage logging didn't satisfies all harvest
        # Continue allocating disturbances
        if irw_salv_avail < remain_irw_vol:
            remain_irw_vol_after_salv = remain_irw_vol - irw_salv_avail
            msg = f"Remaining IRW demand after salvage: {remain_irw_vol_after_salv:.0f} m3."
            self.parent.log.info(msg)
            # Distribute evenly according to the potential irw volume produced #
            df_irw_silv["irw_norm"] = (df_irw_silv["irw_avail"] /
                                       df_irw_silv["irw_avail"].sum())

            # Skew the normalized value based on the harvest skew factors
            # We will retrieve the harvest skew factors for the current year #
            harvest_factors = self.runner.silv.harvest.get_year(self.year)

            # Only one of the columns matches the current year #
            harvest_factors = harvest_factors.rename(columns = {'value_%i' % self.year: 'skew'})

            # Keep only IRW coefficients
            harvest_factors = harvest_factors[harvest_factors["product_created"] == "irw_and_fw"]


            # Keep only the columns that are not empty as join columns
            harvest_join_cols = []
            for col in self.runner.silv.harvest.cols:
                if not any(harvest_factors[col].isna()):
                    harvest_join_cols.append(col)
            harvest_factors = harvest_factors[harvest_join_cols + ['skew']]

            # If silv_practice is defined in harvest factors then use
            # self.runner.fluxes.df to add the silv_practice column to
            # df_irw_silv
            if "silv_practice" in harvest_join_cols:
                df_silv_practice = self.runner.fluxes.df[["disturbance_type", "silv_practice"]]
                df_irw_silv = df_irw_silv.merge(df_silv_practice, on="disturbance_type")

                # Check silv practices are actually present in disturbance_types.csv
                hfsp = harvest_factors.silv_practice.unique()
                distsp = self.runner.fluxes.df["silv_practice"].unique()
                if not set(hfsp).issubset(distsp):
                    msg = "silv_practice defined in harvest_factors.csv: "
                    msg += f"{hfsp}"
                    msg +=  " do not match the ones in disturbance_types.csv: "
                    msg += f"{distsp}"
                    raise ValueError(msg)

            # Check if all rows for which a skew factor is defined are really
            # present in df_irw_silv
            df_irw_silv_check = df_irw_silv.value_counts(harvest_join_cols).reset_index()
            if len(df_irw_silv_check) < len(harvest_factors):
                msg += "Some skew factors are present in harvest but not present in "
                msg += "df_irw_silv. This might happen in rare cases where there is only "
                msg += "coniferous forest available and no broadleaf forest available. "
                msg += "For example because broadleaves are too young and the "
                msg += "query('age >= sw_start') excluded those broadleaf rows. "
                self.parent.log.info(msg)
                # Recompute the skew
                harvest2 = df_irw_silv_check.merge(harvest_factors, on=harvest_join_cols)
                harvest2["skew"] = harvest2["skew"] / harvest2["skew"].sum()
                harvest_factors = harvest2

            # Aggregate the normalized value by groups
            df_irw_silv["irw_norm_agg"] = df_irw_silv.groupby(harvest_join_cols)["irw_norm"].transform("sum")

            # Merge disturbances and harvest factors
            df_irw_silv = pandas.merge(df_irw_silv,
                                       harvest_factors,
                                       how='inner',
                                       on=harvest_join_cols)

            # Modify the harvest distribution coefficient by the skew along each grouping variable
            df_irw_silv["irw_norm_skew"] = (df_irw_silv["irw_norm"]
                                            * df_irw_silv["skew"]
                                            / df_irw_silv["irw_norm_agg"])

            # Raise an error if irw_norm_skew does not sum to one
            if not math.isclose(df_irw_silv["irw_norm_skew"].sum(), 1):
                msg = "IRW norm skew doesn't sum to one:"
                msg += f"{df_irw_silv.groupby(harvest_join_cols)['irw_norm_skew'].sum()}\n"
                msg += "The normalized available merchantable roundwood is distributed as follows:\n"
                msg += f"{df_irw_silv.groupby(harvest_join_cols)['irw_norm_agg'].unique()}\n"
                msg += "The harvest factors are distributed as follows:\n"
                msg += f"{ harvest_factors[harvest_join_cols + ['skew']]}\n "
                msg += "This means that some combinations of silvicultural practices "
                msg += "are not present in the events template."
                msg += "Correct the input in havest_factors.csv."
                msg += "It could also be that the share of industrial roundwood is not specified."
                msg += "Check the irw_frac_by_dist.csv"
                raise ValueError(msg)

            potential_irw = df_irw_silv["irw_avail"].sum()
            msg += f"Potential IRW available from regular silvicultural practices: "
            msg += f"{potential_irw:.0f} m3."
            prct = 100 * remain_irw_vol / potential_irw
            msg += f"IRW demand corresponds to {prct:.0f}% of the IRW available."
            self.parent.log.info(msg)

            #df_irw_silv["prop"] = df_irw_silv[

            # Calculate how much volume we need from each stand #
            df_irw_silv["irw_need"] = (remain_irw_vol_after_salv *
                                             df_irw_silv["irw_norm_skew"])
            assert math.isclose(df_irw_silv["irw_need"].sum(), remain_irw_vol_after_salv)
            # The user is free to over allocate IRW, but will be a warning if the
            # allocation is over the potential annualized availability.
            if  remain_irw_vol > potential_irw:
                excess_prct = remain_irw_vol / potential_irw - 1
                excess_prct = round(excess_prct*100)
                msg = f"\nIRW harvest is greater than the annualized potential by {excess_prct}%."
                warnings.warn(msg)

        # Combine IRW disturbance from salvage logging with normal silviculture operations
        df_irw = pandas.concat([df_irw_salv, df_irw_silv])

        # Create columns if they were not created above i.e.
        # in case there was no IRW harvest at all
        if not "irw_need" in df_irw.columns:
            df_irw["irw_need"] = 0
            df_irw["irw_norm"] = 0

        # Check again whether the irw amount is fully allocated
        assert math.isclose(df_irw['irw_need'].sum(), remain_irw_vol)

        # Check the collateral fuel wood generated
        # How much is this volume as compared to the total volume possible #
        df_irw['irw_frac'] = df_irw['irw_need'] / df_irw['irw_vol']

        # How much firewood would this give us as a collateral product #
        df_irw['fw_colat'] = df_irw['irw_frac'] * df_irw['fw_vol']

        # Subtract from remaining firewood harvest #
        still_remain_fw_vol = remain_fw_vol - df_irw['fw_colat'].sum()
        self.out_var('still_remain_fw_vol', still_remain_fw_vol)
        colat_prct = (df_irw['fw_colat'].sum() / remain_fw_vol) * 100
        msg = f"Remaining FW demand after salvage: {remain_fw_vol:.0f} m3."
        msg += f" Collateral FW generated by IRW harvesting: {df_irw['fw_colat'].sum():.0f} m3 "
        msg += f"i.e. represents {colat_prct:.0f}% of the remaining FW demand."
        self.parent.log.info(msg)

        # If there is no extra firewood needed, set to zero #
        if still_remain_fw_vol <= 0.0:
            still_remain_fw_vol = 0.0
        else:
            if df_fw['fw_vol'].sum() == 0.0:
                msg = "There is remaining fw harvest this year:"
                msg += f"{round(still_remain_fw_vol)} m3, "
                msg += "but there are no events that enable the creation of fw only."
                raise Exception(msg)

        # If there is still firewood to satisfy, distribute it evenly
        # Note: in case `still_remain_fw_vol` is equal to zero,
        # the events amount equal to zero will be filtered out later
        df_fw['fw_norm'] = df_fw['fw_avail'] / df_fw['fw_avail'].sum()
        df_fw['fw_need'] = still_remain_fw_vol * df_fw['fw_norm']
        assert math.isclose(df_fw['fw_need'].sum(), still_remain_fw_vol)

        potential_fw = df_fw['fw_avail'].sum()
        if potential_fw == 0:
            msg = f"Annualized potential FW disturbances is {potential_fw} "
            msg += f"and still remaining potential is {still_remain_fw_vol}."
        else:
            harvest_pot_percent = still_remain_fw_vol / potential_fw
            msg = f"Still remaining FW demand represents {harvest_pot_percent*100:.0f}% "
            msg += "of FW available by regular silvicultural practices."
        self.parent.log.info(msg)

        # The user is free to over allocate fw, but will be a warning if the
        # allocation is over the potential annualized availability.
        if  still_remain_fw_vol > potential_fw:
            excess_prct = still_remain_fw_vol / potential_fw - 1
            excess_prct = round(excess_prct*100)
            msg = "\nStill remaining fuel wood harvest is greater than "
            msg += "the annualized potential FW disturbances."
            msg += f"by {excess_prct}%. "
            warnings.warn(msg)

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
        cols = ['year'] +  self.classif_list

        # Prepare the remaining missing columns for the events #
        df['measurement_type'] = 'M'
        df['step'] = timestep
        df = df.rename(columns={'disturbance_type': 'dist_type_name'})

        # Save some columns of this dataframe as a CSV in the output
        self.out_var('tot_irw_vol_avail', df['irw_avail'].sum())
        self.out_var('tot_fw_vol_avail',  df['fw_avail'].sum())

        # Select which events columns appear in the output record
        # Note: dist_type_name is already an input dist id (not an internal dist id)
        # It will not be converted by the outputdata.__setitem__() method
        cols += ['dist_type_name', 'product_created', 'dist_interval_bias',
                 'using_id', 'sw_start', 'sw_end', 'hw_start', 'hw_end',
                 'min_since_last_dist', 'max_since_last_dist', 'last_dist_id',
                 'sort_type', 'measurement_type', 'efficiency', 'wood_density',
                 'bark_frac', 'irw_avail', 'fw_avail',
                 'irw_norm', 'irw_need', 'irw_frac',
                 'fw_colat', 'fw_norm', 'fw_need', 'amount']
        if 'skew' in df.columns:
            cols += ['skew']
        # Write the events to an output file for the record
        self.runner.output.events = pandas.concat([self.runner.output.events, df[cols]])

        # Get only the right columns in the dataframe to send to `libcbm` #
        cols = self.runner.input_data['events'].columns
        df = df[cols].copy()

        # Create disturbances and send the events to libcbm
        dyn_proc = sit_cbm_factory.create_sit_rule_based_processor(
            self.sit,
            self.cbm,
            reset_parameters = False,
            sit_events = df
        )

        # Run the dynamic rule based processor #
        cbm_vars = dyn_proc.pre_dynamics_func(timestep, cbm_vars)

        # Print a message #
        msg = f"Time step {timestep} (year {self.year}) is about to finish.\n"
        self.parent.log.info(msg)

        # Return #
        return cbm_vars

    @property
    def growth_modifier(self):
        """Growth modifier"""
        return GrowthModifier(self)

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
        """Store summary information into output extras.csv"""
        self.runner.output.extras.loc[self.year, key] = value
