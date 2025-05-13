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


minTimestamp = int(pd.Timestamp(pd.to_datetime(data['event_date']).min().date()).timestamp())
maxTimestamp = int(pd.Timestamp(pd.to_datetime(data['event_date']).max().date()).timestamp())

selectedMinDate = minTimestamp
selectedMaxDate = maxTimestamp

data_filtered = data[(data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= selectedMinDate) &
                 (data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= selectedMaxDate)]

first_of_years = data.groupby([data['event_date'].dt.year])['event_date'].min().sort_values()

def create_map(minTimestamp=minTimestamp, maxTimestamp=maxTimestamp):
    fig = px.scatter_map(
        data[['latitude', 'longitude']],
        lat='latitude',
        lon='longitude',
        #hover_name='name',
        #hover_data=['lat', 'lon'],
        color_discrete_sequence=['blue'],
        zoom=10,
        #height=600
    )
    fig.update_layout(mapbox_style='open-street-map')
    fig.update_traces(marker=dict(size=5))
    return fig

app.layout = html.Div(
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
                    dcc.Graph(figure=create_map(), style={'height': '90%', 'width': '100%'}),
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
                            }
                        ),
                        html.Div(id='date-slider-output')
                    ]
                )
            ]
        ),
        html.Div('Placeholder 2', style={
            'backgroundColor': '#f0f0f0',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'border': '2px dashed #aaa',
            'fontSize': '20px'
        }),
        html.Div('Placeholder 3', style={
            'backgroundColor': '#f0f0f0',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'border': '2px dashed #aaa',
            'fontSize': '20px'
        }),
        html.Div('Placeholder 4', style={
            'backgroundColor': '#f0f0f0',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'border': '2px dashed #aaa',
            'fontSize': '20px'
        }),
    ]
)


@callback(
    Output('date-slider-output', 'children'),
    Input('date-slider', 'value')
)
def update_output(value):
    start_date = pd.to_datetime(value[0], unit='s').strftime('%Y-%m-%d')
    end_date = pd.to_datetime(value[1], unit='s').strftime('%Y-%m-%d')
    return f'Showing data starting from {start_date} to {end_date}'

if __name__ == '__main__':
    app.run(debug=True)
