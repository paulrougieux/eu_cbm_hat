---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.16.2
  kernelspec:
    display_name: susbiom_trade_kernel
    language: python
    name: susbiom_trade_kernel
---

This script allows expanding the calibration period based on FAO data. To be used for updating post-2020 years. There will be several steps.

In the first step, from the reference scenario run by 2020, keep manually only A based NDs in events.csv identified under new scenario name, e.g., "reference_fao". This is needed to determine the irw and fw volume ub associated to A based disturbances.

Second run will implement the IRW demand only corrected by the IRW provided from A based disturbances and as of the same years, 2021 and 2022 of the "reference" scenario. This run will only include "irw_only" silvicultural practices. 

Third run, with fw from A and IRW runs, correct the fw_demand and apply it to silviculture.  

CHECK the list of nat dist!

Once added the 2nd scenario in events.csv for the calibration period, the additional years would be run as empty years. Solution: do not rerun "reference" again.

```python
import pandas as pd
import numpy as np
```

```python
from eu_cbm_hat.core.continent import continent
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ub
# instantiate the object
# for IRW and NDs
scenario = 'reference'
# for FW runs
#scenario = 'reference_update_fao'
combo = continent.combos[scenario]
r = combo.runners['ES'][-1]
reference_year = r.country.inventory_start_year
country_name = r.country.country_name
country_iso2 = r.country.iso2_code
```

## FIRST RUN: after A-only run retrive the IRW VOLUME corresponding to AREA based natural disturbances in pre_2020 for refrence scenario

```python
irw_frac = r.silv.irw_frac.raw
irw_frac = irw_frac.query('(softwood_merch != 0) | (softwood_other != 0) | (softwood_stem_snag != 0) | (softwood_branch_snag != 0)')
irw_frac=irw_frac.drop(columns=['dist_type_name', 'climate', 'growth_period'])
#irw_frac = irw_frac.rename(columns = {'disturbance_type':'dist_type_name'})
irw_frac['disturbance_type']= irw_frac['disturbance_type'].astype(int)
#irw_frac ['site_index']= irw_frac ['site_index'].astype(int)
irw_frac = irw_frac[irw_frac['scenario'] == scenario]
```

```python
columns_to_modify = ['softwood_merch','softwood_other','softwood_stem_snag', 'softwood_branch_snag','hardwood_merch','hardwood_other', 'hardwood_stem_snag', 'hardwood_branch_snag']
for col in columns_to_modify:
    irw_frac=irw_frac.rename(columns={col: col + "_irw_frac"})
irw_frac.iloc[[0,-1]]
```

```python
# check disturbance list
irw_frac['disturbance_type'].unique()
```

```python
#irw_frac['disturbance_type']=irw_frac['disturbance_type'].str.replace('501', '50')
irw_frac.loc[irw_frac['disturbance_type'] == 501, 'disturbance_type'] = 50
irw_frac['disturbance_type'].unique()
```

```python
# import wood density data
# import the constant values of wood density from vol_to_mass_coefs.csv from \silv\
wd_coefs = r.silv.coefs.raw
wd_coefs_data=wd_coefs[['forest_type', 'wood_density', 'bark_frac']]
```

```python
#load simulated outputs
pools_fluxes_data = r.output.pool_flux
pools_fluxes_data.iloc[[0,-1]]
pools_fluxes_data=pools_fluxes_data.query(' year <= 2030')
print(pools_fluxes_data.disturbance_type.unique())
len(pools_fluxes_data)
```

```python
# checks right split of soft and hard on con and broad
grouping_sp = pools_fluxes_data.groupby ('forest_type')['con_broad'].unique()
#grouping_sp
```

```python
#only_nat_dist_4 = pools_fluxes_data[pools_fluxes_data['disturbance_type'].astype(str).str.startswith('4')]
#only_nat_dist_5 = pools_fluxes_data[pools_fluxes_data['disturbance_type'].astype(str).str.startswith('5')]
#only_nat_dist = pd.concat([only_nat_dist_4,only_nat_dist_5])
#len(only_nat_dist)
```

```python
#list(only_nat_dist.columns)
#only_nat_dist['disturbance_type'].unique()
#only_nat_dist['dist_type_name'].unique()
```

```python
# merge with irw
df = pd.merge(pools_fluxes_data, irw_frac, how = 'left', on = ['status', 'forest_type', 'region', 'mgmt_type', 'mgmt_strategy', 'con_broad', 'disturbance_type', 'site_index'])#.dropna()
```

```python
df.disturbance_type.unique()
```

```python
df['softwood_merch_irw'] = df['softwood_merch_to_product'] * df['softwood_merch_irw_frac']
df['softwood_other_irw'] = df['softwood_other_to_product'] * df['softwood_other_irw_frac']
df[ 'softwood_stem_snag_irw'] = df[ 'softwood_stem_snag_to_product'] * df['softwood_stem_snag_irw_frac']
df[ 'softwood_branch_snag_irw'] = df[ 'softwood_branch_snag_to_product'] * df[ 'softwood_branch_snag_irw_frac']
df[ 'hardwood_merch_irw'] = df[ 'hardwood_merch_to_product'] * df[ 'hardwood_merch_irw_frac']
df[ 'hardwood_other_irw'] = df[ 'hardwood_other_to_product'] * df[ 'hardwood_other_irw_frac']
df['hardwood_stem_snag_irw'] = df['hardwood_stem_snag_to_product'] * df[ 'hardwood_stem_snag_irw_frac']
df[ 'hardwood_branch_snag_irw']= df[ 'hardwood_branch_snag_to_product'] * df['hardwood_branch_snag_irw_frac']

df['softwood_merch_fw'] = df['softwood_merch_to_product'] * (1-df['softwood_merch_irw_frac'])
df['softwood_other_fw'] = df['softwood_other_to_product'] * (1-df['softwood_other_irw_frac'])
df[ 'softwood_stem_snag_fw'] = df[ 'softwood_stem_snag_to_product'] * (1-df['softwood_stem_snag_irw_frac'])
df[ 'softwood_branch_snag_fw'] = df[ 'softwood_branch_snag_to_product'] * (1-df[ 'softwood_branch_snag_irw_frac'])
df[ 'hardwood_merch_fw'] = df[ 'hardwood_merch_to_product'] * (1-df[ 'hardwood_merch_irw_frac'])
df[ 'hardwood_other_fw'] = df[ 'hardwood_other_to_product'] * (1-df[ 'hardwood_other_irw_frac'])
df['hardwood_stem_snag_fw'] = df['hardwood_stem_snag_to_product'] * (1-df[ 'hardwood_stem_snag_irw_frac'])
df[ 'hardwood_branch_snag_fw']= df[ 'hardwood_branch_snag_to_product'] * (1-df['hardwood_branch_snag_irw_frac'])

#rename instead of soft hard to con borad
df['prod_irw'] = df['softwood_merch_irw'] + df['softwood_other_irw'] + df[ 'softwood_stem_snag_irw']+df['softwood_branch_snag_irw'] + df[ 'hardwood_merch_irw']+df[ 'hardwood_other_irw'] + df['hardwood_stem_snag_irw'] + df['hardwood_branch_snag_irw']
df['prod_fw'] = df['softwood_merch_fw'] + df['softwood_other_fw'] + df[ 'softwood_stem_snag_fw']+df['softwood_branch_snag_fw'] + df['hardwood_merch_fw']+df[ 'hardwood_other_fw'] + df['hardwood_stem_snag_fw'] + df['hardwood_branch_snag_fw']
```

```python
#df.to_csv(continent.base_dir + '/quick_results/' +'detailed_2021_2022_NEW.csv', mode='w', index=False, header=True)
```

**EXTRACT volume for "A" for pre-2020** from "reference" simulation (< 2020)

```python
only_nat_dist_4 = df[df['disturbance_type'].astype(str).str.startswith('4')]
only_nat_dist_5 = df[df['disturbance_type'].astype(str).str.startswith('5')]
only_nat_dist = pd.concat([only_nat_dist_4,only_nat_dist_5])
only_nat_dist=only_nat_dist[only_nat_dist['year']<= 2020]
len(only_nat_dist)
```

```python
selected_columns = [ 'prod_irw', 'prod_fw']
rw_prod_nd = only_nat_dist.groupby(['year', 'forest_type', 'con_broad'])[selected_columns].sum().reset_index()
rw_prod_nd.iloc[[0, -1]]
```

```python
rw_vol_nd = rw_prod_nd.merge(wd_coefs_data, on=['forest_type'])
rw_vol_nd.iloc[[0, -1]]
```

```python
# If the function should behave differently depending on the 'con_broad' value
def apply_ton_carbon_to_m3_ub(row):
    if row['con_broad'] == 'con':
        row['irw_con_m3'] = ton_carbon_to_m3_ub(row, "prod_irw")
        row['fw_con_m3'] = ton_carbon_to_m3_ub(row, "prod_fw")
    elif row['con_broad'] == 'broad':
        row['irw_broad_m3'] = ton_carbon_to_m3_ub(row, "prod_irw")
        row['fw_broad_m3'] = ton_carbon_to_m3_ub(row, "prod_fw")
    return row
        
rw_vol_nd = rw_vol_nd.apply(apply_ton_carbon_to_m3_ub, axis=1)
rw_vol_nd.iloc[[0, -1]]
```

```python
# aggregate
rw_nd_vol = rw_vol_nd.groupby('year').agg(irw_nd_con_m3 = ('irw_con_m3', 'sum'),
                                   fw_nd_con_m3 = ('fw_con_m3', 'sum'),
                                   irw_nd_broad_m3 = ('irw_broad_m3', 'sum'),
                                   fw_nd_broad_m3 = ('fw_broad_m3', 'sum')).reset_index()
```

```python
# average of IRW volume to be applied in 2021 and 2022 for ND areas, to be deducted from IRW_demands
irw_dist_con_nd = rw_nd_vol["irw_nd_con_m3"].mean()
irw_dist_broad_nd = rw_nd_vol["irw_nd_broad_m3"].mean()
fw_dist_con_nd = rw_nd_vol["fw_nd_con_m3"].mean()
fw_dist_broad_nd = rw_nd_vol["fw_nd_broad_m3"].mean()
```

```python
print(irw_dist_con_nd, irw_dist_broad_nd)
```

```python jupyter={"source_hidden": true}
print(fw_dist_con_nd, fw_dist_broad_nd)
```

**Prepare the simulated output in refrence scenario for 2021-2022 to distribute the IRW demands for 2021-2022**

```python
# extract db without NSs
#only_fm_no_dist_4 = df[~df['disturbance_type'].astype(str).str.startswith('4')]
#only_fm_no_dist_4.disturbance_type.unique()
```

```python
#only_fm_dist = only_fm_no_dist_4[~only_fm_no_dist_4['disturbance_type'].astype(str).str.startswith('5')]
#only_fm_dist['disturbance_type']=only_fm_dist['disturbance_type'].astype(int)
```

```python
# select only the relevant years
#only_fm_dist=only_fm_dist.query(' year >= 2021 & year <=2030')
#only_fm_dist.disturbance_type.unique()
```

```python
# extract db without NSs
# select only the new years
only_fm_no_dist_4 = df[~df['disturbance_type'].astype(str).str.startswith('4')]
only_fm_dist = only_fm_no_dist_4[~only_fm_no_dist_4['disturbance_type'].astype(str).str.startswith('5')]
only_fm_dist=only_fm_dist.query(' year >= 2021 & year <=2022 & disturbance_type <23')
only_fm_dist=only_fm_dist.query(' disturbance_type > 10 & disturbance_type <23')
len(only_fm_dist)
```

```python
only_fm_dist.iloc[[0, -1]]#.disturbance_type.unique()
```

```python
# aggregate C fluxes to prod on product type
selected_c_columns = [ 'prod_irw','prod_fw']
clasif_columns = ['year', 'status', 'forest_type', 'region', 'mgmt_type', 'mgmt_strategy', 'con_broad', 'site_index', 'growth_period', 'disturbance_type']

c_fm_prod = only_fm_dist.groupby(clasif_columns)[selected_c_columns].sum()#.set_index(['year','forest_type'])
c_fm_prod = c_fm_prod.loc[~(c_fm_prod==0).all(axis=1)].reset_index()
c_fm_prod.iloc[[0, -1]]
```

```python jupyter={"source_hidden": true}
# add wood density
fm_prod = c_fm_prod.merge(wd_coefs_data, on='forest_type')
fm_prod.iloc[[0, -1]]
```

```python
# If the function should behave differently depending on the 'con_broad' value
def apply_ton_carbon_to_m3_ub(row):
    if row['con_broad'] == 'con':
        row['irw_con_m3'] = ton_carbon_to_m3_ub(row, "prod_irw")
        row['fw_con_m3'] = ton_carbon_to_m3_ub(row, "prod_fw")
    elif row['con_broad'] == 'broad':
        row['irw_broad_m3'] = ton_carbon_to_m3_ub(row, "prod_irw")
        row['fw_broad_m3'] = ton_carbon_to_m3_ub(row, "prod_fw")
    return row
        
rw_vol_fm = fm_prod.apply(apply_ton_carbon_to_m3_ub, axis=1)
rw_vol_fm.iloc[[0, -1]]
```

```python
# organize the output
keep_cols = ['year', 'status', 'forest_type', 'region', 'mgmt_type', 'mgmt_strategy', 'con_broad', 'site_index', 'growth_period', 'disturbance_type', 'irw_con_m3', 'irw_broad_m3'] 
fm_irw_prod = rw_vol_fm[keep_cols]
```

```python
fm_irw_prod.iloc[[0, -1]]
```

## SECOND STEP, correct the IRW demands for 2021 and 2022 with the volume resulted from salvage logging

```python
irw_demand = pd.read_csv('/mnt/eos_rw/home/users/blujdvi/eu_cbm/eu_cbm_data/domestic_harvest/reference/irw_harvest.csv')
irw_demand = irw_demand [irw_demand ['country'] ==  country_name]
```

```python
irw_demand
```

```python
# Assuming 'irw_demand' is`a query object with methods like query() and 'faostat_name' is a property of the query results
irw_demand_con = irw_demand[irw_demand['faostat_name'] == 'Industrial roundwood coniferous']
irw_demand_con=irw_demand_con.reset_index()

# Assuming 'irw_demand' is`a query object with methods like query() and 'faostat_name' is a property of the query results
irw_demand_broad = irw_demand[irw_demand['faostat_name'] == 'Industrial roundwood non-coniferous']
irw_demand_broad=irw_demand_broad.reset_index()
```

```python
# applying get_value() function 
irw_demand_con_2021 = irw_demand_con._get_value(0, 'value_2021')
irw_demand_con_2022=irw_demand_con._get_value(0, 'value_2022')
irw_demand_broad_2021=irw_demand_broad._get_value(0, 'value_2021')
irw_demand_broad_2022=irw_demand_broad._get_value(0, 'value_2022')

# quantities to be distributed
remaining_irw_demand_con_2021 = irw_demand_con_2021 - irw_dist_con_nd
remaining_irw_demand_con_2022 = irw_demand_con_2022 - irw_dist_con_nd
remaining_irw_demand_broad_2021 = irw_demand_broad_2021 - irw_dist_broad_nd
remaining_irw_demand_broad_2022 = irw_demand_broad_2022 - irw_dist_broad_nd
```

```python
# check ND corrected demands
print(0.5*(remaining_irw_demand_con_2021+remaining_irw_demand_con_2022))#, remaining_irw_demand_broad_2021, remaining_irw_demand_broad_2022)
```

## Third step: distribute the IRW con and broad demands based on distribution of reference scenario by HAT and ther structure of events.csv

```python
#upload irw_frac and select the fractions which corresponds to irw_frac, >0
#irw_frac = r.silv.irw_frac.raw
#irw_frac = irw_frac.query('(softwood_merch != 0) | (softwood_other != 0) | (softwood_stem_snag != 0) | (softwood_branch_snag != 0)')
#irw_frac=irw_frac.drop(columns=['dist_type_name', 'climate', 'growth_period'])
#irw_frac = irw_frac.rename(columns = {'disturbance_type':'dist_type_name'})
#irw_frac ['dist_type_name']= irw_frac ['dist_type_name'].astype(int) 
#irw_frac ['site_index']= irw_frac ['site_index'].astype(int)
#irw_frac = irw_frac[irw_frac ['scenario'] == scenario]
```

```python
# import format of events.csv input
#events_input_hist = pd.read_csv('/mnt/eos_rw/home/users/blujdvi/eu_cbm/eu_cbm_data/countries/'+ country_iso2 + '/activities/mgmt/events.csv')
# remove all disturbances based on A
#events_input_hist=events_input_hist[events_input_hist['measurement_type'] != 'A']
#list(events_input_hist.columns)
```

```python
#events_input_hist_4 = events_input_hist[~events_input_hist['dist_type_name'].astype(str).str.startswith('4')]
#events_input_hist_5 = events_input_hist[~events_input_hist['dist_type_name'].astype(str).str.startswith('5')]
#events_input_hist = pd.concat([events_input_hist_4, events_input_hist_5])
```

```python
#import input data on events from calibrated period and merge to irw_frac, so only practices able to provide irw are mantained.
# remove columns for the new years
#events_input_hist = events_input_hist[(events_input_hist['scenario'] == scenario)].dropna(axis=1)
#events_input_hist['dist_type_name']=events_input_hist['dist_type_name'].astype(int)
#events_input_hist['site_index']= events_input_hist ['site_index'].astype(int)
#events_input_hist=events_input_hist.drop(columns=['climate', 'growth_period'])
#len(events_input_hist)
```

```python
# Merge the DataFrames, this would contain rows with NaNs whic are only fw
#merged_df = pd.merge(events_input_hist, irw_frac, how='left', on=['scenario', 'status', 'forest_type', 'region', 'mgmt_type','mgmt_strategy', 'con_broad', 'site_index', 'dist_type_name'])

# remove NaNs to avoid worong distribution later, i.e., so avoiding using fw amounts 
#merged_df = merged_df.dropna()
#len(merged_df)
```

```python
#merged_df.iloc[[0,-1]]
```

```python
fm_irw_prod=fm_irw_prod.fillna(0)
fm_irw_prod['irw_m3']=fm_irw_prod['irw_con_m3']+fm_irw_prod['irw_broad_m3']
fm_irw_prod.iloc[[0,-1]]
```

```python
# assuming df is your DataFrame
#df = pd.pivot_table(fm_irw_prod, index=['status', 'forest_type', 'region','mgmt_type', 'mgmt_strategy', 
#                                                'con_broad', 'site_index', 'growth_period', 'disturbance_type'], 
#                            columns='year', values=['irw_con_m3', 'irw_broad_m3'])

# reset column index to get a flat column structure
#df.columns = [f"{value}_{col}" for value, col in df.columns]
#df = df.fillna(0)
#df['irw_m3_2021']= df['irw_broad_m3_2021'] + df['irw_con_m3_2021']
#df['irw_m3_2022']= df['irw_broad_m3_2022'] + df['irw_con_m3_2022']
#df= df.reset_index()
#df.iloc[[0, -1]]
```

```python
#fm_irw_prod.columns
```

```python
# Calculate total amount for each category
total_amounts = fm_irw_prod.groupby(['year', 'con_broad'])[['irw_m3']].sum().reset_index()
total_amounts
```

```python
#aggregate back again on con and broad column
df = fm_irw_prod.merge(total_amounts, left_on=['year','con_broad'], right_on=['year','con_broad'], suffixes=('_prod', '_total'))
df#.columns
```

```python
# Calculate proportions for distribution
df['proportion'] = df['irw_m3_prod'] / df['irw_m3_total']
# check
df['proportion'].sum()
```

```python jupyter={"source_hidden": true}
df.iloc[[0, -1]]
```

```python
# prepare for events
df['amount'] = df['irw_m3_total'] *	df['proportion']
# pivot on years
df.columns
```

```python
# assuming df is your DataFrame
df_rezult = pd.pivot_table(df, index=['status', 'forest_type', 'region','mgmt_type', 'mgmt_strategy', 
                                                'con_broad', 'site_index', 'growth_period', 'disturbance_type'], 
                            columns='year', values=['amount'])

# reset column index to get a flat column structure
df_rezult.columns = [f"{value}_{col}" for value, col in df_rezult.columns]
df_rezult
#df = df.fillna(0)
#df['irw_m3_2021']= df['irw_broad_m3_2021'] + df['irw_con_m3_2021']
#df['irw_m3_2022']= df['irw_broad_m3_2022'] + df['irw_con_m3_2022']
df_rezult= df_rezult.reset_index()
#df_rezult.c''olumns#.iloc[[0, -1]]
```

```python
print(df_rezult['amount_2021'].sum())
print(df_rezult['amount_2022'].sum())
```

```python
# import format of events.csv input
events_input_hist = pd.read_csv('/mnt/eos_rw/home/users/blujdvi/eu_cbm/eu_cbm_data/countries/'+ country_iso2 + '/activities/mgmt/events.csv')
# remove all disturbances based on A
events_input_hist=events_input_hist[events_input_hist['measurement_type'] != 'A']
list(events_input_hist.columns)
print(events_input_hist.dtypes)
events_input_hist
```

```python
df_rezult=df_rezult.rename(columns = {'disturbance_type':'dist_type_name'})
df_rezult['site_index']=df_rezult['site_index'].astype(int)
print(df_rezult.dtypes)
df_rezult
```

```python
#left_cols_to_merge = ['status', 'forest_type', 'region', 'mgmt_type', 'mgmt_strategy', 
#                      'con_broad', 'site_index', 'growth_period', 'dist_type_name']


#right_cols_to_merge = ['status', 'forest_type', 'region', 'mgmt_type', 'mgmt_strategy',
#                        'con_broad', 'site_index', 'growth_period', 'dist_type_name']
                                                   
#df_event = events_input_hist.merge(df_rezult) # left_on = left_cols_to_merge, right_on = right_cols_to_merge)
#df_event

df_merged = pd.merge(events_input_hist, df_rezult, on=['status', 'forest_type', 'region', 'mgmt_type', 'mgmt_strategy', 'con_broad', 'site_index',
                                                             'growth_period'], how='left')

df_merged.iloc[[0, -1]]
```

```python
df_merged['amount_2021'].sum()
```

```python
df_merged.to_csv(continent.base_dir + '/quick_results/' +'events_2021_2022.csv', mode='w', index=False, header=True)
```

## FOURTH STEP check IRW supply and add FW

```python
from eu_cbm_hat.core.continent import continent
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ub
# instantiate the object
combo = continent.combos['reference_update_fao']
r_irw = combo.runners['ES'][-1]
#reference_year = r.country.inventory_start_year
#country_name = r.country.country_name
scenario = 'reference_update_fao'
#country_iso2 = r_irw.country.iso2_code
```

```python
# import wood density data
# import the constant values of wood density from vol_to_mass_coefs.csv from \silv\
wd_coefs = r_irw.silv.coefs.raw
wd_coefs_data=wd_coefs[['forest_type', 'wood_density', 'bark_frac']]
```

```python
#load simulated outputs
irw_out = r_irw.output.pool_flux
irw_out.iloc[[0,-1]]
irw_out=irw_out.query(' year <= 2022 ')
print(irw_out.disturbance_type.unique())
```

```python
selected_columns = [ 'disturbance_soft_production', 'disturbance_hard_production', 'disturbance_dom_production',]
irw_prod = irw_out.groupby(['year', 'forest_type'])[selected_columns].sum().reset_index()
irw_prod
```

```python
irw_vol = irw_prod.merge(wd_coefs_data, on='forest_type')
irw_vol.iloc[[0, -1]]

```

```python
irw_vol["fw_con_m3"] = ton_carbon_to_m3_ub(irw_vol, "disturbance_soft_production")
irw_vol["irw_broad_m3"] = ton_carbon_to_m3_ub(irw_vol, "disturbance_hard_production")+ton_carbon_to_m3_ub(irw_vol, "disturbance_dom_production")
```

```python
irw_vol_annual = irw_vol.groupby('year').agg(irw_con = ('disturbance_soft_production', 'sum'),
                                             irw_broad = ('disturbance_hard_production', 'sum')).astype(int).reset_index()
```

```python
irw_vol_annual 
```

```
