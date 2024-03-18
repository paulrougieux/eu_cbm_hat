"""Plotting functions

Some of these functions require the model run for all EU countries for many
scenarios to have been aggregated inside post_processor/agg_combos.py.

Usage:

    >>> from eu_cbm_hat.plot.scenarios import plot_sink_by_country
    >>> from eu_cbm_hat.plot.scenarios import plot_hexprov
    >>> from eu_cbm_hat.plot.scenarios import plot_harvest_demand
    >>> from eu_cbm_hat.plot.scenarios import plot_nai, plot_nai_eu

The arguments to these plotting functions are likely to change over time. These
plotting functions where originally created in a notebook at
eu_cbm_explore/scenarios/ssp2_fair_degrowth/ssp2_fair_owc.ipynb

"""

import seaborn


def plot_sink_by_country(df, y, col_wrap=None, palette=None):
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


def plot_hexprov(df, y, col_wrap=None, palette=None):
    """Facet plot of harvest demand per country for a given product"""
    if col_wrap is None:
        col_wrap = round(len(df["country"].unique()) / 9) + 1
    # Remove harvest_exp_hat from the plot
    selector = df["element"] != "harvest_exp_hat"
    g = seaborn.relplot(
        data=df.loc[selector],
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


def plot_harvest_demand(df, palette=None):
    """Facet plot of harvest demand per country for a given product"""
    col_wrap = round(len(df["country"].unique()) / 9) + 1
    selector = df["combo_name"] != "reference"
    g = seaborn.relplot(
        data=df.loc[selector],
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
