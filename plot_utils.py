from typing import Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from geo_utils import load_geojson_files_with_featureid, merge_geojsons
from helpers import compute_allowed_categories


def render_map(data_filtered: pd.DataFrame, country_color_map: dict, sub_event_type_color_map: dict, map_center: dict, color_mode: str, relayoutData=None):
    hovertemplate = (
        "<b>🌍 Country:</b> %{customdata[1]}<br>"
        "<b>⚠️ Sub-Event-Type:</b> %{customdata[2]}<br>"
        "<b>📅 Date:</b> %{customdata[3]}<br>"
        "<b>👤 Actor 1:</b> %{customdata[4]}<br>"
        "<b>👤 Actor 2:</b> %{customdata[5]}<br>"
        "<b>🪦 Fatalities:</b> %{customdata[6]}<extra></extra>"
    )
    custom_data = ['event_id_cnty', 'country', 'sub_event_type', 'event_date', 'actor1', 'actor2', 'fatalities']

    match color_mode:
        case 'country':
            fig = px.scatter_map(
                data_filtered,
                lat='latitude',
                lon='longitude',
                hover_data=['fatalities'],
                color='country',
                color_discrete_map=country_color_map,
                zoom=5,
                custom_data=custom_data,
                opacity=1,
                center=map_center,
                height=600
            )
        case 'sub_event_type':
            fig = px.scatter_map(
                data_filtered,
                lat='latitude',
                lon='longitude',
                hover_data=['fatalities'],
                color='sub_event_type',
                color_discrete_map=sub_event_type_color_map,
                zoom=5,
                custom_data=custom_data,
                opacity=1,
                center=map_center,
                height=600
            )
        case 'event_date':
            fig = px.scatter_map(
                data_filtered,
                lat='latitude',
                lon='longitude',
                hover_data=['fatalities'],
                color='event_date_i',
                color_continuous_scale=px.colors.sequential.Plasma,
                zoom=5,
                custom_data=custom_data,
                opacity=1,
                labels={'event_date_i': 'Event Date'},
                center=map_center,
                height=600
            )
        case 'fatalities':
            fig = px.scatter_map(
                data_filtered,
                lat='latitude',
                lon='longitude',
                hover_data=['fatalities'],
                color='fatalities',
                color_continuous_scale=px.colors.sequential.Bluered,
                zoom=5,
                size='fatalities',
                custom_data=custom_data,
                opacity=0.8,
                labels={'fatalities': 'Fatalities'},
                center=map_center,
                height=600
            )
        case _:
            fig = px.scatter_map(
                data_filtered,
                lat='latitude',
                lon='longitude',
                hover_data=['fatalities'],
                color='country',
                color_discrete_map=country_color_map,
                zoom=5,
                custom_data=custom_data,
                opacity=1,
                center=map_center,
                height=600
            )

    fig.update_layout(
        clickmode='event+select',
        margin=dict(t=0, b=0, l=0, r=0),
        autosize=False
    )
    fig.update_traces(
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=1)),
        hovertemplate=hovertemplate
    )
    if relayoutData and 'map.center' in relayoutData and 'map.zoom' in relayoutData:
        fig.update_layout(
            mapbox_center=relayoutData['map.center'],
            mapbox_zoom=relayoutData['map.zoom']
        )
    return fig


def update_event_type_pie(data_filtered: pd.DataFrame, event_type_color_map: dict, exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    event_counts = data_filtered['event_type'].value_counts().reset_index()
    event_counts.columns = ['event_type', 'count']

    if exclude_outliers:
        allowed = compute_allowed_categories(data_filtered, 'event_type', outlier_threshold)
        event_counts = event_counts[event_counts['event_type'].isin(allowed)]

    if event_counts.empty:
        return px.pie()

    fig = px.pie(
        event_counts,
        values='count',
        names='event_type',
        title='Percentage of Total Events by Event Type',
        labels={'event_type': 'Event Type', 'count': 'Number of Events'},
        color='event_type',
        color_discrete_map={et: event_type_color_map.get(et, px.colors.qualitative.Alphabet[0]) for et in event_counts['event_type']}
    )
    return fig


def update_choropleth(data_filtered: pd.DataFrame, event_type_selector: str):
    filtered = data_filtered[data_filtered['country'].isin(['Ukraine'])]
    if len(filtered) == 0:
        return px.choropleth()

    if event_type_selector not in filtered['event_type'].unique():
        return px.choropleth()

    admin1_event_counts = pd.pivot_table(
        filtered,
        index='admin1',
        columns='event_type',
        values='event_id_cnty',
        aggfunc='count',
        fill_value=0
    ).reset_index()

    max_event_count = admin1_event_counts.get(event_type_selector, pd.Series([0])).max()

    ukraine_geojson_directory = 'geodata/ukraine_geojson/'
    geojson_files = load_geojson_files_with_featureid(ukraine_geojson_directory)
    merged_geojson = merge_geojsons(geojson_files)

    fig = px.choropleth_map(
        admin1_event_counts,
        geojson=merged_geojson,
        color=event_type_selector,
        locations="admin1",
        featureidkey="id",
        color_continuous_scale=px.colors.sequential.matter,
        range_color=[0, max_event_count],
        map_style="carto-positron",
        center={"lat": 49, "lon": 32},
        zoom=3
    )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig


def update_events_over_time(data_filtered: pd.DataFrame, sub_event_type_color_map: dict, exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    grouped_df = data_filtered.groupby(['event_date', 'sub_event_type']).size().reset_index(name='count')

    if exclude_outliers:
        allowed = compute_allowed_categories(data_filtered, 'sub_event_type', outlier_threshold)
        grouped_df = grouped_df[grouped_df['sub_event_type'].isin(allowed)]

    if grouped_df.empty:
        return px.line()

    fig = px.line(
        grouped_df,
        x='event_date',
        y='count',
        line_group='sub_event_type',
        color='sub_event_type',
        color_discrete_map=sub_event_type_color_map,
        title='Events Over Time',
        labels={'event_date': 'Date', 'count': 'Number of Events'},
    )
    return fig


def update_events_over_time_3d(data_filtered: pd.DataFrame, sub_event_type_color_map: dict, exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    grouped_df = data_filtered.groupby(['event_date', 'sub_event_type']).size().reset_index(name='count')

    if exclude_outliers:
        allowed = compute_allowed_categories(data_filtered, 'sub_event_type', outlier_threshold)
        grouped_df = grouped_df[grouped_df['sub_event_type'].isin(allowed)]

    if grouped_df.empty:
        return px.line_3d()

    fig = px.line_3d(
        grouped_df,
        x='event_date',
        y='sub_event_type',
        z='count',
        line_group='sub_event_type',
        color='sub_event_type',
        color_discrete_map=sub_event_type_color_map,
        title='Events Over Time 3D',
        labels={'event_date': 'Date', 'sub_event_type' : 'Sub Event Type', 'count': 'Number of Events'},
    )
    return fig


def update_events_by_source(data_filtered: pd.DataFrame, sub_event_type_color_map: dict, exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    top_sources = (
        data_filtered.groupby(['source']).size()
        .nlargest(5)
        .index.tolist()
    )
    filtered_top = data_filtered[data_filtered['source'].isin(top_sources)]
    source_event_counts = (
        filtered_top.groupby(['source', 'sub_event_type'])
        .size()
        .reset_index(name='count')
    )

    if exclude_outliers:
        allowed = compute_allowed_categories(data_filtered, 'sub_event_type', outlier_threshold)
        source_event_counts = source_event_counts[source_event_counts['sub_event_type'].isin(allowed)]

    source_totals = source_event_counts.groupby('source')['count'].sum().sort_values(ascending=False)
    source_event_counts['source'] = pd.Categorical(
        source_event_counts['source'],
        categories=source_totals.index,
        ordered=True
    )
    source_event_counts = source_event_counts.sort_values(['source', 'sub_event_type'])

    if source_event_counts.empty:
        return px.bar()

    fig = px.bar(
        source_event_counts,
        x='source',
        y='count',
        color='sub_event_type',
        color_discrete_map=sub_event_type_color_map,
        title='Top 5 Reporting Sources and Sub Event Types',
        labels={'count': 'Number of Events', 'source': 'Source', 'sub_event_type': 'Sub Event Type'},
        barmode='stack'
    )
    return fig


def update_event_type_bar(data_filtered: pd.DataFrame, sub_event_type_color_map: dict, exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    event_counts = data_filtered.groupby(['event_type', 'sub_event_type']).size().reset_index(name='count')

    if exclude_outliers:
        allowed = compute_allowed_categories(data_filtered, 'sub_event_type', outlier_threshold)
        event_counts = event_counts[event_counts['sub_event_type'].isin(allowed)]

    if event_counts.empty:
        return px.bar()

    fig = px.bar(
        event_counts,
        x='event_type',
        y='count',
        color='sub_event_type',
        color_discrete_map=sub_event_type_color_map,
        title='Event Type Breakdown by Sub Event Type',
        labels={'count': 'Number of Events', 'event_type': 'Event Type', 'sub_event_type': 'Sub Event Type'},
        barmode='stack'
    )
    return fig


def update_fatalities_line(data_filtered: pd.DataFrame):
    fatalities_by_date = data_filtered.groupby('event_date')['fatalities'].sum().reset_index()
    fatalities_by_date['fatalities'] = fatalities_by_date['fatalities'].cumsum()
    fig = px.line(
        fatalities_by_date,
        x='event_date',
        y='fatalities',
        title='Fatalities Over Time',
        labels={'event_date': 'Date', 'fatalities': 'Number of Fatalities'}
    )
    return fig


def update_fatalities_line_non_cumulative(data_filtered: pd.DataFrame, trend_window: int = 7*2):
    """Return fatalities per day chart with trend and cumulative fatalities on a secondary y-axis.

    - Primary y-axis: daily fatalities and rolling trend.
    - Secondary y-axis: cumulative fatalities (same time axis).
    """
    fatalities_by_date = data_filtered.groupby('event_date')['fatalities'].sum().reset_index()

    # If no data, return an empty figure
    if fatalities_by_date.empty:
        return px.line()

    # Ensure the dates are sorted before computing rolling average
    fatalities_by_date = fatalities_by_date.sort_values('event_date')

    # Compute rolling trend
    fatalities_by_date['trend'] = (
        fatalities_by_date['fatalities']
        .rolling(window=trend_window, min_periods=1)
        .mean()
    )

    # Compute cumulative fatalities for the secondary axis
    fatalities_by_date['cumulative'] = fatalities_by_date['fatalities'].cumsum()

    # Create a subplot with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Base daily fatalities line (lighter, thinner) on primary y-axis
    fig.add_trace(
        go.Scatter(
            x=fatalities_by_date['event_date'],
            y=fatalities_by_date['fatalities'],
            mode='lines',
            name='Daily Fatalities',
            line=dict(color='blue', width=1),
            hovertemplate='%{x}<br>Daily: %{y}<extra></extra>'
        ),
        secondary_y=False,
    )

    # Trend line on primary y-axis (drawn on top)
    fig.add_trace(
        go.Scatter(
            x=fatalities_by_date['event_date'],
            y=fatalities_by_date['trend'],
            mode='lines',
            name=f'{trend_window}-day rolling avg',
            line=dict(
                color='crimson',
                #dash='dash',
                width=3
            ),
            hovertemplate='%{x}<br>Trend: %{y:.1f}<extra></extra>'
        ),
        secondary_y=False,
    )

    # Cumulative fatalities on secondary y-axis (scaled, thicker)
    fig.add_trace(
        go.Scatter(
            x=fatalities_by_date['event_date'],
            y=fatalities_by_date['cumulative'],
            mode='lines',
            name='Cumulative Fatalities',
            line=dict(color='lightgray', width=3),
            hovertemplate='%{x}<br>Cumulative: %{y}<extra></extra>'
        ),
        secondary_y=True,
    )

    # Layout: label axes and make the secondary axis readable
    fig.update_layout(
        title='Fatalities per Day (daily, trend, cumulative)',
        xaxis_title='Date',
        legend_title_text='Series',
        template='plotly_white'
    )

    fig.update_yaxes(title_text='Daily Fatalities', secondary_y=False)
    fig.update_yaxes(title_text='Cumulative Fatalities', secondary_y=True)

    return fig


def update_events_per_day_by_category(data_filtered: pd.DataFrame, category_col: str = 'event_type', trend_window: int = 7, exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    """Plot events per day for each category with a rolling trend and cumulative on a secondary axis.

    Parameters
    - data_filtered: DataFrame with at least 'event_date' and the category_col.
    - category_col: column name to group by (default 'event_type').
    - trend_window: window size (days) for the rolling average trend.
    """
    # Group and pivot so each category is a column with daily counts
    grouped = (
        data_filtered.groupby(['event_date', category_col])
        .size()
        .reset_index(name='count')
    )

    if grouped.empty:
        return px.line()

    pivot = grouped.pivot(index='event_date', columns=category_col, values='count').fillna(0)
    pivot = pivot.sort_index()

    # Optionally exclude rare categories (outliers)
    if exclude_outliers:
        allowed = compute_allowed_categories(data_filtered, category_col, outlier_threshold)
        # keep original column order but only allowed categories
        categories = [c for c in pivot.columns if c in allowed]
        if not categories:
            return px.line()
        pivot = pivot[categories]
    else:
        categories = list(pivot.columns)
    palette = px.colors.qualitative.Plotly
    # ensure enough colors by cycling
    from itertools import cycle
    color_cycle = cycle(palette)
    color_map = {cat: next(color_cycle) for cat in categories}

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # For each category, add daily, trend, and cumulative traces
    for cat in categories:
        daily = pivot[cat]
        trend = daily.rolling(window=trend_window, min_periods=1).mean()
        cumulative = daily.cumsum()

        color = color_map.get(cat, 'gray')

        # Daily (primary axis) - light thin line
        fig.add_trace(
            go.Scatter(
                x=pivot.index,
                y=daily,
                mode='lines',
                name=f'{cat} - Daily',
                legendgroup=cat,
                line=dict(color=color, width=1),
                opacity=0.6,
                hovertemplate=f'%{{x}}<br>{cat} Daily: %{{y}}<extra></extra>'
            ),
            secondary_y=False,
        )

        # Trend (primary axis) - dashed thicker line
        fig.add_trace(
            go.Scatter(
                x=pivot.index,
                y=trend,
                mode='lines',
                name=f'{cat} - Trend',
                legendgroup=cat,
                line=dict(color=color, dash='dash', width=2.5),
                hovertemplate=f'%{{x}}<br>{cat} Trend: %{{y:.1f}}<extra></extra>'
            ),
            secondary_y=False,
        )

        # Cumulative (secondary axis) - solid thicker line
        fig.add_trace(
            go.Scatter(
                x=pivot.index,
                y=cumulative,
                mode='lines',
                name=f'{cat} - Cumulative',
                legendgroup=cat,
                line=dict(color=color, width=2.5),
                hovertemplate=f'%{{x}}<br>{cat} Cumulative: %{{y}}<extra></extra>'
            ),
            secondary_y=True,
        )

    fig.update_layout(
        title=f'Events per Day by {category_col} (daily, trend, cumulative)',
        xaxis_title='Date',
        legend_title_text='Series',
        template='plotly_white'
    )

    fig.update_yaxes(title_text='Daily Events', secondary_y=False)
    fig.update_yaxes(title_text='Cumulative Events', secondary_y=True)

    return fig


def update_fatalities_pie(data_filtered: pd.DataFrame, sub_event_type_color_map: dict, exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    fatalities_by_sub_event = data_filtered.groupby('sub_event_type')['fatalities'].sum().reset_index()

    if exclude_outliers:
        allowed = compute_allowed_categories(data_filtered, 'sub_event_type', outlier_threshold, value_col='fatalities')
        fatalities_by_sub_event = fatalities_by_sub_event[fatalities_by_sub_event['sub_event_type'].isin(allowed)]
    else:
        total_fatalities = fatalities_by_sub_event['fatalities'].sum()
        if total_fatalities > 0:
            other_group = fatalities_by_sub_event[fatalities_by_sub_event['fatalities'] / total_fatalities < 0.01]
            if not other_group.empty:
                other_group_sum = other_group['fatalities'].sum()
                other_group_name = 'Other'
                other_group_row = pd.DataFrame({'sub_event_type': [other_group_name], 'fatalities': [other_group_sum]})
                fatalities_by_sub_event = pd.concat(
                    [fatalities_by_sub_event[~fatalities_by_sub_event['sub_event_type'].isin(other_group['sub_event_type'])],
                     other_group_row])

    fatalities_by_sub_event = fatalities_by_sub_event.sort_values(by='fatalities', ascending=False)

    if fatalities_by_sub_event.empty:
        return px.pie()

    fig = px.pie(
        fatalities_by_sub_event,
        values='fatalities',
        names='sub_event_type',
        title='Fatalities by Sub Event Type',
        labels={'fatalities': 'Number of Fatalities', 'sub_event_type': 'Sub Event Type'},
        color='sub_event_type',
        color_discrete_map=sub_event_type_color_map,
    )
    return fig


def update_subeventtype_line(data_filtered: pd.DataFrame, sub_event_type_color_map: dict, exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    grouped = data_filtered.groupby(['event_date', 'sub_event_type']).size().reset_index(name='count')

    if exclude_outliers:
        allowed = compute_allowed_categories(data_filtered, 'sub_event_type', outlier_threshold)
        grouped = grouped[grouped['sub_event_type'].isin(allowed)]

    if grouped.empty:
        return px.area()

    pivot = grouped.pivot(index='event_date', columns='sub_event_type', values='count').fillna(0).cumsum()
    fig = px.area(
        pivot,
        x=pivot.index,
        y=pivot.columns,
        title='Cumulative Events by Sub Event Type Over Time',
        labels={'value': 'Number of Events', 'event_date': 'Date', 'variable': 'Sub Event Type'},
        color_discrete_map=sub_event_type_color_map,
    )
    fig.update_layout(legend_title_text='Sub Event Type')
    return fig
