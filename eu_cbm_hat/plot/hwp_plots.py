"""Generate plots of Harvested Wood Products output

Two main sections below:

    - Aggregate HWP output data for all countries within a given scenario and
      generate plots for all countries

    - Generate plots for one country


Gather HWP data for all countries in the given scenario

>>> from eu_cbm_hat.post_processor.agg_combos import save_df_all_countries_to_csv
>>> save_df_all_countries_to_csv("reference", "post_processor.hwp.stock_sink_results")
>>> save_df_all_countries_to_csv("reference", "post_processor.hwp.build_hwp_stock_since_1900")
>>> save_df_all_countries_to_csv("reference", "post_processor.hwp.build_hwp_stock_since_1990")

Generate facet plots for all countries

In all cases get inflow, loss and stock results from the 2 functions build
stock from 1900 and build stock from 1990. Load Aggregate output from csv files
on another computer, after a transfer of the output_agg directory.

>>> import pandas as pd
>>> from eu_cbm_hat import eu_cbm_data_pathlib
>>> import pandas as pd
>>> from eu_cbm_hat import eu_cbm_data_pathlib
>>> from eu_cbm_hat.plot.hwp_plots import hwp_facet_plot_by_products
>>>
>>> ref_agg_dir = eu_cbm_data_pathlib / "output_agg" / "reference"
>>> ils1900 = pd.read_csv(ref_agg_dir / "build_hwp_stock_since_1900.csv")
>>> ils1990 = pd.read_csv(ref_agg_dir / "build_hwp_stock_since_1990.csv")
>>>
>>> hwp_facet_plot_by_products(ils1900, "inflow", "hwp_inflow_by_country.png",
...                        title="Harvested Wood Products inflow amounts per year")
>>> hwp_facet_plot_by_products(ils1900, "loss", "hwp_loss_by_country.png",
...                        title="Harvested Wood Products loss amounts per year")
>>> hwp_facet_plot_by_products(ils1900, "stock", "hwp_stock_by_country.png",
...                        title="Harvested Wood Products stock amounts per year")


Generate plots for individual countries. For example Austria:

>>> from eu_cbm_hat.core.continent import continent
>>> runner_at = continent.combos['reference'].runners['AT'][-1]
>>> hwp = runner_at.post_processor.hwp
>>> sat = hwp.stock_sink_results

For example Luxemburg:

>>> from eu_cbm_hat.core.continent import continent
>>> runner_lu = continent.combos['reference'].runners['LU'][-1]
>>> hwp = runner_lu.post_processor.hwp
>>> slu = hwp.stock_sink_results
>>> # Inflow, loss and stock ils
>>> ils1990 = hwp.build_hwp_stock_since_1990
>>> ils1900 = hwp.build_hwp_stock_since_1900


Plot inflow as a line plot with one color per column

>>> import matplotlib.pyplot as plt
>>> inflow_cols = ['sw_broad_inflow', 'sw_con_inflow', 'wp_inflow', 'pp_inflow']
>>> ils1900[["year"] + inflow_cols].set_index("year").plot()
>>> plt.show()

Plot loss as a line plot with one color per column

>>> loss_cols = ['sw_con_loss', 'sw_broad_loss', 'wp_loss', 'pp_loss', 'hwp_loss']
>>> selector = ils1900["year"] < 2070
>>> ils1900.loc[selector, ["year"] + loss_cols].set_index("year").plot()
>>> plt.show()

Plot stock as a line plot

>>> stock_cols = ['sw_con_stock', 'sw_broad_stock', 'wp_stock', 'pp_stock']
>>> selector = ils1900["year"] < 2070
>>> ils1900.loc[selector, ["year"] + stock_cols].set_index("year").plot()
>>> plt.show()

"""

import pandas as pd
import numpy as np
import seaborn as sns
from eu_cbm_hat import eu_cbm_data_pathlib
import matplotlib.pyplot as plt


PLOT_DIR = eu_cbm_data_pathlib / "plot" / "hwp"
PLOT_DIR.mkdir(parents=True, exist_ok=True)
COLOR_LABELS_MAP = {
    "sw_con": ("sawnwood coniferous", "chocolate"),
    "sw_broad": ("sawnwood broadleaves", "saddlebrown"),
    "wp": ("Wood panels", "moccasin"),
    "pp": ("Paper", "lightskyblue"),
}


def plot_stacked_bars_one_country(
    df: pd.DataFrame,
    stock_cols: list[str],
    sample_interval: int = 10,
    year_col: str = "year",
    title: str = "Stock Inventory Composition Over Time (Stacked Bar Plot)",
):
    """
    Generates and displays a stacked bar plot for time series stock data.

    Args:
        df: The input DataFrame containing the stock data and a year column.
        stock_cols: A list of column names representing the stocks to be stacked.
        sample_interval: The interval (in years) at which to sample the data for plotting.
                         Default is 10 (plot every 10 years).
        year_col: The name of the column containing the year. Default is "year".
        title: The title of the plot.


    Example use:

    from eu_cbm_hat.plot.hwp_plots import plot_stacked_bars_one_country
    from eu_cbm_hat.core.continent import continent
    runner_lu = continent.combos['reference'].runners['LU'][-1]
    hwp = runner_lu.post_processor.hwp
    # Inflow, loss and stock ils
    ils1990 = hwp.build_hwp_stock_since_1990
    ils1900 = hwp.build_hwp_stock_since_1900
    stock_cols = ['sw_con_stock', 'sw_broad_stock', 'wp_stock', 'pp_stock']
    selector = ils1900["year"] < 2070
    plot_stacked_bars_one_country(ils1900, stock_cols)

    """
    # 1. Set the year column as the index for plotting
    try:
        data_to_plot = df[[year_col] + stock_cols].set_index(year_col)
    except KeyError:
        print(
            f"Error: DataFrame must contain '{year_col}' and all columns in {stock_cols}"
        )
        return

    # 2. Sample the data for readability in the bar plot
    # This is crucial for long time series (like 170 years)
    df_sampled = data_to_plot.iloc[::sample_interval]

    # Remove first and last year
    selector = df_sampled["year"] < df["year"].max()
    selector &= df["year"].min() < df_sampled["year"]
    df_sampled = df_sampled.loc[selector].copy()

    # Extract labels and colors for the columns in stock_cols
    legend_labels = [
        COLOR_LABELS_MAP[col][0] for col in stock_cols if col in color_labels_map
    ]
    plot_colors = [
        COLOR_LABELS_MAP[col][1] for col in stock_cols if col in color_labels_map
    ]

    # 4. Generate the Stacked Bar Plot
    plt.figure(figsize=(12, 6))

    df_sampled.plot(
        kind="bar",
        stacked=True,
        ax=plt.gca(),  # Use the current figure/axes
        color=plot_colors,  # Set the colors
    )

    # 5. Customize the plot appearance
    plt.title(title, fontsize=16)
    plt.ylabel("Stock Value (Units)", fontsize=12)
    plt.xlabel("Year", fontsize=12)
    plt.xticks(rotation=45, ha="right")  # Rotate x-labels for better fit
    # Set the labels using the extracted legend_labels
    plt.legend(title="Stock Type", labels=legend_labels)
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    print(
        f"--- Sampled Data Used for Stacked Bar Plot (Every {sample_interval} Years) ---"
    )
    print(df_sampled)


def hwp_facet_plot_by_products(df, variable, filename, title=None):
    """
    Creates a Seaborn facet scatter plot with one facet per country.

    Args:
        df (pd.DataFrame): The input DataFrame containing 'country', 'year',

        filename (str): The name of the file to save the plot to.

    Example:

    >>> import pandas as pd
    >>> from eu_cbm_hat import eu_cbm_data_pathlib
    >>> from eu_cbm_hat.plot.hwp_plots import hwp_facet_plot_by_products
    >>> ref_agg_dir = eu_cbm_data_pathlib / "output_agg" / "reference"
    >>> ils1900 = pd.read_csv(ref_agg_dir / "build_hwp_stock_since_1900.csv")
    >>> hwp_facet_plot_by_products(ils1900, "inflow", "hwp_inflow_by_country.png",
    ...                            title="Harvested Wood Products inflow amounts per year")
    >>> hwp_facet_plot_by_products(ils1900, "loss", "hwp_loss_by_country.png",
    ...                            title="Harvested Wood Products loss amounts per year")
    >>> hwp_facet_plot_by_products(ils1900, "stock", "hwp_stock_by_country.png",
    ...                            title="Harvested Wood Products stock amounts per year")

    """

    products = ["sw_broad", "sw_con", "wp", "pp"]
    cols = [x + "_" + variable for x in products]

    # Reshape to long format
    df_long = df.melt(
        id_vars=["country", "year"],
        value_vars=cols,
        var_name="variable",
        value_name="value",
    )
    palette = {
        col: COLOR_LABELS_MAP.get(col.replace("_" + variable, ""))[1] for col in cols
    }
    g = sns.relplot(
        data=df_long,
        x="year",
        y="value",
        hue="variable",
        col="country",
        palette=palette,
        facet_kws={"sharey": False, "sharex": False},
        # kind='scatter',
        # col_wrap=2,  # Wrap facets to 2 columns for a compact display
        # height=4,    # Height of each subplot
        # aspect=1.2   # Aspect ratio of each subplot
    )

    # Set titles and adjust layout
    g.set_axis_labels("Year", "Inflow Amount")
    if title is not None:
        g.fig.suptitle(title, y=1.03)
    # Adjust the plot to ensure labels don't overlap
    # plt.tight_layout(rect=[0, 0, 1, 0.98])
    g.savefig(PLOT_DIR / filename)


def facet_plot_total_sink(df_sink, df_hwp_sink):
    """Total sink including Harvested Wood Products

    Example use:

        >>> import pandas as pd
        >>> from eu_cbm_hat import eu_cbm_data_pathlib
        >>> from eu_cbm_hat.plot.hwp_plots import facet_plot_total_sink
        >>> ref_agg_dir = eu_cbm_data_pathlib / "output_agg" / "reference"
        >>> df_hwp_sink = pd.read_csv(ref_agg_dir / "post_processor_hwp_stock_sink_results.csv")
        >>> df_sink = pd.read_csv(ref_agg_dir / "post_processor_sink_df_agg_by_year.csv")
        >>> facet_plot_total_sink(df_sink, df_hwp_sink)

    """

    hwp_sink_cols = ["hwp_tot_sink_tco2_1900", "hwp_tot_sink_tco2_1990"]
    sink_cols = ["living_biomass_sink", "litter_sink", "dead_wood_sink", "soil_sink"]
    # Merge left with the HWP sink data frame first, to keep only results
    # available in the HWP sink data frame
    index = ["combo_name", "country", "year"]
    # Keep only HWP years available in the main sink data frame
    selector = df_hwp_sink["year"] > df_sink["year"].min()
    df = df_hwp_sink.loc[selector, index + hwp_sink_cols].merge(
        df_sink[index + sink_cols], on=index, how="left"
    )
    cols = hwp_sink_cols + sink_cols
    # Reshape to long format
    df_long = df.melt(
        id_vars=["country", "year"],
        value_vars=cols,
        var_name="sink_type",
        value_name="value",
    )
    sink_colors = {
        "hwp_tot_sink_tco2_1900": "darkred",
        "hwp_tot_sink_tco2_1990": "red",
        "living_biomass_sink": "forestgreen",
        "litter_sink": "lightgreen",
        "dead_wood_sink": "saddlebrown",
        "soil_sink": "peru",
    }
    g = sns.relplot(
        data=df_long,
        x="year",
        y="value",
        hue="sink_type",
        col="country",
        palette=sink_colors,
        facet_kws={"sharey": False, "sharex": False},
    )
    g.set_axis_labels("Year", "Sink (tCO2)")
    g.fig.suptitle("Total Sink Including Harvested Wood Products", y=1.03)
    g.savefig(PLOT_DIR / "total_sink_including_hwp.png")
