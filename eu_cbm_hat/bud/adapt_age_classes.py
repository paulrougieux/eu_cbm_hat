"""Adapt the age_classes.csv input file to the growth cuves"""

import pandas as pd

def adapt_age_classes(growth_curves, age_class_length):
    """Adapt age_classes to the max age given in the growth curve and to the age class length

    Reduce the length of the age_classes.csv file according to the number of
    columns supplied in the growth_curves.csv in order to avoid this error:
    ValueError: expected 41 columns. This is defined as 10 classifiers plus 31 age classes
    File ~/repos/eu_cbm/libcbm_py/libcbm/input/sit/sit_yield_parser.py:54, in
    parse(yield_table, classifiers, classifier_values, age_classes)

    Example:

        >>> import pandas as pd
        >>> from eu_cbm_hat.bud.adapt_age_classes import adapt_age_classes
        >>> growth_curves = pd.DataFrame({"vol0" : [0], "vol1": [30], "vol2": [90]})
        >>> adapt_age_classes(growth_curves, 10)
        >>> adapt_age_classes(growth_curves, 1)

    """
    if age_class_length not in [1, 10]:
        msg = "Age class length can only take a value of 1 or 10."
        msg += f"\nCurrently age_class_length: {age_class_length}"
        raise ValueError(msg)
    vol_cols = growth_curves.columns[growth_curves.columns.str.contains("^vol")].to_list()
    df = pd.DataFrame({"vol_col" : vol_cols})
    df["age_class_id"] = df["vol_col"].str.replace("vol", "AGEID")
    df["size"] = age_class_length
    df.loc[0, "size"] = 0
    df.drop(columns={"vol_col"}, inplace=True)
    return df
