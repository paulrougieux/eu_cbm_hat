---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.11.1
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

This allows checking and mapping of the EU species/forest types to Canadian Boudewyn eqs. from the original aidb of CBM.

Specifically, the input required are "wd_cbm_target" (as the value intended for the wood density) in "vol_to_mass_coefs.csv".

**Please note** original eqs. are available in the folder ....eu_cbm_data/common.
boudewyn_eq_cbm = ......\common\tblBioTotalStemwoodSpeciesTypeDefault.csv
species_id_cbm = ......common\tblSpeciesTypeDefault.csv

**Also, please pay attention** that under section 8 it is necessary to perfom a manual operation, namely selection of the best match in an ouput file, which is fed back afterwards. Given heterogenous input datasets for each country, this notebook may need local adaptation.

**Moreover, in order to update aidb** with the last selection it is needed to activate last cell. 

```python
import sqlite3
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
%matplotlib inline
from sklearn.metrics import mean_squared_error 

#import the runner and database
from eu_cbm_hat.core.continent import continent
```

```python
# import input data when data is available in aidb
combo = continent.combos['ia_2040']
r = combo.runners['AT'][-1]
libcbm_aidb = r.country.aidb.db
country = r.country
```

```python
# this is useful if there are wildcards in YTs input, so replacing them by inventory inputs
inventory = r.input_data['inventory']
inventory=inventory[~inventory.forest_type.str.contains('NF_', na=False)]
inventory=inventory[(inventory['status'] == "ForAWS")].rename(columns = {'forest_type': 'inv_forest_type'})
```

```python
#prepare the inventory combination in case there are wildcards
clsfrs_inv = (inventory
         .groupby(['status','inv_forest_type','region','mgmt_type','mgmt_strategy','climate','con_broad', 'site_index','growth_period'])
         .agg (area=('area', sum))
         .reset_index())
clsfrs_noq=clsfrs_inv.drop_duplicates().drop(columns = ['area'])
clsfrs_noq.iloc[[1, -1]]
```

```python
# import original aidb data when data is available in local file
boudewyn_eq_cbm = pd.read_csv(continent.base_dir + "/common/tblBioTotalStemwoodSpeciesTypeDefault.csv")
species_id_cbm = pd.read_csv(continent.base_dir + "/common/tblSpeciesTypeDefault.csv")

# import the constant values of wood density from vol_to_mass_coefs.csv from \silv\, this contains the wd_cbm_target
wd_coefs = r.silv.coefs.raw
wd_coefs_data = wd_coefs.rename(columns={'forest_type':'inv_forest_type'})
```

# Extract params for Canadian species from original aidb tables (Boudewyn params)

```python
# add species ids to parameters
#"Data_type" from Boudewyn's input stands for S-species, F=forest, G-genus

vol_to_bio_f = boudewyn_eq_cbm.rename(columns={'DefaultSpeciesTypeID':'cbm_species_id', 'DefaultSPUID': 'cbm_spu_id', 'Data_type':'cbm_data_type'})

species_id_cbm = species_id_cbm.rename(columns={'SpeciesTypeID':'cbm_species_id', 'SpeciesTypeName':'cbm_species_name', 'ForestTypeID':'cbm_group', 'GenusID':'cbm_genus'})
cols_sp=['cbm_species_id', 'cbm_species_name', 'cbm_group','cbm_genus']
vol_to_bio_sp = species_id_cbm[cols_sp]

# remove duplicate equations
cbm_biom_orig = vol_to_bio_sp.merge(vol_to_bio_f, how = 'inner').drop_duplicates(subset=['a']).reset_index()
#cols_eq = ['cbm_spu_id','cbm_species_id', 'cbm_data_type','cbm_species_name', 'a', 'b', 'a1', 'a2', 'a3', 'b1', 'b2', 'b3', 'c1', 'c2', 'c3']
#cbm_biom =cbm_biom_orig[cols_eq]

cbm_biom_orig.iloc[[1,-1]]
```

# Import YTs tables of the respective country

```python
# import volumes from yield tables input
growth_input = r.input_data['growth_curves']

# keep yield data only, and seelct the curves used for the initialization ("init) 
# Using "Init" or Cur" yield tables does not generate difference in the wd, as already checked
yield_curve_in = growth_input.loc[growth_input['growth_period'] == "Init"]
yield_curve_in = yield_curve_in.rename(columns={'forest_type':'inv_forest_type'})

# remove duplicates
yield_curve_in =  yield_curve_in.drop_duplicates()
yield_curve_in.iloc[[1,-1]]
```

```python
# check if there are wildcards
wild_card = yield_curve_in.region.unique()
sorted_clsfr = np.sort(wild_card)
sorted_clsfr
```

```python
# Generic approach to replace wildcards on selected column, this runs if there are wildcard for the selected classifier
#variable = "region"

# Separate in 2 dataframe depending on whether there is a wildcard or not 
#df_q = yield_curve_in.loc[yield_curve_in[variable] == "?"].copy()
#df_q.drop(columns="region", inplace=True)
#df_noq = yield_curve_in.loc[yield_curve_in[variable] != "?"].copy()
#df_noq['region'] = df_noq['region']#.astype(int)
#df_q_inv = df_q.merge(clsfrs_noq, on = ['status', 'inv_forest_type', 'region', 'mgmt_type', 'mgmt_strategy',
#                                        'con_broad', 'site_index', 'growth_period'])
# Merge back the two dataframes
#yield_curve = pd.concat([df_noq, df_q_inv])
#yield_curve.region.unique()
```

```python
#define variable for which ? is used
#import the names of the concerned "variable"
inventory = r.input_data['inventory']
var_df=inventory[['region']].drop_duplicates()
yield_curve_noq = yield_curve_in.drop(columns = ['region']) 
```

```python
# distribute itrw to all regions
yield_curve=var_df.merge(yield_curve_noq, how = 'cross')
```

```python
# check for the duplicates
col_clsfr = ['status', 'inv_forest_type', 'region', 'mgmt_type', 'mgmt_strategy','climate']

dup_inputs = yield_curve[yield_curve[col_clsfr].duplicated()]
# to csv
#dup_inputs.to_csv('dup_inputs.csv')
len(dup_inputs)
```

```python
#remove the volume corresponding to lower age ranges
#this first when we want to climates 
yield_curves=yield_curve.drop (columns = ['vol0', 'vol1', 'vol2', 'vol3'])

yield_curves.head(1)
```

# Estimate the "target" merchantable biomass by conversion of YT volume with constant values selected as "wd_cbm_target"

```python
# Reshape the volume yield curves to long format
index = ['status', 'inv_forest_type', 'region', 'mgmt_type', 'mgmt_strategy',
         'climate', 'con_broad', 'site_index', 'growth_period', 'sp']

# add wood_density column vol_to_mass_coefs.csv"
yc = (yield_curves
           .melt(id_vars=index, var_name="age", value_name="volume")
           .sort_values(index)
           .merge(wd_coefs_data[["inv_forest_type", "wd_cbm_target"]], on ='inv_forest_type')
          )
```

```python
#add new column on biomass estimated based on wood density coeficients (the constant value from .csv input)
yc["bm_coeff"] = yc["volume"] * yc["wd_cbm_target"]
yc.iloc[[1,-1]]
```

 # Define formula for "non-linear" conversion of volume to biomass by A & B parameteres

```python
# define function to estimate the biomass from a and b and YTs volumes 
"""deduct the proportion of non-merch from stemwood and stumps by merchantability criteria defined in the AIDB for each country, 
i.e.*0.92 top proportion (5.18%) and stump proportion (2.80%)"""
def compute_cbm_biomass(df, a, b):
    """Compute cbm biomass from a and b applied to YTs"""
    cbm_biomass = 0.92 * (a * df["volume"] ** b)
    return  cbm_biomass
```

```python
# Compute biomass for all values of "a" and "b" existing in the aidb
# and for all combinations of classifiers
for i in cbm_biom_orig.index:
    column_name = "bm_cbm_" + str(cbm_biom_orig.loc[i, "cbm_spu_id"]) + str("_")+ str(cbm_biom_orig.loc[i, "cbm_species_id"]) + str("_") + str(cbm_biom_orig.loc[i, "cbm_data_type"])+ str("_")+ str(cbm_biom_orig.loc[i, "cbm_species_name"])+ str("_")  + str(cbm_biom_orig.loc[i, "a"]) + str("_") + str(cbm_biom_orig.loc[i, "b"])
    column_name_2 = str(cbm_biom_orig.loc[i, "cbm_group"]) + str("_")+ str(cbm_biom_orig.loc[i, "cbm_genus"])
    yc[column_name] = compute_cbm_biomass(yc, cbm_biom_orig.loc[i, "a"], cbm_biom_orig.loc[i, "b"]).copy()
    yc['species'] = str(cbm_biom_orig.loc[i, "cbm_species_id"])

list(yc.columns)
```

```python
#count the number of columns which assess the matches between biomass by coeff and all CBM's values, 
# deducting the 15 classifiers columns as of list() 

len(yc.columns)-15
```

## Compute RMSE between biomass estimated with "wd_cbm_target" and all possible "A&B based conversion"

```python
#define rmse formula
def rmse_comp(x, y):
    """ Compute the root mean square error
    Example use:
            >>> rmse_comp(yc1_bis["volume"], yc1_bis["bio_cbm0"])
    """
    return ((x - y) ** 2).mean() ** .5
```

```python
# Get unique combinations of classifiers in the data frame of yield curves
clfrs = list(r.country.orig_data.classif_names.values())
clfrs = list(map(lambda x: x.replace("forest_type", "inv_forest_type"), clfrs))
yc_unique_classif = yc[clfrs].drop_duplicates().reset_index(drop=True)

# Initialise empty values
bio_cbm_cols = [col for col in yc.columns if col.startswith('bm_cbm')]

yc_rmse = yc_unique_classif.copy()
for col in bio_cbm_cols:
    yc_rmse[col] = np.nan
mean_squared_error
# For each unique combination of classifiers, compute the RMSE of each "a" and "b" coefficient
for i in yc_unique_classif.index:
    # Remove this to compute it for more than a few lines
    #if i > 10:
    #    break
    # Filter yc for this combination of classifiers
    yc_chunk = yc.merge(yc_unique_classif.loc[[i]], on=clfrs, how="inner")
    for col in bio_cbm_cols:
        yc_rmse.loc[i,col] = rmse_comp(yc_chunk["bm_coeff"], yc_chunk[col])

# display rmse for all cbm species
list(yc_rmse.columns)
```

```python
#count the number of columns which assess the matches, deducting the classifiers columns as of list() 
len(yc_rmse.columns)-9
```

```python
# identifying the mapping of "inv_forest_type" with "cbm_forest_type_match" based on min_rmse
yc_rmse_long = yc_rmse.melt(id_vars = clfrs, value_vars=bio_cbm_cols, var_name="best_cbm_match", value_name="rmse")
yc_rmse_long.iloc[[1, -1]]
```

```python
yc_rmse_long.index
```

```python
len(yc_rmse_long)
```

# attach stemwood proportion to rmse data

```python
# Reshape the volume yield curves to long format
index = ['status', 'inv_forest_type', 'region', 'mgmt_type', 'mgmt_strategy',
         'climate', 'con_broad', 'site_index', 'growth_period', 'sp']

# add wood_density column vol_to_mass_coefs.csv"
yc_p = (yield_curves
           .melt(id_vars=index, var_name="age", value_name="volume")
           .sort_values(index)
          )
```

```python
#apply the params to corresponding volume, and replace vol values with proportion
import numpy as np
def compute_pstemwood(df, a1, a2, a3, b1, b2, b3, c1, c2, c3):
    pstemwood = 1/(1 + np.exp(a1 + a2 * df["volume"] + a3 * np.log(df["volume"]))+
                  np.exp(b1 + b2 * df["volume"] + b3 * np.log(df["volume"]))+
                  np.exp(c1 + c2 * df["volume"] + c3 * np.log(df["volume"])))
    return pstemwood
```

```python
# Compute biomass for all values of "a" and "b" existing in the aidb
# and for all combinations of classifiers
for i in cbm_biom_orig.index:
    column_name = "bm_cbm_" + str(cbm_biom_orig.loc[i, "cbm_spu_id"]) + str("_")+ str(cbm_biom_orig.loc[i, "cbm_species_id"]) + str("_") + str(cbm_biom_orig.loc[i, "cbm_data_type"])+ str("_")+ str(cbm_biom_orig.loc[i, "cbm_species_name"])+ str("_")  + str(cbm_biom_orig.loc[i, "a"]) + str("_") + str(cbm_biom_orig.loc[i, "b"])# +str('_x_') +str(cbm_biom_orig.loc[i, "cbm_group"]) + str("_")+ str(cbm_biom_orig.loc[i, "cbm_genus"])
    # + str("_")+ str(cbm_biom_orig.loc[i, "cbm_genus"])
    yc_p[column_name] = compute_pstemwood(yc_p, cbm_biom_orig.loc[i, "a1"], cbm_biom_orig.loc[i, "a2"], cbm_biom_orig.loc[i, "a3"],cbm_biom_orig.loc[i, "b1"],cbm_biom_orig.loc[i, "b2"],cbm_biom_orig.loc[i, "b3"],cbm_biom_orig.loc[i, "c1"],cbm_biom_orig.loc[i, "c2"],cbm_biom_orig.loc[i, "c3"]).copy()
    yc_p['species'] = str(cbm_biom_orig.loc[i, "cbm_species_id"])
list(yc_p.columns)
```

```python
len(yc_p.columns)-13
```

```python
# THIS takes long
# identifying the mapping of "inv_forest_type" with "cbm_forest_type_match" based on min_rmse
yc_p_long = yc_p.melt(id_vars = clfrs, value_vars=bio_cbm_cols, var_name="best_cbm_match", value_name="rmse")
yc_p_long.iloc[[1, -1]]
```

```python
# melt to have the same format as rmse dataframe
yc_p_long = yc_p.melt(id_vars = clfrs, value_vars=bio_cbm_cols, var_name="best_cbm_match", value_name="p_stemwood")
yc_p_long.iloc[[1, -1]]
```

```python
# drop duplicates
yc_p_long = yc_p_long.drop_duplicates(subset=['status', 'inv_forest_type', 'region', 'mgmt_type', 'mgmt_strategy', 'climate', 'con_broad', 'site_index', 'growth_period','best_cbm_match'])
```

```python
len(yc_p_long)
```

# Identify the best match in original aidb for EU species/forest types

```python
# final on NUTS:  best_cbm_match between biomass based on coeff and on all cbm params
index = ['inv_forest_type', 'region', 'mgmt_type', 'mgmt_strategy', 'climate']
yc_rmse_long_20 = (yc_rmse_long
         .sort_values(by= index + ['rmse'], ascending=True)
         .groupby(index)
         # Take the first 20 match for each combination of classifiers
         .head(100))
print(len(yc_rmse_long_20))
yc_rmse_long_20.iloc[[1, -1]]
```

```python
#create a single dataframe with rmse and pstemwood
cols_mrg = ['status', 'inv_forest_type', 'region', 'mgmt_type', 'mgmt_strategy', 'climate', 'con_broad', 'site_index', 'growth_period', 'best_cbm_match']
yc_rmse_long_10 = yc_rmse_long_20.merge(yc_p_long, on = cols_mrg, how = 'inner')

len(yc_rmse_long_10)
```

# PRINT this only if needed, if not go to next

```python
#PRINT a FILE WHERE TO DO MANUAL SELECTION OF BEST MATCHES
# Highlight min_rmse with a value of 1
yc_rmse_long_10.loc[yc_rmse_long_10.groupby(index)["rmse"].idxmin(), "min_rmse"] = 1

# Write to a csv file in libcbm_data/output/boudewyn/
(continent.output_dir + "boudewyn/").create_if_not_exists()
yc_rmse_long_10.to_csv(continent.output_dir + "/boudewyn/yc_rmse.csv", mode='w',index=False)
```

'NOW' open the csv file and select the best match manually in the file by adding "1" on the column "rmse". To this file it will append the actual selections in the next cells, so if you rerun you need to erase the long format tables at the lower part of the csv file. 

```python
# IMPORT BACK the yc_rmse.csv file with seelcted matches

# CHANGE COUNTRY CODE IN FILE NAME

match_selected = pd.read_csv(continent.output_dir + "/boudewyn/yc_rmse.csv")
match = match_selected.loc[match_selected["min_rmse"] == 1].copy()
match.iloc[[1, -1]]
```

```python
# extract the spui_id and species_id from "best_match" column
match['cbm_spu_id'] = match['best_cbm_match'].str.replace("bm_cbm_","").str[:2].str.replace("_", '')

# extract the cbm_species_id
match['cbm_species_id'] = match['best_cbm_match'].str.replace("bm_cbm_", '').str[:6].str[2:].str.replace("_F_", '').str.replace("_G_", '').str.replace("_S_", '').str.replace("_F", '').str.replace("_G", '').str.replace("_S", '').str.replace("_", '')

#check the presence of strange characters 
print(match.cbm_spu_id.unique())
print(match.cbm_species_id.unique())
```

```python
#remove cbm's forest types, #ignore mapping to species, genus, forest
match ['cbm_data_type_s'] = match["best_cbm_match"].str.extract(pat = '(_[S]_)')
match ['cbm_data_type_g'] = match["best_cbm_match"].str.extract(pat = '(_[G]_)')
match ['cbm_data_type_f'] = match["best_cbm_match"].str.extract(pat = '(_[F]_)')

match.loc[match['cbm_data_type_s'].isna(), 'cbm_data_type_s'] = ''
match.loc[match['cbm_data_type_g'].isna(), 'cbm_data_type_g'] = ''
match.loc[match['cbm_data_type_f'].isna(), 'cbm_data_type_f'] = ''

match ['cbm_data_type'] = match['cbm_data_type_s'] + match['cbm_data_type_g'] + match['cbm_data_type_f']
match ['cbm_data_type'] = match['cbm_data_type'].str.replace("_", '')
match ['cbm_species_id']=match ['cbm_species_id'].astype('int')
match ['cbm_spu_id'] =match ['cbm_spu_id'].astype('int')
```

```python
match = match[['status', 'inv_forest_type', 'region', 'mgmt_type', 'mgmt_strategy',
       'climate', 'con_broad', 'site_index', 'growth_period', 'best_cbm_match',
       'cbm_spu_id', 'cbm_species_id', 'cbm_data_type']]
match.iloc[[1, -1]]
```

```python
#merge best_match with 
best_match = match.merge(cbm_biom_orig,how='inner', 
                         left_on = [ 'cbm_spu_id','cbm_species_id', 'cbm_data_type'], 
                         right_on = [ 'cbm_spu_id','cbm_species_id', 'cbm_data_type'])

best_match = best_match[[  'status', 'inv_forest_type', 'region', 'mgmt_type', 'mgmt_strategy',
       'climate', 'con_broad', 'site_index', 'growth_period', 'best_cbm_match',
       'cbm_spu_id', 'cbm_species_id', 'cbm_data_type', 'index',
       'cbm_species_name', 'a', 'b', 'a_nonmerch', 'b_nonmerch', 'k_nonmerch',
       'cap_nonmerch', 'a_sap', 'b_sap', 'k_sap', 'cap_sap', 'a1', 'a2', 'a3',
       'b1', 'b2', 'b3', 'c1', 'c2', 'c3', 'min_volume', 'max_volume',
       'low_stemwood_prop', 'high_stemwood_prop', 'low_stembark_prop',
       'high_stembark_prop', 'low_branches_prop', 'high_branches_prop',
       'low_foliage_prop', 'high_foliage_prop']]

best_match#.iloc[[0,1,2,-1]]
#best_match.columns
best_match=best_match.drop_duplicates()
```

```python
best_match.inv_forest_type.unique()
```

```python
best_match.region.unique()
```

```python
len(best_match)
```

# Prepare the country's Boudewyn eqs. in the country's eqs.

```python
# initial complete list of codes for all Boudewyn eqs. in the country's AIDB
cbm_codes = libcbm_aidb.read_df('vol_to_bio_species')
cbm_codes.iloc[[1, -1]]
```

## identify country's "spatial_unit_id"

```python
# add the spatial units: admin+CLU
eu_spatial_units = libcbm_aidb.read_df('spatial_unit')
eu_spatial_units = eu_spatial_units[['id', 'admin_boundary_id', 'eco_boundary_id']].rename(columns = {'id':'spatial_unit_id'})
eu_spatial_units.iloc[[0,-1]]
```

```python
# add the spatial units: admin+CLU
eu_admin_units = libcbm_aidb.read_df('admin_boundary_tr').rename(columns={'name':'name_aidb'})
eu_admin_units=eu_admin_units[['admin_boundary_id', 'name_aidb']]
eu_admin_units.iloc[[1, -1]]
```

```python
# obtain explicit table with all EU regions and climates
eu_spatialized = eu_spatial_units.merge(eu_admin_units)
eu_spatialized.iloc[[1, -1]]
```

```python
#narow down to respective country, add country codes to names in aidb, expand with climates
# disregard the two columns they are usefull for othe purposes
ms_admin_clsfr = r.country.associations.df
ms_spatial_units = eu_spatialized.merge(ms_admin_clsfr, on = 'name_aidb', how = 'inner')
ms_spatial_units = ms_spatial_units.drop(columns = ['name_input','category']).rename(columns={'corresponding_inv':'region', 'name_aidb':'admin_name_aidb'})
ms_spatial_units# .iloc[[1, -1]]

ms_spatial_units = ms_spatial_units[ms_spatial_units ['admin_name_aidb'] !='Sweden' ]
ms_spatial_units.head(1)
```

```python
#if (set(best_match["region"]) - set(ms_spatial_units["region"]) != set()):
#    raise ValueError("Some forest types are missing")
```

```python
len(ms_spatial_units)
```

```python
len(best_match)
```

## identify country's "species_id"

```python
# focus on species_id from aidb
# extract all the names used in the aidb
eu_cbm_species = libcbm_aidb.read_df('species_tr').rename(columns={'name':'name_aidb'})
eu_cbm_species#.iloc[[1, -1]]
```

```python
#sp list from associations
species_name = country.associations.df
species_name#.iloc[[1, -1]]
```

```python
# import classifiers from input
clsfr_input = r.input_data.paths
clsfr_input = r.input_data['classifiers']
```

```python
# extract the forest_type name from classifiers
forest_types=clsfr_input.loc[clsfr_input['classifier_number']== 2]
forest_types=forest_types.rename(columns=({'name':'name_input', 'classifier_value_id':'forest_type'}))
forest_types.reset_index()
```

```python
#forest_types=forest_types['name_input'].replace({'OB_SE': 'OB (SE)'})
```

```python
input_forest_types = species_name.merge(forest_types, how = 'inner', on = 'name_input')
input_forest_types 
```

```python
input_forest_types.name_aidb.unique()
```

```python
#input_forest_types ["name_aidb"] = input_forest_types ["name_aidb"].replace({'OC (IT)':'OC_IT',
#                                                                               'OB (IT)':'OB_IT', 
#                                                                               'AA (IT)':'AA_IT', 
#                                                                               'CS (IT)':'CS_IT', 
#                                                                               'FS (IT)':'FS_IT', 
#                                                                               'LD (IT)':'LD_IT',
#                                                                               'Oca (IT)':'Oca_IT', 
#                                                                               'OE (IT)':'OE_IT', 
#                                                                               'PA (IT)':'PA_IT',
#                                                                               'PM (IT)':'PM_IT', 
#                                                                               'PN (IT)':'PN_IT',
#                                                                               'PS (IT)':'PS_IT',
#                                                                               'QC (IT)':'QC_IT',
#                                                                               'QI (IT)':'QI_IT', 
#                                                                               'QR (IT)':'QR_IT',
#                                                                               'QS (IT)':'QS_IT', 
#                                                                               'RF (IT)': 'RF_IT' })
```

```python
#narrow to country's forest types, join species in aidb with ms data
ms_species =  eu_cbm_species.merge(input_forest_types)#.reset_index()
ms_species#.columns
```

```python
ms_species = ms_species[['species_id',  'name_aidb',  'name_input','forest_type']].rename(columns={'name_aidb':'species_name_aidb'})

ms_species=ms_species.drop_duplicates('species_id')

ms_species.reset_index()
```

```python
#ms_species ["forest_type"] = ms_species["forest_type"].replace({'CP':'OC','BP':'OB' })
#ms_species=ms_species.rename(columns = {'corresponding_inv':'forest_type'})
```

```python
ms_species.forest_type.unique()
```

```python
#attach the forest types to each spatial_unit strata
ms_spatial_species = ms_spatial_units.merge(ms_species, how = 'cross') # ensure all possible combinations between spu and sp, clus 
len(ms_spatial_species)
ms_spatial_species#.iloc[[0,-1]
```

```python
# expected
114*17
```

```python
#keep only the needed columns
ms_spatial_species = ms_spatial_species [['spatial_unit_id', 'species_id', 'admin_name_aidb', 'species_name_aidb', 'eco_boundary_id']]
ms_spatial_species =ms_spatial_species.rename(columns = {'eco_boundary_id':'climate'})
ms_spatial_species#.iloc[[1, -1]]
len(ms_spatial_species)
```

```python
len(ms_spatial_units) * len(ms_species)
```

```python
cbm_codes.iloc[[1, -1]]
```

```python
#identify the equation's "vol_to_bio_factor_id", so they can be identified further in the table "vol_to_bio_factor_forest_types" in aidb
factor_codes = ms_spatial_species.merge(cbm_codes, on = ['spatial_unit_id','species_id'], how = 'inner')
factor_codes#.species_id.unique()
```

```python
#factor_codes.to_csv("aidb_ft.csv")
```

```python
factor_codes.species_name_aidb.unique()
```

```python
ms_species.iloc[[0,1]]
```

```python
factor_codes=factor_codes[['spatial_unit_id', 'species_id', 'vol_to_bio_factor_id', 'admin_name_aidb', 'species_name_aidb', 'climate']]
factor_codes.iloc[[0,1]]
```

```python
len(factor_codes)
```

```python
# introduc forest types, cateva tipuri lipsesc 
factor_codes = factor_codes.merge(ms_species, on = ['species_id','species_name_aidb'])
#factor_codes['climate'] = factor_codes['climate'].astype(int)
factor_codes #.iloc[[1,2,-2,-1]]
```

```python
len(factor_codes.species_id	.unique())
```

```python
len(factor_codes.spatial_unit_id.unique())
```

```python
factor_codes.species_name_aidb.unique()
```

```python
factor_codes.forest_type.unique()
```

```python
#best_match__ = concat_df_1.drop_duplicates()
best_match__ =best_match.rename(columns={'inv_forest_type':'forest_type'})
```

```python
best_match__
```

```python
best_match__.forest_type.unique()
```

```python
len(best_match__)
```

```python
best_match__.forest_type.unique()
```

```python
if (set(best_match__["forest_type"]) - set(ms_species["forest_type"]) != set()):
    raise ValueError("Some forest types are missing")
```

```python
ms_species
```

```python
best_match_=best_match__.merge(ms_species, on = 'forest_type', how = 'inner')

# replace name of the regions with country, if needed
#best_match_['region'] = 'IT'


best_match_.columns#.iloc[[1, -1]]
```

```python
len(best_match_)
```

```python
selector = best_match_.duplicated(keep="first")
#best_match_no_dup = best_match_[~selector]
#best_match_no_dup
selector
```

```python
factor_codes.iloc[[0]]
```

```python
best_match_.iloc[[0]]
```

```python
factor_codes.columns
```

```python
best_match_.columns
```

```python
#best_match_['climate'] = best_match_['climate'].astype(int)
solution =factor_codes.merge(best_match_, on =['forest_type', 'species_id', 'species_name_aidb', 'name_input'], how = 'outer').dropna()
#.iloc[[1, -1]]
solution
```

```python
solution = solution.drop(columns = ['climate_y'])
```

```python
solution=solution.rename(columns = { 'admin_name_aidb':'region','climate_x':'climate'})
solution.columns
```

```python
solution
```

```python
solution['climate']= "?"
solution=solution.drop_duplicates()
solution
```

```python
solution.species_name_aidb.unique()
```

```python
#select the classifier required
cols_classifiers = ['status','region','forest_type','climate', 'mgmt_type', 
                     'mgmt_strategy', 'con_broad', 'site_index', 'growth_period',]

# keep tracking of correspondence between data input and aidb
cols_cbm_match = ['species_name_aidb', 'cbm_spu_id', 'cbm_species_id','cbm_data_type', 
                  'best_cbm_match','cbm_species_name']
    
# the actual set of corresponding to best match for the aidb required code
cols_tab_vol_to_bio_forest_type = ['spatial_unit_id', 'species_id']     

# the actual set of params for the equations corresponding to best match for the aidb required code
cols_tab_vol_to_bio_factor = ['vol_to_bio_factor_id', 'a', 'b', 'a_nonmerch', 'b_nonmerch', 'k_nonmerch',
       'cap_nonmerch', 'a_sap', 'b_sap', 'k_sap', 'cap_sap', 'a1', 'a2', 'a3',
       'b1', 'b2', 'b3', 'c1', 'c2', 'c3', 'min_volume', 'max_volume',
       'low_stemwood_prop', 'high_stemwood_prop', 'low_stembark_prop',
       'high_stembark_prop', 'low_branches_prop', 'high_branches_prop',
       'low_foliage_prop', 'high_foliage_prop']
```

```python
final_solution= solution[cols_classifiers+cols_tab_vol_to_bio_forest_type +cols_tab_vol_to_bio_factor]
#final_solution.vol_to_bio_factor_id.unique()
```

```python
#diminsh the number of rows, so to match the aidb 
final_solution_narowed=final_solution#.drop_duplicates(subset=['vol_to_bio_factor_id'], keep='last').copy()
final_solution_narowed#.iloc[[1, -1]]
```

```python
final_solution_narowed.forest_type.unique()
```

# Transfer to aidb tables

Prepare the output to be written to the AIDB, unsing columns from 

```python
aidb_input_tab_vol_to_bio_forest_type= final_solution_narowed[cols_tab_vol_to_bio_forest_type + ['vol_to_bio_factor_id']]

aidb_input_tab_vol_to_bio_forest_type=aidb_input_tab_vol_to_bio_forest_type#.rename(columns = {'species_id_x':'species_id'})

print("Unique spatial unit")
print(aidb_input_tab_vol_to_bio_forest_type["spatial_unit_id"].unique())
print("Unique species id")
print(aidb_input_tab_vol_to_bio_forest_type["species_id"].unique())
print("Unique vol_to_bio_factor_id")
print(aidb_input_tab_vol_to_bio_forest_type["vol_to_bio_factor_id"].unique())
len(aidb_input_tab_vol_to_bio_forest_type["vol_to_bio_factor_id"].unique())
display(aidb_input_tab_vol_to_bio_forest_type)#.iloc[[1, -1]]
```

```python
aidb_input_tab_vol_to_bio_forest_type.spatial_unit_id.unique()
```

```python
# Load existing table to check
vol_to_bio_factor_existing = libcbm_aidb.read_df("vol_to_bio_factor")
```

```python
len(vol_to_bio_factor_existing)
```

```python
# Use existing column names to select and arragne the columns
final_solution_narowed.rename(columns={"vol_to_bio_factor_id":"id"}, inplace=True)
set(final_solution_narowed.columns).issubset(vol_to_bio_factor_existing.columns)
```

```python
vol_to_bio_factor_existing.columns
```

```python
final_solution_narowed.columns
```

```python
selected_columns = ['id', 'a', 'b', 'a_nonmerch', 'b_nonmerch', 'k_nonmerch',
       'cap_nonmerch', 'a_sap', 'b_sap', 'k_sap', 'cap_sap', 'a1', 'a2', 'a3',
       'b1', 'b2', 'b3', 'c1', 'c2', 'c3', 'min_volume', 'max_volume',
       'low_stemwood_prop', 'high_stemwood_prop', 'low_stembark_prop',
       'high_stembark_prop', 'low_branches_prop', 'high_branches_prop',
       'low_foliage_prop', 'high_foliage_prop']
aidb_input_tab_vol_to_bio_factor = final_solution_narowed[selected_columns].copy()
aidb_input_tab_vol_to_bio_factor =aidb_input_tab_vol_to_bio_factor.set_index('id')
aidb_input_tab_vol_to_bio_factor#.iloc[[1, -1]]
```

```python
#nulify original params for non-merchantable biomass exisiting in the original Canadian Boudewyn eqs.
aidb_input_tab_vol_to_bio_factor.a_nonmerch =1
aidb_input_tab_vol_to_bio_factor.b_nonmerch =1
aidb_input_tab_vol_to_bio_factor.k_nonmerch =0
aidb_input_tab_vol_to_bio_factor.cap_nonmerch =1
aidb_input_tab_vol_to_bio_factor.a_sap =1
aidb_input_tab_vol_to_bio_factor.b_sap =0
aidb_input_tab_vol_to_bio_factor.k_sap =0
aidb_input_tab_vol_to_bio_factor.cap_sap =1

aidb_input_tab_vol_to_bio_factor
```

```python
aidb_input_tab_vol_to_bio_factor.dropna()
aidb_input_tab_vol_to_bio_factor#.reset_index(drop=True)
```

```python
add_171 = pd.read_csv(continent.base_dir + "/common/add_171.csv")
```

```python
add_171 = add_171.set_index('id')
add_171
```

```python
aidb_input_tab_vol_to_bio_factor=pd.concat([aidb_input_tab_vol_to_bio_factor, add_171])
```

```python
len(aidb_input_tab_vol_to_bio_factor)
```

```python
aidb_input_tab_vol_to_bio_factor.head(1)
```

```python
# Write to the aidb
libcbm_aidb.write_df(aidb_input_tab_vol_to_bio_factor,  "vol_to_bio_factor")
```

```python

```
