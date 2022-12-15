#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# Third party modules #
import pandas

# First party modules #
from plumbing.cache import property_cached
from plumbing.common import camel_to_snake

# Internal modules #

###############################################################################
class Fluxes:
    """
    Access to the information about fluxes that each disturbance creates.
    This data is extracted from the AIDB.

    Example use check that clear cut disturbances are the ones that remove most of the merch biomass:

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['hat'].runners['ZZ'][-1]
        >>> # Run at least one present time step so that SIT is available
        >>> runner.num_timesteps = runner.country.base_year - runner.country.inventory_start_year + 1
        >>> runner.run()
        >>> # Rank fluxes to merchantable pool to check clear cut disturbances
        >>> # are actually the ones with the highest proportion in the dist matrix
        >>> cols = ['user_name', 'silv_practice', 'hardwood_merch_prod_prop', 'softwood_merch_prod_prop']
        >>> runner.fluxes.df.sort_values("hardwood_merch_prod_prop", ascending=False)[cols]

    """

    def __init__(self, runner, debug=False):
        # Default attributes #
        self.runner = runner
        # Shortcuts #
        self.country = self.runner.country
        self.aidb = self.country.aidb
        # Extra attributes #
        self.debug = debug

    @property_cached
    def df(self):
        # The link between the internal sit_id and the external user_id #
        sit_usr = self.runner.simulation.sit.disturbance_id_map
        df = pandas.DataFrame.from_dict(sit_usr, orient='index',
                                        columns=['user_id'])
        df = df.rename_axis('sit_id')
        df = df.reset_index()

        # Then the user_id is mapped to a user_desc #
        usr_desc = self.country.orig_data['disturbance_types']
        usr_desc = usr_desc.rename(columns={'dist_type_name':'user_id'})
        df = pandas.merge(df, usr_desc, on='user_id', how='left')
        df = df.rename(columns={'dist_desc_input':'user_name'})

        # The user_desc is mapped to an aidb_name #
        desc_name = self.country.associations.key_to_rows('MapDisturbanceType')
        desc_name = pandas.DataFrame.from_dict(desc_name, orient='index',
                                               columns=['aidb_name'])
        df = pandas.merge(df, desc_name, how='left',
                          left_on='user_name', right_index=True)

        # The aidb_name is mapped to an aidb_id #
        name_id = self.country.aidb.db.read_df('disturbance_type_tr')
        name_id = name_id.rename(columns={'disturbance_type_id': 'aidb_id'})
        name_id = name_id.set_index('name')['aidb_id']
        df = pandas.merge(df, name_id, how='left',
                          left_on='aidb_name', right_index=True)

        # The aidb_id is mapped to a flux matrix_id #
        table = 'disturbance_matrix_association'
        id_matrix = self.country.aidb.db.read_df(table)
        mapping = {'disturbance_type_id':   'aidb_id',
                   'disturbance_matrix_id': 'matrix_id'}
        id_matrix = id_matrix.rename(columns = mapping)
        id_matrix = id_matrix.groupby(['aidb_id'])
        id_matrix = id_matrix.agg({'matrix_id': 'unique'}).reset_index()
        assert all(id_matrix['matrix_id'].apply(len) == 1)
        id_matrix = id_matrix.explode('matrix_id')
        df = pandas.merge(df, id_matrix, on='aidb_id', how='left')

        # Get the ID numbers of every pool, especially `products` pool #
        pool_ids = self.country.aidb.db.read_df('pool')
        pool_ids = pool_ids.rename(columns={'id':   'pool_id',
                                            'code': 'pool_name'})
        prod_id = pool_ids.query('pool_name == "Products"')['pool_id'].item()

        # Take all matrices and keep only fluxes going to `products` pools #
        mtxs = self.country.aidb.db.read_df('disturbance_matrix_value')
        mtxs = mtxs.rename(columns={'disturbance_matrix_id': 'matrix_id'})
        mtxs = mtxs.query('sink_pool_id == %i' % prod_id)
        mtxs = mtxs.drop(columns='sink_pool_id')
        mtxs = mtxs.rename(columns={'source_pool_id': 'pool_id'})

        # Replace IDs by names of pools and pivot #
        mtxs = pandas.merge(mtxs, pool_ids, on='pool_id')
        mtxs = mtxs.drop(columns = 'pool_id')
        mtxs = mtxs.pivot(index   = 'matrix_id',
                          columns = 'pool_name',
                          values  = 'proportion')
        mtxs = mtxs.fillna(0)
        mtxs = mtxs.reset_index()

        # Optional debug message #
        if self.debug:
            msg = "Movements to the `products` pool are coming exclusively" \
                  " form the pools listed below (for the AIDB at '%s').\n\n"
            cols = list(mtxs.columns)
            cols.pop(cols.index('matrix_id'))
            msg += ', '.join(cols)
            print(msg % self.aidb.repo_file)

        # Add pool columns to df #
        df = pandas.merge(df, mtxs, on='matrix_id', how='left')
        df = df.fillna(0)

        # Modify column names #
        df.columns = df.columns.to_series().apply(camel_to_snake)
        from eu_cbm_hat.cbm.dynamic import DynamicSimulation
        sources   = DynamicSimulation.sources
        self.cols = [pool + '_prod_prop' for pool in sources]
        mapping   = dict(zip(sources, self.cols))
        df        = df.rename(columns = mapping)

        # We always want to have the eight source pool columns #
        for pool in self.cols:
            if pool not in df.columns: df[pool] = 0.0

        # The name we will be using for the join #
        df = df.rename(columns={'sit_id': 'disturbance_type'})

        # Return #
        return df
