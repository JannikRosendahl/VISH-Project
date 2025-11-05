import pandas as pd


def compute_allowed_categories(df: pd.DataFrame, column: str, threshold: float, value_col: str | None = None) -> set:
    if df.empty or threshold <= 0:
        return set(df[column].dropna().unique())

    if value_col is None:
        counts = df[column].value_counts()
    else:
        counts = df.groupby(column)[value_col].sum()

    total = counts.sum()
    if total <= 0:
        return set(counts.index)

    rel = counts / total
    allowed = set(rel[rel >= threshold].index)
    if not allowed:
        return set(counts.index)
    return allowed


def maybe_filter_by_outliers(df: pd.DataFrame, column: str, exclude_outliers: bool, threshold: float, value_col: str | None = None) -> pd.DataFrame:
    if not exclude_outliers:
        return df
    allowed = compute_allowed_categories(df, column, threshold, value_col=value_col)
    if not allowed:
        return df
    return df[df[column].isin(allowed)]
