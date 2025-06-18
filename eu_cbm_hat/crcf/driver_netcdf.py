import numpy as np
from netCDF4 import Dataset



class Netcdf:

    def __init__(self, file_path:str):
        self.file = file_path
        self.is_init = False


    def init(self, num_timesteps:int, columns:list[str], cmp:str='zlib'):

        self.is_init = True

        # max length column labels
        nchrs = 0
        for label in columns:
            nchrs = max(nchrs, len(label))

        # init netcdf
        with Dataset(self.file, 'w') as nc:

            nc.createDimension('timestep', num_timesteps)
            nc.createDimension('column', len(columns))
            nc.createDimension('simulation', None)
            nc.createDimension('nchrs', nchrs)

            vlab = nc.createVariable('column_labels', 'S1', ('column', 'nchrs'), compression=cmp)
            vlab._Encoding = 'ascii'
            vlab[:] = np.array(columns, dtype=f'S{nchrs}')

            vsim = nc.createVariable('sim', 'f8', ('simulation', 'timestep', 'column'), compression=cmp)
            vsim.full_name = 'eu-cbm-hat simulations'


    def write_simulation(self, data:np.ndarray):
        with Dataset(self.file, 'a') as nc:
            idx = nc['sim'].shape[0]
            nc['sim'][idx] = data