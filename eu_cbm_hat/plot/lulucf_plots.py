"""Plotting functions

Some of these functions require the model run for all EU countries for many
scenarios to have been aggregated inside post_processor/agg_combos.py.

Usage:

    >>> from eu_cbm_hat.plot.lulucf_plots import plot_sink_by_country
    >>> from eu_cbm_hat.plot.scenarios import plot_hexprov
    >>> from eu_cbm_hat.plot.scenarios import plot_harvest_demand
    >>> from eu_cbm_hat.plot.scenarios import plot_nai, plot_nai_eu

The arguments to these plotting functions are likely to change over time. These
plotting functions where originally created in a notebook at
eu_cbm_explore/scenarios/ssp2_fair_degrowth/ssp2_fair_owc.ipynb

Define a palette to use these plots


"""
import re
import pandas as pd
import seaborn
import seaborn.objects as so
import seaborn as sns
import matplotlib.pyplot as plt


# Rename pathways for the paper
def rename_combo_to_pathway(combo_name):
    """Rename a combo to a pathway
    For example:
        >>> rename_combo_to_pathway("pikssp2_owc_min")
    """
    out = re.sub("pik|_fel1", "", combo_name)
    #out = re.sub("min", "l", out)
    #out = re.sub("max", "h", out)
    return out

def plot_sink_by_country_old (df, y, col_wrap=None, palette=None):
    """Facet plot of CO2 forest sink by country"""
    if col_wrap is None:
        col_wrap = round(len(df["country"].unique()) / 9) + 1
    df = df.copy()
    df[y + "mt"] = df[y] / 1e6
    g = seaborn.relplot(
        data=df,
        x="year",
        y=y + "mt",
        col="country",
        hue="pathway",
        kind="line",
        col_wrap=col_wrap,
        palette=palette,
        facet_kws={"sharey": False, "sharex": False},
    )
    g.set_titles(row_template="{row_name}", col_template="{col_name}")  # , size=30)
    g.fig.set_size_inches(20, 15)
    g.fig.subplots_adjust(hspace=0.3, top=0.95)
    g.set_ylabels(f"{y} MtCO2 eq")
    g.fig.suptitle(f"{y}")
    return g

def plot_sink_by_country(df, y, col_wrap=None, palette=None):
    """Facet plot of CO2 forest sink by country"""
    if col_wrap is None:
        col_wrap = round(len(df["country"].unique()) / 9) + 1
    df = df.copy()
    df[y + "mt"] = df[y] / 1e6

    # Set global font size and line width without grids and with a clean background
    sns.set_theme(style='white', font_scale=1.5, rc={'lines.linewidth': 2.5})

    g = sns.relplot(
        data=df,
        x="year",
        y=y + "mt",
        col="country",
        hue="pathway",
        kind="line",
        col_wrap=col_wrap,
        palette=palette,
        facet_kws={"sharey": False, "sharex": True},
        linewidth=2.5  # Set the line thickness
    )
    
    # Remove the y-axis labels for each subplot
    for ax in g.axes.flat:
        ax.set_ylabel('')
    
    # Set the size of the figure
    g.fig.set_size_inches(20, 15)
    
    # Set a single Y-axis label for the entire figure
    g.fig.text(0.01, 0.5, f"{y} (MtCO2 eq)", va='center', rotation='vertical', fontsize=16)

    # Remove grid lines
    for ax in g.axes.flat:
        ax.grid(False)

    g.fig.suptitle(f"{y}", fontsize=20)

    # Adjust the subplot parameters to give more space for the legend
    g.fig.subplots_adjust(bottom=0.1, top=0.95, hspace=0.3)  # Adjust the top and bottom

    # Draw the legend
    g._legend.remove()
    g.fig.legend(loc='lower center', bbox_to_anchor=(0.5, -0.05), ncol=3)

    return g


def plot_hexprov(df, y, col_wrap=None, palette=None):
    """Facet plot of harvest demand per country for a given product"""
    if col_wrap is None:
        col_wrap = round(len(df["country"].unique()) / 9) + 1
    g = seaborn.relplot(
        data=df,
        x="year",
        y=y,
        col="country",
        hue="pathway",
        style="element",
        kind="line",
        col_wrap=col_wrap,
        palette=palette,
        facet_kws={"sharey": False, "sharex": False},
    )
    g.set(xticks=[2010, 2030, 2050, 2070])
    g.fig.subplots_adjust(top=0.95)
    g.set_titles(row_template="{row_name}", col_template="{col_name}")
    g.fig.set_size_inches(20, 15)
    g.fig.subplots_adjust(hspace=0.3)
    return g

import matplotlib.pyplot as plt

def plot_hexprov_regions(df, y, col_wrap=None, palette=None):
    """Facet plot of harvest demand per country for a given product"""
    if col_wrap is None:
        col_wrap = round(len(df["region_name"].unique()) / 9) + 1

    # Replace NA values with a specific color (e.g., white)
    #df_filtered= df.fillna(value={'year': 0, y: 0})  # Replace NA with 0 or any other value
    df_filtered= df[df["year"]>= 2020]
    
    g = sns.relplot(
        data=df_filtered,
        x="year",
        y=y,
        col="region_name",
        hue="pathway",
        style="element",
        kind="line",
        col_wrap=col_wrap,
        palette=palette,
        facet_kws={"sharey": False, "sharex": False}
    )
    g.set(xticks=[2020, 2030, 2050, 2070])
    g.fig.subplots_adjust(top=0.95)
    g.set_titles(row_template="{row_name}", col_template="{col_name}")
    g.fig.set_size_inches(20, 15)
    g.fig.subplots_adjust(hspace=0.3)

    # Customize the plot to represent NA values as white color
    for ax in g.axes.flat:
        ax.plot([2020, 2070], [0, 0], color="white", linestyle="--")  # Replace NA values with white color

    return g

def plot_hexprov_irw_fw(df, col_wrap=None, palette=None):
    """Facet plot of harvest demand per country for a given product"""
    if col_wrap is None:
        col_wrap = round(len(df["country"].unique()) / 9) + 1

    # Since 'harvest_demand_irw' and 'harvest_demand_fw' are not separate columns,
    # we will assume that the 'harvest' column contains these values.
    df_filtered = df[df['element'].isin(['harvest_demand_irw', 'harvest_demand_fw'])]

    g_ms = sns.relplot(
    data=df_filtered,
    x="year",
    y="harvest",
    col="country",
    hue="pathway",
    style="element",
    kind="line",
    col_wrap=3,
    facet_kws={"sharey": False, "sharex": False},
    )
    g_ms.set(xticks=[2010, 2030, 2050, 2070])
    g_ms.fig.subplots_adjust(top=0.95)
    g_ms.set_titles(row_template="{row_name}", col_template="{col_name}")
    g_ms.fig.set_size_inches(20, 15)
    g_ms.fig.subplots_adjust(hspace=0.3)
    return g_ms


def plot_harvest_demand(df, palette=None):
    """Facet plot of harvest demand per country for a given product"""
    col_wrap = round(len(df["country"].unique()) / 9) + 1
    g = seaborn.relplot(
        data=df,
        x="year",
        y="demand",
        col="country",
        hue="combo_name",
        style="faostat_name",
        kind="line",
        col_wrap=col_wrap,
        palette=palette,
        facet_kws={"sharey": False, "sharex": False},
    )
    g.fig.subplots_adjust(top=0.95)
    g.fig.suptitle(f"Industrial roundwood harvest demand from the economic model")
    g.set_titles(row_template="{row_name}", col_template="{col_name}")
    g.fig.set_size_inches(20, 15)
    g.fig.subplots_adjust(hspace=0.3)
    return g


def plot_nai(df, y, ylabel, forest_type=None, palette=None):
    """Plot Net Annual Increment"""
    g = seaborn.relplot(
        data=df,
        x="year",
        y=y,
        col="country",
        hue="pathway",
        kind="line",
        col_wrap=5,
        palette=palette,
        facet_kws={"sharey": False, "sharex": False},
    )
    status = df["status"].unique()[0]
    title = f"Net Annual Increment {status}"
    if forest_type is not None:
        title += f" forest type: {forest_type}"
    g.fig.suptitle(title)
    g.set_titles(row_template="", col_template="{col_name}")
    g.fig.supylabel(ylabel)
    g.fig.set_size_inches(15, 15)
    g.fig.subplots_adjust(hspace=0.3)
    g.fig.subplots_adjust(top=0.90, left=0.08, right=0.88)
    file_name = f"nai_{y}_{status}_by_country.png"
    return g


def plot_nai_eu(df, y, palette=None):
    """Plot Net Annual Increment in the EU"""
    g = seaborn.relplot(
        data=df,
        x="year",
        y=y,
        col="status",
        hue="pathway",
        kind="line",
        col_wrap=1,
        palette=palette,
        facet_kws={"sharey": False, "sharex": False},
    )
    g.set_titles(row_template="{row_name}", col_template="{col_name}")
    g.fig.supylabel("NAI in million m3")
    g.fig.set_size_inches(12, 10)
    g.fig.subplots_adjust(hspace=0.3)
    g.fig.subplots_adjust(top=0.90, right=0.88)
    return g


def plot_sink_composition(df, selected_years, index):
    """Bar plot of the sink composition for all years
    Facet on pathway, with years on the x axis.
        >>> plot_sink_composition(sink_by_country_groups,
        ...                       [2030, 2050, 2070],
        ...                       index = ["pathway", "year", "country_group"])
        >>> plot_sink_composition(sink_eu,
        ...                       [2030, 2050, 2070],
        ...                       index=["pathway", "year"])
    """
    # Compute dom sink and select years
    df["dom_sink"] = df[["litter_sink", "dead_wood_sink"]].sum(axis=1)
    selected_columns = ["living_biomass_sink", "dom_sink", "soil_sink", "hwp_sink_bau"]
    selector = df["year"].isin(selected_years)
    df = df.loc[selector, index + selected_columns].copy()
    df[selected_columns] = df[selected_columns] / 1e6
    # Reshape to long format
    df_long = df.melt(id_vars=index, var_name="sink", value_name="value")
    # Plot
    p = so.Plot(df_long, x="year", y="value", color="sink")
    p = p.add(so.Bar(), so.Stack())
    if "country_group" in index:
        p = p.facet("pathway", "country_group").share(x=False)
        p = p.layout(size=(14, 9), engine="tight")
    else:
        p = p.facet("pathway").share(x=False)
        p = p.layout(size=(10, 8), engine="tight")
    palette = {
        "living_biomass_sink": "forestgreen",
        "dom_sink": "gold",
        "soil_sink": "black",
        "hwp_sink_bau": "chocolate",
    }
    p = p.scale(x=so.Continuous().tick(at=selected_years), color=palette)
    p = p.label(x="", y="Million t CO2 eq", color="")
    return p


def plot_sink_by_regions(df, y, col_wrap=None, palette=None):
    """Facet plot of harvest demand per country for a given product"""
    if col_wrap is None:
        col_wrap = round(len(df["region_name"].unique()) / 9) + 1

    # Replace NA values with a specific color (e.g., white)
    df_filled = df.fillna(value={'year': 0, y: 0})  # Replace NA with 0 or any other value

    g = sns.relplot(
        data=df_filled,
        x="year",
        y=y,
        col="region_name",
        hue="pathway",
        kind="line",
        col_wrap=col_wrap,
        palette=palette,
        facet_kws={"sharey": False, "sharex": False}
    )
    g.set(xticks=[2010, 2030, 2050, 2070])
    g.set_titles(row_template="{row_name}", col_template="{col_name}")
    g.fig.set_size_inches(20, 15)
    g.fig.subplots_adjust(hspace=0.3)

    # Remove grid lines
    for ax in g.axes.flat:
        ax.grid(False)

    # Adjust the subplot parameters to reduce space on the right and below
    g.fig.subplots_adjust(left=0.08, bottom=0.08, top=0.92, right=0.92)

    # Draw the legend and place it below the plots
    g._legend.remove()
    g.fig.legend(loc='lower center', bbox_to_anchor=(0.5, -0.05), ncol=3)

    g.fig.suptitle(f"{y}", fontsize=20)

    return g
