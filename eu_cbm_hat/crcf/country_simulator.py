import os
import shutil
import pandas

from plumbing.logger import create_file_logger

from eu_cbm_hat import eu_cbm_data_dir
from eu_cbm_hat.crcf import Runner
from eu_cbm_hat.crcf.driver_netcdf import Netcdf
from eu_cbm_hat.crcf.driver_database import Database




class CountrySimulator:
    """
    Extract all unique stand-event combinations from the eu-cbm-data dataset.
    Store these combinations in a database file.
    Run simulations for each individual stand and save the results in a NetCDF file.

    How to run:
        >>> from eu_cbm_hat.crcf import CountrySimulator
        >>> country_code = 'FI'
        >>> output_dir   = 'results'
        >>> obj = CountrySimulator()
        >>> obj.run(country_code, output_dir)
    """

    classifiers = 'status,forest_type,region,mgmt_type,mgmt_strategy,climate,con_broad,site_index,growth_period'.split(',')
    columns_events = 'status,forest_type,region,mgmt_type,mgmt_strategy,climate,con_broad,site_index,growth_period,using_id,sw_start,sw_end,hw_start,hw_end,min_since_last_dist,max_since_last_dist,last_dist_id,min_tot_biom_c,max_tot_biom_c,min_merch_soft_biom_c,max_merch_soft_biom_c,min_merch_hard_biom_c,max_merch_hard_biom_c,min_tot_stem_snag_c,max_tot_stem_snag_c,min_tot_soft_stem_snag_c,max_tot_soft_stem_snag_c,min_tot_hard_stem_snag_c,max_tot_hard_stem_snag_c,min_tot_merch_stem_snag_c,max_tot_merch_stem_snag_c,min_tot_merch_soft_stem_snag_c,max_tot_merch_soft_stem_snag_c,min_tot_merch_hard_stem_snag_c,max_tot_merch_hard_stem_snag_c,efficiency,sort_type,measurement_type,amount,dist_type_name,step'.split(',')

    def __init__(self,
                 path_cache:str='cache',
                 scenario:str='reference',
                 num_timesteps:int=200,
                ):

        self.cache = path_cache
        self.scenario = scenario
        self.num_timesteps = num_timesteps

        self.log = None
        self.country = None


    def init_libcbm_input_files(self):

        # copy default files
        shutil.copyfile(f'{eu_cbm_data_dir}/countries/{self.country}/common/age_classes.csv', f'{self.cache}/input/csv/age_classes.csv')
        shutil.copyfile(f'{eu_cbm_data_dir}/countries/{self.country}/common/classifiers.csv', f'{self.cache}/input/csv/classifiers.csv')
        shutil.copyfile(f'{eu_cbm_data_dir}/countries/{self.country}/common/disturbance_types.csv', f'{self.cache}/input/csv/disturbance_types.csv')

        # growth_curves.csv
        self.write_growth_curves()

        # transitions.csv (empty file)
        with open(f'{eu_cbm_data_dir}/countries/{self.country}/activities/mgmt/transitions.csv') as ff:
            header = ff.readline()
        with open(f'{self.cache}/input/csv/transitions.csv', 'w') as ff:
            ff.write(header)


    def write_growth_curves(self):
        ds = pandas.read_csv(f'{eu_cbm_data_dir}/countries/{self.country}/activities/mgmt/growth_curves.csv', dtype=str)
        ds = ds[ds['scenario'] == self.scenario].drop(columns=['scenario'])
        ds.to_csv(f'{self.cache}/input/csv/growth_curves.csv', index=False)


    def read_growth_curves(self)->pandas.DataFrame:
        ds = pandas.read_csv(f'{eu_cbm_data_dir}/countries/{self.country}/activities/mgmt/growth_curves.csv', dtype=str)
        ds = ds[ds['scenario'] == self.scenario].drop(columns=['scenario'])
        unique = ds.drop_duplicates(subset=self.classifiers)
        return unique


    def read_classifiers(self)->dict:

        # read eu_cbm_hat classifiers.csv
        df0 = pandas.read_csv(f'{eu_cbm_data_dir}/countries/{self.country}/common/classifiers.csv')

        # data to dict
        classifiers = {}
        for ii in df0['classifier_number'].unique():
            df1  = df0[df0['classifier_number']==ii]
            name = df1.loc[df1['classifier_value_id']=='_CLASSIFIER', 'name'].item()
            classifiers[name] = {}
            for _, hh in df1.loc[df1['classifier_value_id']!='_CLASSIFIER', ['classifier_value_id', 'name']].iterrows():
                classifiers[name][hh['classifier_value_id']] = hh['name']

        return classifiers


    def read_disturbance_types(self)->dict:
        ds = pandas.read_csv(f'{eu_cbm_data_dir}/countries/{self.country}/common/disturbance_types.csv', dtype=str)
        ds = ds.set_index(ds.columns[0])[ds.columns[1]].to_dict()
        ds = {'-1': 'none'} | ds
        return ds


    def read_events(self)->pandas.DataFrame:
        ds = pandas.read_csv(f'{eu_cbm_data_dir}/countries/{self.country}/activities/mgmt/events.csv', dtype=str)
        ds = ds[ds['scenario'] == self.scenario].drop(columns=['scenario'])
        return ds


    def read_inventory(self)->pandas.DataFrame:

        ds = pandas.read_csv(f'{eu_cbm_data_dir}/countries/{self.country}/activities/mgmt/inventory.csv', dtype=str)
        ds = ds[ds['scenario'] == self.scenario].drop(columns=['scenario'])
        ds = ds.iloc[ds[self.classifiers].drop_duplicates().index]

        ds.loc[:, 'using_id'] = False
        ds.loc[:, 'age'] = 1
        ds.loc[:, 'area'] = 100.0

        return ds


    def write_empty_events(self):
        with open(f'{self.cache}/input/csv/events.csv', 'w') as ff:
            ff.write(','.join(self.columns_events) + '\n')


    def allowed_disturbances(self):

        # read eu_cbm_hat disturbance_types.csv
        dist = self.read_disturbance_types()

        # False for events involving fire, wind, insects
        allowed = {}
        for key, value in dist.items():
            value = value.lower()
            if 'fire' in value or 'wind' in value or 'insect' in value:
                allowed[key] = False
            else:
                allowed[key] = True

        return allowed


    def find_corresponding_rows(self, df_to_search:pandas.DataFrame, df_reference:pandas.Series)->pandas.DataFrame:

        # replace '?' with df_reference corresponding values
        tmp = df_to_search.copy()
        for label in self.classifiers:
            tmp.loc[tmp[label]=='?', label] = df_reference[label]

        # rows in df_to_search corresponding to df_reference[self.classifiers]
        ds = tmp[tmp[self.classifiers[:-1]].eq(df_reference[self.classifiers[:-1]]).all(axis=1)].reset_index()

        return ds


    def find_init_curr_curves_indices(self, curves:pandas.DataFrame, stand:pandas.Series)->tuple:

        # corresponding rows
        df = self.find_corresponding_rows(curves, stand)
        if len(df) > 2:
            self.log.error(f'found more than 2 corresponding growth curves\n\n{df}')
            raise ValueError(f'found more than 2 corresponding growth curves\n\n{df}')

        # cur and init curves indices
        ds0 = df.loc[df['growth_period'] == 'Init', 'index']
        ds1 = df.loc[df['growth_period'] == 'Cur', 'index']
        index_init = -1 if len(ds0) == 0 else ds0.item()
        index_curr = -1 if len(ds1) == 0 else ds1.item()

        return index_init, index_curr


    def run(self, country_code:str, output_dir:str, dry_run:bool=False):

        # set country code
        self.country = country_code

        # logger
        logger_name = country_code
        log_file    = f'{output_dir}/simulations_{country_code}.log'
        self.log    = create_file_logger(logger_name, log_file, console_level='debug')

        # retrieve eu-cbm-hat info
        curves = self.read_growth_curves()
        stands = self.read_inventory()
        events = self.read_events()
        dist   = self.allowed_disturbances()

        # init database
        path_db = f'sqlite:///{output_dir}/simulations_{self.country}.db'
        db = Database(path_db)
        db.init(self.read_classifiers(), self.read_disturbance_types())

        # init env for eu-cbm-hat computations
        if not dry_run:

            # create cache folder
            os.makedirs(f'{self.cache}/input/csv', exist_ok=True)

            # init libcbm input files
            self.init_libcbm_input_files()

            # netcdf instance
            nc = Netcdf(f'{output_dir}/simulations_{self.country}.nc')

        # avoid duplicate eu-cbm-hat simulation runs.
        # sidx = list[idx_sim], where idx_sim =
        # (idx row growth curve init, idx row growth curve curr, idx row event)
        sidx = []

        # loop on species
        for _, stand in stands.iterrows():

            # =====================
            #     simple growth
            # =====================

            # log
            self.log.info('==========')
            self.log.info(f'eu_cbm_hat on {",".join([str(ii) for ii in stand[self.classifiers[:-1]].to_list()])}')
            self.log.info('==========')

            # add species to db
            id_species = db.add_commit_species(stand)

            # assemble idx_sim
            idx_curve = self.find_init_curr_curves_indices(curves, stand)
            idx_sim   = idx_curve + (-1,)

            if idx_sim not in sidx:

                # add simulation to db
                db.add_simulation(id_species, '-1', -1, len(sidx))
                sidx.append(idx_sim)

                # cbm simulation
                if not dry_run:

                    # write libcbm inventory.csv and events.csv files
                    stand.to_frame().T.to_csv(f'{self.cache}/input/csv/inventory.csv', index=False)
                    self.write_empty_events()

                    # run cbm
                    table = Runner(self.cache, self.country, self.num_timesteps, logger_name).run()
                    for classif in self.classifiers:
                        table[classif] = table[classif].replace(db.classifier_ids(classif))

                    # eventually init netcdf
                    if not nc.is_init:
                        nc.init(self.num_timesteps+1, table.columns)

                    # write to netcdf
                    nc.write_simulation(table.to_numpy())
            
            else:

                # add simulation to db
                db.add_simulation(id_species, '-1', -1, sidx.index(idx_sim))
                self.log.info('Previously computed')


            # ============
            #     mgmt
            # ============

            # unique events
            ds = self.find_corresponding_rows(events, stand)
            oo = 'sw_start,hw_start,dist_type_name'.split(',')
            ds = ds.iloc[ds[oo].drop_duplicates().index]

            # loop on events
            for _, evt in ds.iterrows():

                # name and timestep
                evt_name = evt['dist_type_name']
                evt_step = '1' if evt["sw_start"] == '0' else evt["sw_start"]

                # eventually skip if not allowed disturbance
                if not dist[evt_name]:
                    continue

                # log
                self.log.info('==========')
                self.log.info(f'eu_cbm_hat on {",".join([str(ii) for ii in stand[self.classifiers[:-1]].to_list()])},{evt_name},{evt_step}')
                self.log.info('==========')

                # assemble idx_sim
                idx_sim = idx_curve + (evt['index'],)

                if idx_sim not in sidx:

                    # add simulation to db
                    db.add_simulation(id_species, evt_name, evt_step, len(sidx))
                    sidx.append(idx_sim)

                    # cbm simulation
                    if not dry_run:

                        # build data for events.csv
                        # add [sort_type, measurement_type, amount, evt_name, evt_step]
                        data  = evt[self.columns_events[:-5]].to_list()
                        data += [1, 'P', 1, evt_name, evt_step]

                        # write events.csv
                        df = pandas.DataFrame([data], columns=self.columns_events)
                        df.to_csv(f'{self.cache}/input/csv/events.csv', index=False)

                        # run cbm
                        table = Runner(self.cache, self.country, self.num_timesteps, logger_name).run()
                        for classif in self.classifiers:
                            table[classif] = table[classif].replace(db.classifier_ids(classif))

                        # write to netcdf
                        nc.write_simulation(table.to_numpy())

                else:

                    # add simulation to db
                    db.add_simulation(id_species, evt_name, evt_step, sidx.index(idx_sim))
                    self.log.info('Previously computed')

            # commit
            db.commit()

        # close db
        db.close()

        # clean cache
        if os.path.exists(self.cache):
            shutil.rmtree(self.cache)

        # log
        self.log.info('Normal termination')