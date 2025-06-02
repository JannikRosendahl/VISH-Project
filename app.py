# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
import os
from dash import Dash, State, html, dcc, Input, Output, callback, ctx
import plotly.express as px
import pandas as pd

app = Dash()


def load_data() -> pd.DataFrame:
    file_name = 'Europe-Central-Asia_2018-2025_May02.csv'
    data_path = 'data/' + file_name
    url = 'http://www.jannik-rosendahl.com/data/' + file_name
    
    # check if the file exists locally
    try:
        with open(data_path, 'r') as f:
            data = pd.read_csv(f)
            print('Loaded data from local file')
    except FileNotFoundError:
        os.makedirs('data', exist_ok=True)
        print('Local file not found, downloading from URL, this may take a minute')
        data = pd.read_csv(url)
        data.to_csv(data_path, index=False)
        print('Downloaded data from URL and saved to local file')
    
    # data preprocessing
    data = data[data['actor1'].str.contains('ukraine|russia', case=False, na=False)]
    data['event_date'] = pd.to_datetime(data['event_date'])

    data['event_date_i'] = data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp()))
    return data

data = load_data()

minTimestamp = int(pd.Timestamp(data['event_date'].min().date()).timestamp())
maxTimestamp = int(pd.Timestamp(data['event_date'].max().date()).timestamp())

map_center = {}

# map color modes
color_modes = ['country', 'sub_event_type', 'event_date', 'fatalities']  # <-- Add 'fatalities' here
# sub_event_type color map
sub_event_type_color_map = {sub_event_type: px.colors.qualitative.Alphabet[i % len(px.colors.qualitative.Alphabet)] for i, sub_event_type in enumerate(sorted(data['sub_event_type'].unique()))}

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

# Configurable number of rows and columns for bottom widgets
WIDGET_ROWS = 3
WIDGET_COLS = 2

# Configurable minimum heights (in px)
MAP_MIN_HEIGHT = 600
WIDGET_MIN_HEIGHT = 400

# List of widget graph IDs (add or remove as needed)
widget_graphs = [
    ('fatalities-line', 'Fatalities Line'),
    ('subeventtype-line', 'Sub Event Type Over Time'),  # <-- Added new widget
    ('fatalities-pie', 'Fatalities Pie'),
    ('event-type-bar', 'Event Type Bar'),
    ('events-by-source', 'Events by Source'),
    ('events-over-time', 'Events Over Time'),
    # Add more widget IDs here if needed
]

app.title = 'Ukraine Dashboard'

app.layout = html.Div(
    style={
        'minHeight': '100vh',
        'backgroundColor': '#f7f9fa',
        'fontFamily': 'Segoe UI, Arial, sans-serif',
        'padding': '0',
        'margin': '0',
    },
    children=[
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
                'top': 0,  # <-- Set to 0 for true stickiness
                'zIndex': 1000
            },
            children=[
                html.Div(
                    'Ukraine Dashboard',
                    style={'flex': '0 0 auto'}
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
                'minHeight': 'calc(100vh - 120px)',
                'padding': '1rem'
            },
            children=[
                # Sidebar for controls
                html.Div(
                    style={
                        'width': '320px',
                        'backgroundColor': 'white',
                        'borderRadius': '12px',
                        'boxShadow': '0 2px 8px rgba(0,0,0,0.07)',
                        'padding': '2rem 1.5rem',
                        'marginRight': '2rem',
                        'display': 'flex',
                        'flexDirection': 'column',
                        'gap': '2rem',
                        'minWidth': '260px',
                        'maxHeight': '100%',
                        'overflowY': 'auto'
                    },
                    children=[
                        html.Div([
                            html.Label('Map Color Options', style={'fontWeight': 'bold'}),
                            dcc.RadioItems(
                                color_modes, color_modes[0], inline=True, id='map-color-selector',
                                style={'marginTop': '0.5rem'}
                            ),
                        ]),
                        html.Div([
                            dcc.Checklist(
                                ['Include Non-Fatal Events'],
                                ['Include Non-Fatal Events'],
                                id='bool_options',
                                style={'marginTop': '0.5rem'}
                            )
                        ]),
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
                            dcc.Graph(id='map', clear_on_unhover=True, style={'height': '100%', 'width': '100%'}),
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
                        # Dynamically generate widgets for the bottom area
                        *[
                            html.Div(
                                dcc.Graph(id=widget_id, style={'height': '100%', 'width': '100%'}),
                                className='widget',
                                style={
                                    'backgroundColor': 'white',
                                    'borderRadius': '12px',
                                    'boxShadow': '0 2px 8px rgba(0,0,0,0.07)',
                                    'padding': '1rem',
                                    'gridColumn': f'{(i % WIDGET_COLS) + 1}',
                                    'gridRow': f'{(i // WIDGET_COLS) + 2}',
                                    'minHeight': f'{WIDGET_MIN_HEIGHT}px',
                                    #'height': '100%'  # Make widget fill grid cell
                                }
                            )
                            for i, (widget_id, _) in enumerate(widget_graphs[:WIDGET_ROWS * WIDGET_COLS])
                        ]
                    ]
                ),
            ]
        )
    ]
)

def render_map(color_mode):
    global data_filtered
    global map_center

    hovertemplate = (
        "<b>🌍 Country:</b> %{customdata[1]}<br>"
        "<b>⚠️ Sub-Event-Type:</b> %{customdata[2]}<br>"
        "<b>👤 Actor 1:</b> %{customdata[3]}<br>"
        "<b>👤 Actor 2:</b> %{customdata[4]}<br>"
        "<b>🪦 Fatalities:</b> %{customdata[5]}<extra></extra>"
    )

    custom_data = ['event_id_cnty', 'country', 'sub_event_type', 'actor1', 'actor2', 'fatalities']

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
                color_continuous_scale=px.colors.sequential.matter,
                zoom=5,
                size='fatalities',
                custom_data=custom_data,
                opacity=0.8,
                labels={'fatalities': 'Fatalities'},
                center=map_center,
                height=600
            )
        case _:
            print('Invalid color mode, defaulting to country')
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
    return fig

@callback(Output('events-over-time', 'figure'), Input('date-slider', 'value'))
def update_events_over_time(interval):
    start_ts, end_ts = interval
    filtered = data[
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= start_ts) &
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= end_ts)
    ]
    unique_event_types = filtered.groupby(['event_date', 'sub_event_type']).size().reset_index(name='count')
    fig = px.area(
        unique_event_types,
        x='event_date',
        y='count',
        color='sub_event_type',
        title='Events Over Time',
        labels={'event_date': 'Date', 'count': 'Number of Events'}
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
    markers[int(pd.Timestamp(date).timestamp())] = { 'label': date.strftime('|'),'style': {"color": "blue", "fontSize": "60px", "transform": "translate(0, -35px)" } }
    return markers 


def render_events_by_source():
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

def render_event_type_bar():
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

def render_time_interval(minTimestamp, maxTimestamp):
    start_date = pd.to_datetime(minTimestamp, unit='s').strftime('%Y-%m-%d')
    end_date = pd.to_datetime(maxTimestamp, unit='s').strftime('%Y-%m-%d')
    return f'Showing data starting from {start_date} to {end_date}'

@callback([
    Output('map', 'figure'),
    Output('events-by-source', 'figure'),
    Output('event-type-bar', 'figure'),
    Output('date-slider-output', 'children')
], [
    Input('date-slider', 'value'),
    Input('map-color-selector', 'value'),
    Input('bool_options', 'value'),
], State('map', 'relayoutData'))
def update_df(interval, map_color_mode, bool_options, relayoutData):
    global data
    global data_filtered
    global map_center
    triggered_id = ctx.triggered_id
    # print(f'callback triggered by {triggered_id}, {interval=}, {map_color_mode=}, {bool_options=}')
    minTimestamp, maxTimestamp = interval
    data_filtered = data[
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= minTimestamp) &
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= maxTimestamp)
    ]
    if 'Include Non-Fatal Events' not in bool_options:
        data_filtered = data_filtered[data_filtered['fatalities'] > 0]

    map = render_map(map_color_mode)
    # print(relayoutData)
    if relayoutData and 'map.center' in relayoutData and 'map.zoom' in relayoutData:
        # print('trying to preserve map state')
        map_center = relayoutData['map.center']
        map.update_layout(
            mapbox_center=relayoutData['map.center'],
            mapbox_zoom=relayoutData['map.zoom']
        )

    return map, render_events_by_source(), render_event_type_bar(), render_time_interval(minTimestamp, maxTimestamp)

# add callback for fatalities line chart
@callback(
   Output('fatalities-line', 'figure'),
   Input('date-slider', 'value')
)
def update_fatalities_line(date_range):
    start_ts, end_ts = date_range
    filtered = data[
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= start_ts) &
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= end_ts)
    ]

    fatalities_by_date = filtered.groupby('event_date')['fatalities'].sum().reset_index()
    fatalities_by_date['fatalities'] = fatalities_by_date['fatalities'].cumsum()
    fig = px.line(
        fatalities_by_date,
        x='event_date',
        y='fatalities',
        title='Fatalities Over Time',
        labels={'event_date': 'Date', 'fatalities': 'Number of Fatalities'}
    )
    return fig

# add callback for fatalities by sub_event_type pie chart
@callback(
   Output('fatalities-pie', 'figure'),
   Input('date-slider', 'value')
)
def update_fatalities_pie(date_range):
    start_ts, end_ts = date_range
    filtered = data[
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= start_ts) &
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= end_ts)
    ]
    fatalities_by_sub_event = filtered.groupby('sub_event_type')['fatalities'].sum().reset_index()
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

# Add callback for sub_event_type stacked line chart
@callback(
    Output('subeventtype-line', 'figure'),
    Input('date-slider', 'value')
)
def update_subeventtype_line(date_range):
    start_ts, end_ts = date_range
    filtered = data[
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= start_ts) &
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= end_ts)
    ]
    # Group by date and sub_event_type
    grouped = (
        filtered.groupby(['event_date', 'sub_event_type'])
        .size()
        .reset_index(name='count')
    )
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
    app.run(debug=True)