# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import os
from click import style
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

selectedMinDate = minTimestamp
selectedMaxDate = maxTimestamp

# Create a fixed color palette for each sub_event_type
sub_event_types = data['sub_event_type'].unique()
color_palette = px.colors.qualitative.Pastel
color_map = {sub_event: color_palette[i % len(color_palette)] for i, sub_event in enumerate(sorted(sub_event_types))}

data_filtered = data[(data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= selectedMinDate) &
                 (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= selectedMaxDate)]

first_of_years = data.groupby([data['event_date'].dt.year])['event_date'].min().sort_values()

def create_map(minTimestamp=minTimestamp, maxTimestamp=maxTimestamp):
    data_filtered = data[
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= minTimestamp) &
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= maxTimestamp)
    ]
    fig = px.scatter_map(
        data_filtered[['latitude', 'longitude', 'fatalities', 'country']],
        # data['fatalities'] > 0
        #  & ()
        lat='latitude',
        lon='longitude',
        #hover_name='name',
        hover_data=['fatalities'],
        color='country',
        color_discrete_sequence=px.colors.qualitative.Plotly,
        size='fatalities',
        zoom=5,
        #height=600,
    )
    fig.update_layout(
        #mapbox_style='open-street-map'
    )
    fig.update_traces(
        #cluster=dict(enabled=True)
    )
    return fig

app.layout = html.Div(children=[
    html.H1("Ukraine Dashboard"),
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

                        children=[dcc.Graph(id='map', figure=create_map(), style={'height': '90%', 'width': '100%'})],
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
                                    "placement": "bottom", 
                                    "always_visible": True,
                                    "transform": "formatTimestamp"
                                },
                                allowCross=False
                            ),
                            html.Div(id='date-slider-output', style={"margin" : "1rem"})
                        ],
                        style={"margin" : "1rem"}
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
            html.Div(
                children=[
                    html.Div(
                        children=[dcc.Graph(id='disorder-type-pie', style={'height': '100%', 'width': '100%'})],
                        style={'border': '1px solid #ccc'}
                    )
                ],
            )
        ]
    )
])

# Add callback for map
@app.callback(
    Output('map', 'figure'),
    Input('date-slider', 'value')
)
def update_map(date_range):
    start_ts, end_ts = date_range
    fig = create_map(start_ts, end_ts)
    return fig

@callback(
    Output('events-by-source', 'figure'),
    Input('date-slider', 'value')
)
def update_events_by_source(date_range):
    start_ts, end_ts = date_range
    filtered = data[
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= start_ts) &
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= end_ts)
    ]
    # Count events per source
    top_sources = (
        filtered.groupby(['source']).size()
        .nlargest(5)
        .index.tolist()
    )
    filtered_top = filtered[filtered['source'].isin(top_sources)]
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

# Add callback for bar chart
@callback(
    Output('event-type-bar', 'figure'),
    Input('date-slider', 'value')
)
def update_event_type_bar(date_range):
    start_ts, end_ts = date_range
    filtered = data[
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= start_ts) &
        (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= end_ts)
    ]
    event_counts = filtered.groupby(['event_type', 'sub_event_type']).size().reset_index(name='count')
    fig = px.bar(
        event_counts,
        x='event_type',
        y='count',
        color='sub_event_type',
        color_discrete_map=color_map,
        title='Event Type Breakdown by Sub Event Type',
        labels={'count': 'Number of Events', 'event_type': 'Event Type', 'sub_event_type': 'Sub Event Type'},
        barmode='stack'
    )
    return fig

@callback(
    Output('date-slider-output', 'children'),
    Input('date-slider', 'value')
)
def update_output(value):
    start_date = pd.to_datetime(value[0], unit='s').strftime('%Y-%m-%d')
    end_date = pd.to_datetime(value[1], unit='s').strftime('%Y-%m-%d')
    return f'Showing data starting from {start_date} to {end_date}'

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
