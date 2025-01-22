"""Get statistics on the country data for publication purposes

Country data is accessible through runner.orig_data

Note: cannot attach this method to the runner.post_processor, because
initializing runner.post processor requires data in the output directory. A
method attached to the post_processor would not run for countries which have no
model run output yet. Sometimes you want statistics on all countries for the
country orig data on a laptop where the model has not been run in all countries
yet i.e. a laptop where the output directory is not available for most
countries.

Print unique classifier values in all countries:

    >>> from eu_cbm_hat.post_processor.orig_data_stats import classifiers_all_countries
    >>> classifiers_all = classifiers_all_countries(combo_name="reference")
    >>> for this_cl in classifiers_all["classifier"].unique():
    >>>     selector = classifiers_all["classifier"] == this_cl
    >>>     if this_cl == "forest_type":
    >>>         # Remove NF forest types
    >>>         selector &= ~classifiers_all["classifier_value_id"].str.contains("NF")
    >>>     print("\n\n", this_cl)
    >>>     df = classifiers_all.loc[selector]
    >>>     unique_values = df["classifier_value_id"].unique()
    >>>     print(len(unique_values), unique_values)

Prepare a table of unique classifier values and description in all EU countries:

    >>> selector = classifiers_all["country"] != "ZZ"
    >>> classif_unique = classifiers_all.loc[selector].value_counts(["classifier", "classifier_value_id", "name"], sort=False)
    >>> classif_unique.to_csv("/tmp/classifiers.csv")

"""
from eu_cbm_hat.core.continent import continent
from functools import cached_property
from eu_cbm_hat.post_processor.agg_combos import apply_to_all_countries
from eu_cbm_hat.post_processor.agg_combos import place_combo_name_and_country_first


def classifiers_one_country(combo_name: str, iso2_code: str):
    """Classifiers of the country orig_data in one country"""
    runner = continent.combos[combo_name].runners[iso2_code][-1]
    df = runner.country.orig_data["classifiers"].copy()
    selector = df["classifier_value_id"] == "_CLASSIFIER"
    df.loc[selector, "classifier"] = df.loc[selector, "name"]
    df["classifier"].ffill(inplace=True)
    df = place_combo_name_and_country_first(df, runner)
    selector = df["classifier_value_id"] != '_CLASSIFIER'
    return df.loc[selector].copy()


def classifiers_all_countries(combo_name):
    """Classifiers of the country orig data in all countries"""
    df_all = apply_to_all_countries(classifiers_one_country, combo_name=combo_name)
    return df_all
