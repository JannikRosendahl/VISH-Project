# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
import copy
import os
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, State, callback, ctx, dcc, html

from data_utils import default_file, update_available_files, load_data
from geo_utils import load_geojson_files_with_featureid, merge_geojsons
from helpers import compute_allowed_categories, maybe_filter_by_outliers
import plot_utils as pu

debug = True
app = Dash(__name__)

def print_debug(*args, **kwargs):
    global debug
    if debug:
        print(*args, **kwargs)

available_files = update_available_files()

data = load_data(default_file)

# Use precomputed integer timestamps when available to avoid expensive per-row conversions
if 'event_date_i' in data.columns:
    minTimestamp = int(data['event_date_i'].min())
    maxTimestamp = int(data['event_date_i'].max())
else:
    minTimestamp = int(pd.Timestamp(data['event_date'].min().date()).timestamp())
    maxTimestamp = int(pd.Timestamp(data['event_date'].max().date()).timestamp())

relayoutData = {}
map_center = {}

# map color modes
color_modes = ['country', 'sub_event_type', 'event_date', 'fatalities']
choropleth_color_modes = data['event_type'].unique().tolist()

# color maps
sub_event_type_color_map = {s: px.colors.qualitative.Prism[i % len(px.colors.qualitative.Prism)] for i, s in enumerate(sorted(data['sub_event_type'].unique()))}
event_type_color_map = {et: px.colors.qualitative.Prism[i % len(px.colors.qualitative.Prism)] for i, et in enumerate(sorted(data['event_type'].unique()))}
country_palette = px.colors.qualitative.Alphabet
countries = sorted(data['country'].unique())
country_color_map = {}
for i, country in enumerate(countries):
    if country.lower() == 'ukraine':
        country_color_map[country] = 'blue'
    elif country.lower() == 'russia':
        country_color_map[country] = 'red'
    else:
        country_color_map[country] = country_palette[i % len(country_palette)]

if 'event_date_i' in data.columns:
    data_filtered = data[(data['event_date_i'] >= minTimestamp) & (data['event_date_i'] <= maxTimestamp)]
else:
    data_filtered = data[(data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= minTimestamp) &
                 (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= maxTimestamp)]

first_of_years = data.groupby([data['event_date'].dt.year])['event_date'].min().sort_values()

# Configurable number of rows and columns for widgets
WIDGET_ROWS = 10
WIDGET_COLS = 1

# Configurable minimum heights (in px)
MAP_MIN_HEIGHT = 600
WIDGET_MIN_HEIGHT = 400

# List of widget graph IDs (add or remove as needed)
widget_graphs = [
    ('fatalities-line-non-cumulative', 'Fatalities Per Day'),
    ('fatalities-line', 'Fatalities Line'),
    ('subeventtype-line', 'Sub Event Type Over Time'),  # <-- Added new widget
    ('fatalities-pie', 'Fatalities Pie'),
    ('event-type-pie', 'Event Type Pie'),
    ('event-type-bar', 'Event Type Bar'),
    ('events-by-source', 'Events by Source'),
    ('events-over-time', 'Events Over Time'),
    ('events-over-time-3d', 'Events Over Time 3D')
]

app.title = 'Conflict Monitor'

app.layout = html.Div(
    style={
        'minHeight': '100vh',
        'backgroundColor': '#f7f9fa',
        'fontFamily': 'Segoe UI, Arial, sans-serif',
        'padding': '0',
        'margin': '0',
    },
    children=[
        html.Div(id='update-metaelement', style={'display': 'none'}),
        html.Div(id='meta-update-dataset', style={'display': 'none'}),
        # Header row with title and date slider
        html.Header(
            style={
                'display': 'flex',
                'alignItems': 'center',
                'backgroundColor': '#1a2636',
                'color': 'white',
                'padding': '1.5rem 2rem',
                'fontSize': '2rem',
                'fontWeight': 'bold',
                'letterSpacing': '1px',
                'boxShadow': '0 2px 8px rgba(0,0,0,0.05)',
                'position': 'sticky',
                'top': 0,
                'zIndex': 1000,
            },
            children=[
                html.Div(
                    children=[
                        html.Div(
                            'Conflict Monitor',
                            id='header-title',
                            style={'flex': '0 0 auto'}
                        ),
                        html.Div(className='loader', id='loading-indicator'),
                    ],
                    style={'display': 'flex', 'flexDirection': 'column', 'marginTop': '0.5rem', 'alignItems': 'center', 'flex': '0 0 auto'}
                ),
                html.Div(
                    style={'flex': '1', 'marginLeft': '3rem', 'marginRight': '2rem'},
                    children=[
                        html.Label('Date Range', style={'fontWeight': 'bold', 'color': 'white', 'fontSize': '1.1rem'}),
                        dcc.RangeSlider(
                            minTimestamp, maxTimestamp, 86400,
                            value=[minTimestamp, maxTimestamp],
                            id='date-slider',
                            marks={int(pd.Timestamp(date).timestamp()): date.strftime('%Y-%m-%d') for date in first_of_years},
                            tooltip={'placement': 'bottom', 'always_visible': True, 'transform': 'formatTimestamp'},
                            allowCross=False
                        ),
                        html.Div(id='date-slider-output', style={'marginTop': '0.5rem', 'fontSize': '1rem', 'color': '#fff'}),
                    ]
                )
            ]
        ),
        # Main content area
        html.Main(
            style={
                'display': 'flex',
                'flexDirection': 'row',
                'flex': '1 5',
                'minHeight': 'calc(100vh - 120px)',
                'padding': '1rem'
            },
            children=[
                # Sidebar for controls
                html.Div(
                    style={
                        'backgroundColor': 'white',
                        'borderRadius': '12px',
                        'boxShadow': '0 2px 8px rgba(0,0,0,0.07)',
                        'padding': '2rem 1.5rem',
                        'marginRight': '2rem',
                        'display': 'flex',
                        'flexDirection': 'column',
                        'minWidth': '260px',
                        'maxWidth': '300px',
                        'maxHeight': '100%',
                        'overflowY': 'auto'
                    },
                    children=[
                        html.H3('Change Dataset', style={'fontWeight': 'bold'}),
                        dcc.Dropdown(
                            options=[{'label': file, 'value': file} for file in sorted(available_files, key=lambda x: x.lower())],
                            id='dataset-selector',
                            value=default_file,
                        ),
                        html.Button('Reload Dataset', id='reload-dataset-button', n_clicks=0, style={'width': '100%'}),
                        html.H3('Data Preprocessing', style={'fontWeight': 'bold'}),
                        html.Div([
                            html.Label('Actor Filter'),
                            dcc.Input(
                                id='preprocessing-actor-filter',
                                type='text',
                                value='ukraine|russia',
                                placeholder='Enter filter regex for actors (e.g. ukraine|russia)',
                                style={'width': '100%', 'marginBottom': '0.5rem'},
                                debounce=True
                            ),
                            html.Button('Filter', id='preprocessing-actor-filter-reload-button', n_clicks=0, style={'width': '100%'})
                        ]),
                        html.Div([
                            dcc.Checklist(
                                ['Include Non-Fatal Events'],
                                ['Include Non-Fatal Events'],
                                id='bool_options',
                                style={'marginTop': '0.5rem'}
                            )
                        ]),
                        html.Hr(style={'margin': '1rem 0'}),
                        html.H3('Map Color Options', style={'fontWeight': 'bold'}),
                        html.Div([
                            html.Label('Select Color Mode'),
                            dcc.RadioItems(
                                color_modes, color_modes[0], inline=True, id='map-color-selector',
                                style={'marginTop': '0.5rem'}
                            ),
                        ]),
                        html.Hr(style={'margin': '1rem 0'}),
                                html.Div(
                                    id='notes',
                                    style={
                                        'marginTop': '2rem',
                                        'padding': '1rem',
                                        'backgroundColor': '#f0f4f8',
                                        'borderRadius': '8px',
                                        'fontSize': '1rem',
                                        'minHeight': '80px'
                                    }
                                ),
                                html.Hr(style={'margin': '1rem 0'}),
                                html.H3('Display Options', style={'fontWeight': 'bold'}),
                                html.Div([
                                    dcc.Checklist(
                                        ['Exclude Outliers'],
                                        [],
                                        id='exclude-outliers-checkbox',
                                        style={'marginTop': '0.5rem'}
                                    ),
                                    html.Label('Outlier threshold (relative occurrence)', style={'marginTop': '0.5rem', 'display': 'block'}),
                                    dcc.Slider(
                                        id='outlier-threshold-slider',
                                        min=0.0,
                                        max=0.1,
                                        step=0.001,
                                        value=0.01,
                                        marks={0.0: '0%', 0.005: '0.5%', 0.01: '1%', 0.02: '2%', 0.05: '5%', 0.1: '10%'},
                                        tooltip={'placement': 'bottom', 'always_visible': False}
                                    )
                                ]),
                    ]
                ),
                # Main plots area
                html.Div(
                    id='main-plots',
                    children=[
                        # Map spans all columns on the first row
                        html.Div(
                            dcc.Graph(id='map', clear_on_unhover=True, style={}),
                            style={
                                'backgroundColor': 'white',
                                'borderRadius': '12px',
                                'boxShadow': '0 2px 8px rgba(0,0,0,0.07)',
                                'padding': '1rem',
                                'gridColumn': f'1 / span {WIDGET_COLS}',
                                'gridRow': '1',
                                'minHeight': f'{MAP_MIN_HEIGHT}px'
                            }
                        ),
                        # Choropleth map widget
                        html.Div(
                            [
                                html.Label('Choropleth Map Color Options', style={'fontWeight': 'bold'}),
                                dcc.RadioItems(
                                    choropleth_color_modes, choropleth_color_modes[0], inline=True, id='choropleth-map-color-selector',
                                    style={'marginTop': '0.5rem'}
                                ),
                                dcc.Graph(id='choropleth-map', style={'height': '100%', 'width': '100%'})
                            ],
                            className='widget',
                            style={
                                'backgroundColor': 'white',
                                'borderRadius': '12px',
                                'boxShadow': '0 2px 8px rgba(0,0,0,0.07)',
                                'padding': '1rem',
                                'gridColumn': f'1 / span {WIDGET_COLS}',
                                'gridRow': '2',
                                'minHeight': f'{MAP_MIN_HEIGHT}px',
                                'maxHeight' : '100%'
                            }
                        ),
                        # Dynamically generate widgets for the bottom area
                        *[
                            html.Div(
                                dcc.Graph(id=widget_id),
                                className='widget',
                                style={
                                    'backgroundColor': 'white',
                                    'borderRadius': '12px',
                                    'boxShadow': '0 2px 8px rgba(0,0,0,0.07)',
                                    'padding': '1rem',
                                    'gridColumn': f'{(i % WIDGET_COLS) + 1}',
                                    'gridRow': f'{(i // WIDGET_COLS) + 3}',
                                    'minHeight': f'{WIDGET_MIN_HEIGHT}px',
                                    'maxHeight': '100%'
                                }
                            )
                            for i, (widget_id, _) in enumerate(widget_graphs[:WIDGET_ROWS * WIDGET_COLS])
                        ],
                    ],
                    style={
                        'width': '100%',
                    }
                ),
            ]
        )
    ]
)

@callback([
    Output('meta-update-dataset', 'children'),
], [
    Input('dataset-selector', 'value'),
    Input('reload-dataset-button', 'n_clicks'),
], running=[
    (Output('loading-indicator', 'className'), 'loader on', 'loader')
])
def reload_dataset(selected_file: str, n_clicks: int):
    """
    This function is called by the dataset selector or the reload button.
    It reloads the data from the selected file and updates the notes.
    """
    global data
    global available_files

    print_debug(f'Reloading dataset. Triggered by {ctx.triggered_id}.')
    print_debug(f'Arguments: {n_clicks=}, {selected_file=}')

    if not selected_file:
        print_debug('No file selected, using default file.')
        selected_file = default_file

    data = load_data(selected_file)
    update_available_files()

    return [None]

@callback([
    Output('update-metaelement', 'children'),
], [
    Input('meta-update-dataset', 'children'),
    Input('date-slider', 'value'),
    Input('bool_options', 'value'),
    Input('preprocessing-actor-filter', 'value'),
    Input('preprocessing-actor-filter-reload-button', 'n_clicks')
], running=[
    (Output('loading-indicator', 'className'), 'loader on', 'loader')
])
def update_df(_, interval, bool_options: list[str], preprocessing_actor_filter: str, n_clicks: int):
    """
    This function is called by widgets which update the data selection.
    It filters the global `data` DataFrame into `data_filtered`.
    Then it returns a dummy output, which is used to trigger `update_widgets`.
    """
    global data
    global data_filtered

    print_debug(f'Updating data. Triggered by {ctx.triggered_id}.')
    print_debug(f'Arguments: {interval=}, {bool_options=}, {preprocessing_actor_filter=}, {n_clicks=}')

    minTimestamp, maxTimestamp = interval
    # Prefer precomputed integer timestamps for performance
    if 'event_date_i' in data.columns:
        data_filtered = data[(data['event_date_i'] >= minTimestamp) & (data['event_date_i'] <= maxTimestamp)]
    else:
        data_filtered = data[
            (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= minTimestamp) &
            (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= maxTimestamp)
        ]

    if 'Include Non-Fatal Events' not in bool_options:
        data_filtered = data_filtered[data_filtered['fatalities'] > 0]

    # data = data[data['actor1'].str.contains('ukraine|russia', case=False, na=False)]
    if preprocessing_actor_filter:
        data_filtered = data_filtered[data_filtered['actor1'].str.contains(preprocessing_actor_filter, case=False, na=False) |
                                      data_filtered['actor2'].str.contains(preprocessing_actor_filter, case=False, na=False)]

    print_debug(f'Filtered data contains {len(data_filtered)} rows.')

    return [None]
    
@callback([
    Output('map', 'figure'),
    Output('date-slider-output', 'children'),
    Output('event-type-pie', 'figure'),
    Output('choropleth-map', 'figure'),
    Output('events-over-time', 'figure'),
    Output('events-over-time-3d', 'figure'),
    Output('events-by-source', 'figure'),
    Output('event-type-bar', 'figure'),
    Output('fatalities-line', 'figure'),
    Output('fatalities-line-non-cumulative', 'figure'),
    Output('fatalities-pie', 'figure'),
    Output('subeventtype-line', 'figure'),
], [
    Input('update-metaelement', 'children'),
    Input('map-color-selector', 'value'),
    Input('choropleth-map-color-selector', 'value'),
    Input('exclude-outliers-checkbox', 'value'),
    Input('outlier-threshold-slider', 'value'),
], [
    State('map', 'relayoutData')
], running=[
    (Output('loading-indicator', 'className'), 'loader on', 'loader')
])
def update_widgets(arg, map_color_mode: str, choropleth_options: str, exclude_outliers_value, outlier_threshold_value, relayoutData):
    """
    This function is called by the `update_df` callback, or by a widget which changes display options.
    It updates all widgets in the app.
    """
    print_debug(f'Updating widgets. Triggered by {ctx.triggered_id}.')
    print_debug(f'Arguments: {arg=}, {map_color_mode=}, {choropleth_options=}')

    # Determine exclude flag from checklist value
    exclude_outliers = False
    try:
        exclude_outliers = 'Exclude Outliers' in (exclude_outliers_value or [])
    except Exception:
        exclude_outliers = False

    threshold = float(outlier_threshold_value or 0.01)

    return (
        pu.render_map(data_filtered, country_color_map, sub_event_type_color_map, map_center, map_color_mode, relayoutData),
        update_date_slider_text(minTimestamp, maxTimestamp),
        pu.update_event_type_pie(data_filtered, event_type_color_map, exclude_outliers, threshold),
        pu.update_choropleth(data_filtered, choropleth_options),
        pu.update_events_over_time(data_filtered, sub_event_type_color_map, exclude_outliers, threshold),
        pu.update_events_over_time_3d(data_filtered, sub_event_type_color_map, exclude_outliers, threshold),
        pu.update_events_by_source(data_filtered, sub_event_type_color_map, exclude_outliers, threshold),
        pu.update_event_type_bar(data_filtered, sub_event_type_color_map, exclude_outliers, threshold),
        pu.update_fatalities_line(data_filtered),
        pu.update_fatalities_line_non_cumulative(data_filtered),
        pu.update_fatalities_pie(data_filtered, sub_event_type_color_map, exclude_outliers, threshold),
        pu.update_subeventtype_line(data_filtered, sub_event_type_color_map, exclude_outliers, threshold),
    )


def render_map(color_mode, relayout_data=None):
    # now using plot_utils.render_map
    return pu.render_map(data_filtered, country_color_map, sub_event_type_color_map, map_center, color_mode, relayout_data)

def update_event_type_pie(exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    return pu.update_event_type_pie(data_filtered, event_type_color_map, exclude_outliers, outlier_threshold)

def update_choropleth(event_type_selector):
    return pu.update_choropleth(data_filtered, event_type_selector)

# geo json helpers moved to geo_utils


# helpers moved to helpers.py

def update_events_over_time(exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    return pu.update_events_over_time(data_filtered, sub_event_type_color_map, exclude_outliers, outlier_threshold)

def update_events_over_time_3d(exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    return pu.update_events_over_time_3d(data_filtered, sub_event_type_color_map, exclude_outliers, outlier_threshold)

@callback(Output('notes', 'children'), Input('map', 'clickData'))
def update_notes(clickData):
    if clickData is None:
        return 'Click on a point on the map for details...'
    id = clickData['points'][0]['customdata'][0]
    point_data = data[data['event_id_cnty'] == id].iloc[0]
    return html.P(children=[
        html.B(children=['Date: ']), f'{point_data['event_date']}', html.Br(),
        html.B(children=['Type: ']), f'{point_data['sub_event_type']}', html.Br(),
        html.B(children=['Fatalities: ']), f'{point_data['fatalities']}', html.Br(),
        html.B(children=['Notes: ']), f'{point_data['notes']}', html.Br(),
    ])

@callback(Output('date-slider', 'marks'), Input('map', 'clickData'))
def update_date_slider(clickData):
    markers = {int(pd.Timestamp(date).timestamp()): date.strftime('%Y-%m-%d') for date in first_of_years}
    if clickData is None:
        return markers
    id = clickData['points'][0]['customdata'][0]
    point_data = data[data['event_id_cnty'] == id].iloc[0]
    date = point_data['event_date']
    markers[int(pd.Timestamp(date).timestamp())] = {
        'label': date.strftime('|'),
        'style': {
            "color": "lightblue",
            "fontSize": "40px",
            "transform": "translate(-5px, -42px)" 
        }
    }
    return markers 

def update_events_by_source(exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    return pu.update_events_by_source(data_filtered, sub_event_type_color_map, exclude_outliers, outlier_threshold)

def update_event_type_bar(exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    return pu.update_event_type_bar(data_filtered, sub_event_type_color_map, exclude_outliers, outlier_threshold)

def update_date_slider_text(minTimestamp, maxTimestamp):
    global data_filtered
    start_date = pd.to_datetime(minTimestamp, unit='s').strftime('%Y-%m-%d')
    end_date = pd.to_datetime(maxTimestamp, unit='s').strftime('%Y-%m-%d')
    return f'Showing data starting from {start_date} to {end_date}. Currently showing {len(data_filtered)} events.'

def update_fatalities_line():
    return pu.update_fatalities_line(data_filtered)

def update_fatalities_line_non_cumulative():
    return pu.update_fatalities_line_non_cumulative(data_filtered)

def update_fatalities_pie(exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    return pu.update_fatalities_pie(data_filtered, sub_event_type_color_map, exclude_outliers, outlier_threshold)

def update_subeventtype_line(exclude_outliers: bool = False, outlier_threshold: float = 0.01):
    return pu.update_subeventtype_line(data_filtered, sub_event_type_color_map, exclude_outliers, outlier_threshold)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8050, debug=debug, dev_tools_hot_reload=debug, dev_tools_ui=debug)
server = app.server