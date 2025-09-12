"""Plot NPP values

See also:

- info/clim_adjust_common_input.py
- info/clim_adjust.py

Usage:

>>> import matplotlib.pyplot as plt
>>> from eu_cbm_hat.plot.npp import plot_npp_facet
>>> from eu_cbm_hat.info.clim_adjust_common_input import mean_npp_by_model_country_clu_con_broad
>>> df = mean_npp_by_model_country_clu_con_broad(hist_start_year=2010, hist_end_year=2020)
>>> plot_npp_facet(df, 'Austria')
>>> plt.show()

"""
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def plot_npp_facet(df: pd.DataFrame, country_name: str) -> sns.FacetGrid:
    """
    Creates a seaborn facet plot of mean Net Primary Productivity (NPP)
    for a specified country, broken down by model and vegetation type.

    The function handles data quality issues by automatically filtering out
    sentinel values and aggregate model data to ensure a scientifically
    valid comparison of individual model outputs.

    Args:
        df (pd.DataFrame): A pandas DataFrame containing the NPP data.
        country_name (str): The name of the country for which to plot the data.

    Returns:
        seaborn.FacetGrid: The seaborn FacetGrid object representing the plot.

    Raises:
        ValueError: If the specified country is not found in the DataFrame.
    """
    if country_name not in df['country'].unique():
        raise ValueError(f"Country '{country_name}' not found in DataFrame.")

    selector = df['country'] == country_name
    selector &= df['npp']!= -1.0
    selector &= df["model"] != "models-mix"
    filtered_df = df.loc[selector]
    # Ensure a consistent order for models and vegetation types
    model_order = sorted(filtered_df['model'].unique())
    con_broad_order = sorted(filtered_df['con_broad'].unique())

    # Create the facet plot
    g = sns.relplot(
        data=filtered_df,
        x="year",
        y="npp",
        kind="line",
        col="con_broad",
        row="climate",
        hue="model",
        facet_kws={
            'sharey': False,
            'margin_titles': True,
        },
        height=3,
        aspect=1.5,
    )
    g.set_titles(col_template="{col_name}",
                 row_template="Climate: {row_name}")
    g.fig.suptitle(
        f'Annual Mean NPP for {country_name} (2000-2022)',
        y=1.02,
        fontsize=16
    )
    g.set_axis_labels("Year", "Mean NPP")
    return g

