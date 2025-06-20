# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
import os
from dash import Dash, State, html, dcc, Input, Output, callback, ctx
import plotly.express as px
import pandas as pd
import json
import chardet
import copy

debug = True
app = Dash(__name__)

def print_debug(*args, **kwargs):
    global debug
    if debug:
        print(*args, **kwargs)

default_file = '2022-01-01-2025-06-11-Europe.csv'
available_files: set

def update_available_files() -> set[str]:
    global default_file
    available_files = set()
    available_files.add(default_file)

    data_path = 'data/'
    try:
        files = os.listdir(data_path)
        for file in files:
            if file.endswith('.csv'):
                available_files.add(file)
    except FileNotFoundError:
        pass
    print_debug(f'Available files: {available_files}')
    return available_files
available_files = update_available_files()

def load_data(file_name: str) -> pd.DataFrame:
    data_path = 'data/' + file_name
    
    # check if the file exists locally
    try:
        with open(data_path, 'r') as f:
            data = pd.read_csv(f)
            print('Loaded data from local file')
    except FileNotFoundError:
        os.makedirs('data', exist_ok=True)
        print('Local file not found, downloading from URL, this may take a minute')
        url = 'http://www.jannik-rosendahl.com/data/' + file_name
        data = pd.read_csv(url)
        data.to_csv(data_path, index=False)
        print('Downloaded data from URL and saved to local file')
    
    data['event_date'] = pd.to_datetime(data['event_date'])
    data['event_date_i'] = data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp()))
    return data

data = load_data(default_file)

minTimestamp = int(pd.Timestamp(data['event_date'].min().date()).timestamp())
maxTimestamp = int(pd.Timestamp(data['event_date'].max().date()).timestamp())

relayoutData = {}
map_center = {}

# map color modes
color_modes = ['country', 'sub_event_type', 'event_date', 'fatalities']
choropleth_color_modes = data['event_type'].unique().tolist()

sub_event_type_color_map = {set: px.colors.qualitative.Prism[i % len(px.colors.qualitative.Prism)] for i, set in enumerate(sorted(data['sub_event_type'].unique()))}
event_type_color_map = {et: px.colors.qualitative.Prism[i % len(px.colors.qualitative.Prism)] for i, et in enumerate(sorted(data['event_type'].unique()))}

# country color map
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
], [
    State('map', 'relayoutData')
], running=[
    (Output('loading-indicator', 'className'), 'loader on', 'loader')
])
def update_widgets(arg, map_color_mode: str, choropleth_options: str, relayoutData):
    """
    This function is called by the `update_df` callback, or by a widget which changes display options.
    It updates all widgets in the app.
    """
    print_debug(f'Updating widgets. Triggered by {ctx.triggered_id}.')
    print_debug(f'Arguments: {arg=}, {map_color_mode=}, {choropleth_options=}')

    return render_map(map_color_mode, relayoutData), \
        update_date_slider_text(minTimestamp, maxTimestamp), \
        update_event_type_pie(), \
        update_choropleth(choropleth_options), \
        update_events_over_time(), \
        update_events_over_time_3d(), \
        update_events_by_source(), \
        update_event_type_bar(), \
        update_fatalities_line(), \
        update_fatalities_line_non_cumulative(), \
        update_fatalities_pie(), \
        update_subeventtype_line()


def render_map(color_mode, relayout_data=None):
    global data_filtered
    global map_center

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
        case 'fatalities':  # <-- Add this case
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
            print_debug('Invalid color mode, defaulting to country')
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
        hovertemplate = hovertemplate
    )
    if relayoutData and 'map.center' in relayoutData and 'map.zoom' in relayoutData:
        print_debug('trying to preserve map state')
        map_center = relayoutData['map.center']
        fig.update_layout(
            mapbox_center=relayoutData['map.center'],
            mapbox_zoom=relayoutData['map.zoom']
        )
    return fig

def update_event_type_pie():
    global data_filtered

    event_counts = data_filtered['event_type'].value_counts().reset_index()
    event_counts.columns = ['event_type', 'count']
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

def update_choropleth(event_type_selector):
    global data_filtered

    filtered = data_filtered[data_filtered['country'].isin(['Ukraine'])]
    if len(filtered) == 0:
        print_debug('No data available for Ukraine, returning empty figure')
        return px.choropleth()
    
    # check if the event_type_selector has datapoints
    if event_type_selector not in filtered['event_type'].unique():
        print_debug(f'No data available for event type: {event_type_selector}, returning empty figure')
        return px.choropleth()

    # Gruppieren nach Region
    # Create a pivot table: rows = admin1, columns = event_type, values = event counts
    admin1_event_counts = pd.pivot_table(
        filtered,
        index='admin1',
        columns='event_type',
        values='event_id_cnty',  # or any column, since we use 'count'
        aggfunc='count',
        fill_value=0
    ).reset_index()

    # max event count for color range
    max_event_count = admin1_event_counts.get(event_type_selector, pd.Series([0])).max()

    # GeoJSON-Dateien laden

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

def load_geojson_files_with_featureid(dir):
    geojson_data = {}
    #print_debug("Loading GeoJSON files from directory:", dir)

    # Funktion zum Laden einer Datei mit automatischer Kodierungserkennung
    def load_file_with_encoding(file_path):
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)  # Kodierung erkennen
            encoding = result['encoding']
        with open(file_path, 'r', encoding=encoding) as f:
            return json.load(f)

    # Ukraine GeoJSONs laden
    for filename in os.listdir(dir):
        if filename.endswith('.geojson'):
            f = load_file_with_encoding(os.path.join(dir, filename))
            features = [f]
            for feature in features:
                name = feature['properties']['name:en']
                if name == 'Kiev Oblast':
                    name = 'Kyiv'
                if name == 'Odessa Oblast':
                    name = 'Odesa'
                if name == 'Autonomous Republic of Crimea':
                    name = 'Crimea'
                feature['properties']['name:en'] = name.replace('Oblast', '').strip()
                feature_id = feature['properties']['name:en']
                feature['id'] = feature_id  # Setze die ID basierend auf "name:en"
            geojson_data[filename] = f

    return geojson_data

def merge_geojsons(geojson_dict):
    merged = {
        "type": "FeatureCollection",
        "features": []
    }
    for g in geojson_dict.values():
        if "features" in g:
            merged["features"].extend(copy.deepcopy(g["features"]))
        elif g.get("type") == "Feature":
            merged["features"].append(copy.deepcopy(g))
    return merged

def update_events_over_time():
    global data_filtered
    unique_event_types = data_filtered.groupby(['event_date', 'sub_event_type']).size().reset_index(name='count')
    fig = px.line(
        unique_event_types,
        x='event_date',
        y='count',
        line_group='sub_event_type',
        color='sub_event_type',
        color_discrete_map=sub_event_type_color_map,
        title='Events Over Time',
        labels={'event_date': 'Date', 'count': 'Number of Events'},
    )
    return fig

def update_events_over_time_3d():
    global data_filtered
    unique_event_types = data_filtered.groupby(['event_date', 'sub_event_type']).size().reset_index(name='count')
    fig = px.line_3d(
        unique_event_types,
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

def update_events_by_source():
    global data_filtered
    # Count events per source
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
    # Sort by total number of reports per source (descending)
    source_totals = source_event_counts.groupby('source')['count'].sum().sort_values(ascending=False)
    source_event_counts['source'] = pd.Categorical(
        source_event_counts['source'],
        categories=source_totals.index,
        ordered=True
    )
    source_event_counts = source_event_counts.sort_values(['source', 'sub_event_type'])
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

def update_event_type_bar():
    global data_filtered
    event_counts = data_filtered.groupby(['event_type', 'sub_event_type']).size().reset_index(name='count')
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

def update_date_slider_text(minTimestamp, maxTimestamp):
    global data_filtered
    start_date = pd.to_datetime(minTimestamp, unit='s').strftime('%Y-%m-%d')
    end_date = pd.to_datetime(maxTimestamp, unit='s').strftime('%Y-%m-%d')
    return f'Showing data starting from {start_date} to {end_date}. Currently showing {len(data_filtered)} events.'

def update_fatalities_line():
    global data_filtered
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

def update_fatalities_line_non_cumulative():
    global data_filtered
    fatalities_by_date = data_filtered.groupby('event_date')['fatalities'].sum().reset_index()
    fig = px.line(
        fatalities_by_date,
        x='event_date',
        y='fatalities',
        title='Fatalities Per Day',
        labels={'event_date': 'Date', 'fatalities': 'Number of Fatalities'}
    )
    return fig

def update_fatalities_pie():
    global data_filtered
    fatalities_by_sub_event = data_filtered.groupby('sub_event_type')['fatalities'].sum().reset_index()
    total_fatalities = fatalities_by_sub_event['fatalities'].sum()
    other_group = fatalities_by_sub_event[fatalities_by_sub_event['fatalities'] / total_fatalities < 0.01]
    if not other_group.empty:
        other_group_sum = other_group['fatalities'].sum()
        other_group_name = 'Other'
        other_group_row = pd.DataFrame({'sub_event_type': [other_group_name], 'fatalities': [other_group_sum]})
        fatalities_by_sub_event = pd.concat(
            [fatalities_by_sub_event[~fatalities_by_sub_event['sub_event_type'].isin(other_group['sub_event_type'])],
             other_group_row])
    fatalities_by_sub_event = fatalities_by_sub_event.sort_values(by='fatalities', ascending=False)

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

def update_subeventtype_line():
    global data_filtered
    # Group by date and sub_event_type
    grouped = data_filtered.groupby(['event_date', 'sub_event_type']).size().reset_index(name='count')

    # check if there are any data points
    if grouped.empty:
        print_debug('No data available for sub event types, returning empty figure')
        return px.area()
    
    # Pivot for stacked line chart
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

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8050, debug=debug, dev_tools_hot_reload=debug, dev_tools_ui=debug)
server = app.server