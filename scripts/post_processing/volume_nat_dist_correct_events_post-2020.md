---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.16.4
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

This script alows extraction of total volume generated in a year by natural disturbances. To be used for updating post-2020 years.

```python
import matplotlib.pyplot as plt
from eu_cbm_hat.post_processor.convert import ton_carbon_to_m3_ub
%matplotlib inline
import pandas as pd
import numpy as np
```

```python
from eu_cbm_hat.core.continent import continent
# instantiate the object
combo = continent.combos['reference_2024']
r = combo.runners['LV'][-1]
reference_year = r.country.inventory_start_year
country_name = r.country.country_name
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
pools_fluxes_data=pools_fluxes_data.query(' year > 2020 & year <=2022   ')
print(pools_fluxes_data.year.unique())
```

```python
# expected disturbances after 2021
events_input_hist = r.input_data['events']

# check list of disturbanecs 
dist_list = np.array(events_input_hist.dist_type_name.unique(), dtype='int64')   
dist_list
```

```python
only_nat_dist = pools_fluxes_data[pools_fluxes_data['disturbance_type'].astype(str).str.startswith('4')]
#only_nat_dist
```

```python
selected_columns = ['disturbance_soft_production', 'disturbance_hard_production']
c_nat_dist = only_nat_dist.groupby(['year', 'forest_type'])[selected_columns].sum().reset_index()
df = c_nat_dist.merge(wd_coefs_data, on="forest_type")
```

```python
df["con_m3"] = ton_carbon_to_m3_ub(df, "disturbance_soft_production")
df["broad_m3"] = ton_carbon_to_m3_ub(df, "disturbance_hard_production")
df['total_nat_dist_m3']= df['con_m3']+ df['broad_m3']
df = df.groupby(['year'])['total_nat_dist_m3'].sum().reset_index()
```

```python
df=df.set_index(['year']).T
df['country'] = country_name
# insert column with insert(location, column_name, column_value)
column_to_move = df.pop("country")
df.insert(0, "country", "country")
```

```python
with pd.ExcelWriter('existing_file.xlsx', engine='openpyxl', mode='a') as writer:
    df.to_excel(writer, sheet_name='nat_disturb_volumes', index=False)
```

```python
df.to_csv('existing.csv', mode='a', index=False, header=False)
```

```python

```
