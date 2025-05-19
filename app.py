# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import os
from dash import Dash, html, dcc, Input, Output, callback
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
    return data

data = load_data()

minTimestamp = int(pd.Timestamp(data['event_date'].min().date()).timestamp())
maxTimestamp = int(pd.Timestamp(data['event_date'].max().date()).timestamp())

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

app.layout = html.Div(children=[
    html.H1('Ukraine Dashboard'),
    html.Div(
        style={
            'display': 'grid',
            'gridTemplateColumns': '2fr 1fr',
            'gridTemplateRows': '2fr 1fr',
            'gap': '2px',
            'height': '100vh',
            'padding': '2px',
            'boxSizing': 'border-box',
        },
        children=[
            html.Div(
                children=[
                    html.Div(
                        children=[dcc.Graph(id='map', style={'height': '90%', 'width': '100%'})],
                        style={'border': '1px solid #ccc', }
                    ),
                    html.Div(
                        children=[
                            dcc.RangeSlider(
                                minTimestamp, maxTimestamp, 86400,  # 86400 seconds = 1 day
                                value=[minTimestamp, maxTimestamp],
                                id='date-slider',
                                marks={int(pd.Timestamp(date).timestamp()): date.strftime('%Y-%m-%d') for date in first_of_years},
                                tooltip={
                                    'placement': 'bottom', 
                                    'always_visible': True,
                                    'transform': 'formatTimestamp'
                                },
                                allowCross=False
                            ),
                            html.Div(id='date-slider-output', style={'margin' : '1rem'})
                        ],
                        style={'margin' : '1rem'}
                    )
                ]
            ),
            html.Div(
                children=[
                    html.Div(
                        children=[dcc.Graph(id='events-by-source', style={'height': '100%', 'width': '100%'})],
                        style={'border': '1px solid #ccc'}
                    )
                ],
            ),
            html.Div(
                children=[
                    html.Div(
                        children=[dcc.Graph(id='event-type-bar', style={'height': '100%', 'width': '100%'})],
                        style={'border': '1px solid #ccc'}
                    )
                ],
            ),
            # html.Div('Placeholder 4', style={
            #     'backgroundColor': '#f0f0f0',
            #     'display': 'flex',
            #     'alignItems': 'center',
            #     'justifyContent': 'center',
            #     'border': '2px dashed #aaa',
            #     'fontSize': '20px'
            # }),
            html.Div(id='notes'),
        ]
    )
])

def render_map():
    global data_filtered
    fig = px.scatter_map(
        data_filtered,
        lat='latitude',
        lon='longitude',
        hover_data=['fatalities'],
        color='country',
        color_discrete_map=country_color_map,
        zoom=5,
        custom_data=['event_id_cnty'],
        opacity=1
    )
    fig.update_layout(
        clickmode='event+select'
    )
    return fig

@callback(Output('notes', 'children'), Input('map', 'clickData'))
def update_notes(clickData):
    if clickData is None:
        return 'Click on a point on the map for details...'
    print(clickData)
    id = clickData['points'][0]['customdata'][0]
    point_data = data[data['event_id_cnty'] == id].iloc[0]
    return html.P(children=[
        f'Date: {point_data['event_date']}', html.Br(),
        f'Type: {point_data['sub_event_type']}', html.Br(),
        f'Fatalities: {point_data['fatalities']}', html.Br(),
        f'Notes: {point_data['notes']}', html.Br(),
    ])

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
], Input('date-slider', 'value'))
def update_df(interval):
    global data
    global data_filtered
    minTimestamp, maxTimestamp = interval
    data_filtered = data[
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= minTimestamp) &
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= maxTimestamp)
    ]
    return render_map(), render_events_by_source(), render_event_type_bar(), render_time_interval(minTimestamp, maxTimestamp)

if __name__ == '__main__':
    app.run(debug=True)