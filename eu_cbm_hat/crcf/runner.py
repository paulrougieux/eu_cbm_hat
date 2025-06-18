import logging

from autopaths.auto_paths import AutoPaths

from plumbing.cache  import property_cached
from plumbing.common import camel_to_snake
from plumbing.logger import create_file_logger

from eu_cbm_hat                     import eu_cbm_data_dir
from eu_cbm_hat.cbm.simulation      import Simulation
from eu_cbm_hat.launch.create_json  import CreateJSON
from eu_cbm_hat.launch.associations import Associations
from eu_cbm_hat.info.orig_data      import OrigData

# all_country_codes = pandas.read_csv(eu_cbm_data_dir + 'common/country_codes.csv')
# ref_years = pandas.read_csv(eu_cbm_data_dir + 'common/reference_years.csv')


class AIDB:
    all_paths = '/config/aidb.db'
    def __init__(self, data_dir):
        self.paths = AutoPaths(data_dir, self.all_paths)

class InputData:
    all_paths = """
    /input/csv/
    /input/csv/age_classes.csv
    /input/csv/classifiers.csv
    /input/csv/disturbance_types.csv
    /input/csv/events.csv
    /input/csv/inventory.csv
    /input/csv/transitions.csv
    /input/csv/growth_curves.csv
    """
    def __init__(self, input_dir):
        self.paths = AutoPaths(input_dir, self.all_paths)

class Country:
    def __init__(self, iso2_code):
        self.iso2_code = iso2_code
        self.data_dir  = f'{eu_cbm_data_dir}/countries/{self.iso2_code}'
        self.aidb      = AIDB(self.data_dir)
    @property_cached
    def associations(self):
        return Associations(self)
    @property_cached
    def orig_data(self):
        return OrigData(self)

class Output:
    def __init__(self, parent):
        # classifiers
        classifiers_ids = parent.simulation.sit.classifier_value_ids
        classifiers     = parent.simulation.cbm_output.classifiers.to_pandas()
        value2id        = {v: k for m in classifiers_ids.values() for k, v in m.items()}
        classifiers     = classifiers.set_index(['identifier', 'timestep'])
        classifiers     = classifiers.replace(value2id)
        classifiers     = classifiers.reset_index()
        # data
        area            = parent.simulation.cbm_output.area.to_pandas()
        flux            = parent.simulation.cbm_output.flux.to_pandas()
        parameters      = parent.simulation.cbm_output.parameters.to_pandas()
        pool            = parent.simulation.cbm_output.pools.to_pandas()
        state           = parent.simulation.cbm_output.state.to_pandas()
        on_cols         = ['identifier', 'timestep']
        self.table      = (classifiers
                            .merge(area,       how='left', on=on_cols)
                            .merge(parameters, how='left', on=on_cols)
                            .merge(state,      how='left', on=on_cols)
                            .merge(pool,       how='left', on=on_cols)
                            .merge(flux,       how='left', on=on_cols)
                          )
        self.table.columns = self.table.columns.to_series().apply(camel_to_snake)
    def save(self, filename):
        self.table.to_csv(filename, index=False)

class Runner:
    all_paths = """
    /input/
    /input/json/config.json
    /runner.log
    /cbm_output.csv
    """
    def __init__(self, path, country_iso2_code, num_timesteps=1, logger=None):
        self.short_name    = country_iso2_code
        self.num_timesteps = num_timesteps
        self.country       = Country(country_iso2_code)
        self.input_data    = InputData(path)
        self.paths         = AutoPaths(path, self.all_paths)
        self.log           = create_file_logger(self.country.iso2_code, self.paths.log, console_level='debug') if logger is None else logging.getLogger(logger)
    @property_cached
    def create_json(self):
        return CreateJSON(self)
    @property_cached
    def simulation(self):
        return Simulation(self)
    @property_cached
    def cbm_output(self):
        return Output(self)
    def run(self, output:str=None, interrupt_on_error=True):
        self.create_json()
        self.log.info("Running simulation")
        self.simulation(interrupt_on_error)
        self.log.info("Simulation finished")
        if output is not None:
            self.log.info(f"Writing output to {output}")
            self.cbm_output.save(output)
        else:
            return self.cbm_output.table