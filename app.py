# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import os
from dash import Dash, html, dcc, Input, Output, callback, ctx
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

# map color modes
color_modes = ['country', 'sub_event_type', 'event_date']
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
                                marks={
                                    int(pd.Timestamp(date).timestamp()): date.strftime('%Y-%m-%d') for date in first_of_years
                                },
                                tooltip={
                                    'placement': 'bottom',
                                    'always_visible': True,
                                    'transform': 'formatTimestamp'
                                },
                                allowCross=False
                            ),
                            html.Div(id='date-slider-output', style={'margin' : '1rem'}),
                            html.Div(
                                style={'margin' : '1rem'},
                                children=[
                                    'Map Color Options: ',
                                    dcc.RadioItems(color_modes, color_modes[0], inline=True, id='map-color-selector')
                                ]
                            ),
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

def render_map(color_mode):
    global data_filtered

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
                custom_data=['event_id_cnty'],
                opacity=1
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
                custom_data=['event_id_cnty'],
                opacity=1
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
                custom_data=['event_id_cnty'],
                opacity=1,
                labels={'event_date_i': 'Event Date'}
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
                custom_data=['event_id_cnty'],
                opacity=1
            )
    fig.update_layout(
        clickmode='event+select'
    )
    fig.update_traces(
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=1))
    )
    return fig

@callback(Output('notes', 'children'), Input('map', 'clickData'))
def update_notes(clickData):
    if clickData is None:
        return 'Click on a point on the map for details...'
    id = clickData['points'][0]['customdata'][0]
    point_data = data[data['event_id_cnty'] == id].iloc[0]
    return html.P(children=[
        f'Date: {point_data['event_date']}', html.Br(),
        f'Type: {point_data['sub_event_type']}', html.Br(),
        f'Fatalities: {point_data['fatalities']}', html.Br(),
        f'Notes: {point_data['notes']}', html.Br(),
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
])
def update_df(interval, value):
    global data
    global data_filtered
    triggered_id = ctx.triggered_id
    print(f'callback triggered by {triggered_id}, {interval=}, {value=}')
    minTimestamp, maxTimestamp = interval
    data_filtered = data[
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= minTimestamp) &
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= maxTimestamp)
    ]
    return render_map(value), render_events_by_source(), render_event_type_bar(), render_time_interval(minTimestamp, maxTimestamp)

# add callback for fatalities line chart
#@callback(
#    Output('fatalities-line', 'figure'),
#    Input('date-slider', 'value')
#)
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
#@callback(
#    Output('fatalities-pie', 'figure'),
#    Input('date-slider', 'value')
#)
def update_fatalities_pie(date_range):
    #start_ts, end_ts = date_range
    #filtered = data[
    #    (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= start_ts) &
    #    (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= end_ts)
    #]
    #fatalities_by_sub_event = filtered.groupby('sub_event_type')['fatalities'].sum().reset_index()
    fatalities_by_sub_event = data.groupby('sub_event_type')['fatalities'].sum().reset_index()
    # cummulate groups with less than 1% of total fatalities together as "other"
    total_fatalities = fatalities_by_sub_event['fatalities'].sum()
    other_group = fatalities_by_sub_event[fatalities_by_sub_event['fatalities'] / total_fatalities < 0.01]
    if not other_group.empty:
        other_group_sum = other_group['fatalities'].sum()
        other_group_name = 'Other'
        other_group_row = pd.DataFrame({'sub_event_type': [other_group_name], 'fatalities': [other_group_sum]})
        fatalities_by_sub_event = pd.concat(
            [fatalities_by_sub_event[~fatalities_by_sub_event['sub_event_type'].isin(other_group['sub_event_type'])],
             other_group_row])
    # Sort the DataFrame by fatalities in descending order
    fatalities_by_sub_event = fatalities_by_sub_event.sort_values(by='fatalities', ascending=False)

    fig = px.pie(
        fatalities_by_sub_event,
        values='fatalities',
        names='sub_event_type',
        title='Fatalities by Sub Event Type',
        labels={'fatalities': 'Number of Fatalities', 'sub_event_type': 'Sub Event Type'}
    )
    return fig

if __name__ == '__main__':
    app.run(debug=True)