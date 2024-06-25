#!/usr/bin/env python
# coding: utf-8
# %%
import pandas as pd

# %%
# #Explore solutions for harvest volume
# 
# Step1. Run "harvest_exp_prov_all_countries" script, save the output file "harv_reference.csv", then extract the timeseries values of IRW only, "tot_irw_vol_avail". 
# 
# Step2. Replace these values in 'eu_cbm_data/domestic_harvest/irw_demand.csv, and run again.
# 
# Step3. Do Step1 again, save "harv_first_interation. csv", then Step2 again. In the reference file, to compare the values for "tot_irw_vol_avail"
# 
# Step4, Step 5, ..... until the difference between succesive outputs of "tot_irw_vol_avail" are within +/- 5% for entire time series. 

# # Iterations with IRW

# %%
from eu_cbm_hat.core.continent import continent
from eu_cbm_hat.post_processor.agg_combos import harvest_exp_prov_all_countries
import pandas
pandas.set_option('display.precision', 0) # Display rounded numbers
harv_data = harvest_exp_prov_all_countries("reference", "year")


# %%


continent.output_dir


# %%


# print the output file
#harv_data.to_csv(continent.output_dir + "harv_mws.csv", mode='w',index=False, header = True)


# %%


#reload csv file
irw_data = pd.read_csv(continent.output_dir + "harv_mws.csv")

#keep only relevant columns with "tot_irw_vol_avail", and divide by 1000 
irw_data = irw_data[['country', 'year', 'tot_irw_vol_avail']]
irw_data['tot_irw_vol_avail']=irw_data['tot_irw_vol_avail']/1000

# keep only data after 2021
irw_data=irw_data[irw_data['year']> 2021]


# %%


irw_data_wide = pd.pivot(irw_data, index='country', columns='year', values=['tot_irw_vol_avail']).fillna(0)
irw_data_wide=irw_data_wide.astype(int)#.reset_index()
# remove the first level of header
#irw_data_wide = irw_data_wide.droplevel(0, axis=1)


# %%


irw_data_wide


# %%


#irw_data_wide=irw_data_wide.reset_index()
#irw_data_wide=irw_data_wide.str.replace('tot_irw_vol_avail';'value_')

irw_data_wide1 = irw_data_wide.apply(lambda x: x.replace({'tot_irw_vol_avail':'value_'}, regex=True))
irw_data_wide1


# %%


# add missing elements
irw_data_wide['faostat_name'] = 'Industrial roundwood'
irw_data_wide['element'] = 'Production'
irw_data_wide['unit'] = '1000m3'

# include country as column

irw_data_wide=irw_data_wide[['faostat_name',      'element',         'unit',  'year',       2022,           2023,           2024,           2025,
                 2026,           2027,           2028,           2029,
                 2030,           2031,           2032,           2033,
                 2034,           2035,           2036,           2037,
                 2038,           2039,           2040,           2041,
                 2042,           2043,           2044,           2045,
                 2046,           2047,           2048,           2049,
                 2050,           2051,           2052,           2053,
                 2054,           2055,           2056,           2057,
                 2058,           2059,           2060,           2061,
                 2062,           2063,           2064,           2065,
                 2066,           2067,           2068,           2069,
                 2070, ]]


# %%


irw_data_wide


# %%


#paste it in the input file, while keeping a copy of the orignal values
C:\CBM\eu_cbm_data\domestic_harvest\continous_cover


# # Check of the sink

# sink should be close to zero

# %%


from eu_cbm_hat.post_processor.sink import sink_one_country
sink_y = sink_one_country(""reference", "LU", groupby="year")


# %%


#sink_y.plot('year', 'living_biomass_sink')


# %%




