"""Generate plots of Harvested Wood Products output

Two main sections below:

    - Aggregate HWP output data for all countries within a given scenario and
      generate plots for all countries

    - Generate plots for one country


Gather HWP data for all countries for a given scenario:

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
>>> from eu_cbm_hat.plot.hwp_plots import plot_hwp_ils_facet_by_country
>>>
>>> ref_agg_dir = eu_cbm_data_pathlib / "output_agg" / "reference"
>>> ils1900 = pd.read_csv(ref_agg_dir / "build_hwp_stock_since_1900.csv")
>>> ils1990 = pd.read_csv(ref_agg_dir / "build_hwp_stock_since_1990.csv")
>>>
>>> plot_hwp_ils_facet_by_country(ils1900, "inflow", "hwp_inflow_by_country.png",
...                        title="Harvested Wood Products inflow amounts per year")
>>> plot_hwp_ils_facet_by_country(ils1900, "loss", "hwp_loss_by_country.png",
...                        title="Harvested Wood Products loss amounts per year")
>>> plot_hwp_ils_facet_by_country(ils1900, "stock", "hwp_stock_by_country.png",
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

from typing import Optional
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from eu_cbm_hat import eu_cbm_data_pathlib
from eu_cbm_hat.post_processor.sink import sum_litter_and_dead_wood


PLOT_DIR = eu_cbm_data_pathlib / "plot" / "hwp"
PLOT_DIR.mkdir(parents=True, exist_ok=True)
PRODUCT_PALETTE = {
    "sw_con": ("Sawnwood Coniferous", "chocolate"),
    "sw_broad": ("Sawnwood Broadleaves", "saddlebrown"),
    "wp": ("Wood Panels", "moccasin"),
    "pp": ("Paper", "lightskyblue"),
}

def plot_hwp_ils_facet_by_country(df: pd.DataFrame, variable: str, filename: str, title: Optional[str] = None) -> None:
    """
    Create a Seaborn scatter plot of HWP inflow, loss or stock (ils) with one
    facet per country. 

    The input data frame has details on the product level: sawnwood, panel and
    paper.

    Args:
        df (pd.DataFrame): The input DataFrame containing 'country', 'year',
        filename (str): The name of the file to save the plot to.

    Example:

    >>> import pandas as pd
    >>> from eu_cbm_hat import eu_cbm_data_pathlib
    >>> from eu_cbm_hat.plot.hwp_plots import plot_hwp_ils_facet_by_country
    >>> ref_agg_dir = eu_cbm_data_pathlib / "output_agg" / "reference"
    >>> ils1900 = pd.read_csv(ref_agg_dir / "post_processor_hwp_build_hwp_stock_since_1900.csv")
    >>> ils1990 = pd.read_csv(ref_agg_dir / "post_processor_hwp_build_hwp_stock_since_1990.csv")
    >>> plot_hwp_ils_facet_by_country(ils1900, "inflow", "hwp_inflow_by_country_start_1900.png",
    ...                               title="Harvested Wood Products inflow amounts per year")
    >>> plot_hwp_ils_facet_by_country(ils1900, "loss", "hwp_loss_by_country.png",
    ...                               title="Harvested Wood Products loss amounts per year")
    >>> plot_hwp_ils_facet_by_country(ils1900, "stock", "hwp_stock_by_country.png",
    ...                               title="Harvested Wood Products stock amounts per year")

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
    df_long['product_short'] = df_long['variable'].str.replace('_' + variable, '')
    df_long['product'] = df_long['product_short'].map(lambda p: PRODUCT_PALETTE[p][0])
    palette = {PRODUCT_PALETTE[k][0]: PRODUCT_PALETTE[k][1] for k in PRODUCT_PALETTE}
    df_long["value_m"] = df_long["value"] / 1e6
    g = sns.relplot(
        data=df_long,
        x="year",
        y="value_m",
        hue="product",
        col="country",
        palette=palette,
        facet_kws={"sharey": False, "sharex": False},
        kind='scatter',
        height=3,    # Height of each subplot
        aspect=1.2   # Aspect ratio of each subplot
    )
    g.set_axis_labels("Year", "Million tons of Carbon")
    if title is not None:
        g.fig.suptitle(title, y=1.03)
    # Adjust the plot to ensure labels don't overlap
    # plt.tight_layout(rect=[0, 0, 1, 0.98])
    g.savefig(PLOT_DIR / filename)


def plot_hwp_total_sink_facet_by_country(df_sink: pd.DataFrame, df_hwp_sink: pd.DataFrame) -> None:
    """Total sink including Harvested Wood Products and biomass sink

    Example use:

        >>> import pandas as pd
        >>> from eu_cbm_hat import eu_cbm_data_pathlib
        >>> from eu_cbm_hat.plot.hwp_plots import plot_hwp_total_sink_facet_by_country
        >>> ref_agg_dir = eu_cbm_data_pathlib / "output_agg" / "reference"
        >>> df_hwp_sink = pd.read_csv(ref_agg_dir / "post_processor_hwp_stock_sink_results.csv")
        >>> df_sink = pd.read_csv(ref_agg_dir / "post_processor_sink_df_agg_by_year.csv")
        >>> plot_hwp_total_sink_facet_by_country(df_sink, df_hwp_sink)

    """
    # Aggregate litter and dead wood into one column
    df_sink = sum_litter_and_dead_wood(df_sink)
    hwp_sink_cols = ["hwp_tot_sink_tco2_1900", "hwp_tot_sink_tco2_1990"]
    sink_cols = ["living_biomass_sink", "dom_sink", "soil_sink"]
    # Merge left with the HWP sink data frame first, to keep only results
    # available in the HWP sink data frame
    index = ["combo_name", "country", "year"]
    # Keep only HWP years available in the main sink data frame
    selector = df_hwp_sink["year"] > df_sink["year"].min()
    # 
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
        "dom_sink": "saddlebrown",
        "soil_sink": "peru",
    }
    df_long["value_m"] = df_long["value"] / 1e6
    g = sns.relplot(
        data=df_long,
        x="year",
        y="value_m",
        hue="sink_type",
        col="country",
        palette=sink_colors,
        facet_kws={"sharey": False, "sharex": False},
        height=3,    # Height of each subplot
        aspect=1.2   # Aspect ratio of each subplot
    )
    g.set_axis_labels("Year", "Sink million tons of CO2 eq")
    g.fig.suptitle("Total Sink Including Harvested Wood Products", y=1.03)
    g.savefig(PLOT_DIR / "total_sink_including_hwp.png")
