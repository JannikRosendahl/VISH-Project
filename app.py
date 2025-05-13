# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.


from dash import Dash, html, dcc, Input, Output, callback
import plotly.express as px
import pandas as pd

app = Dash()

# Load data into application
df = pd.read_csv('./data/Ukraine_Black_Sea_2020_2025_May02.csv', sep=',')

minTimestamp = int(pd.Timestamp(pd.to_datetime(df['event_date']).min().date()).timestamp())
maxTimestamp = int(pd.Timestamp(pd.to_datetime(df['event_date']).max().date()).timestamp())

selectedMinDate = minTimestamp
selectedMaxDate = maxTimestamp

df['event_date'] = pd.to_datetime(df['event_date'])
df_filtered = df[(df['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) >= selectedMinDate) &
                 (df['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp())) <= selectedMaxDate)]

first_of_years = df.groupby([df['event_date'].dt.year])['event_date'].min().sort_values()

app.layout = html.Div(children=[
    html.H1(children='Ukraine Dashboard'),

    html.Div([
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
    ]),

    html.Div(children='''
        Dash: A web application framework for your data.
    ''')
]) 

@callback(
    Output('date-slider-output', 'children'),
    Input('date-slider', 'value'))
def update_output(value):
    start_date = pd.to_datetime(value[0], unit='s').strftime('%Y-%m-%d')
    end_date = pd.to_datetime(value[1], unit='s').strftime('%Y-%m-%d')
    return f'Showing data starting from {start_date} to {end_date}'

if __name__ == '__main__':
    app.run(debug=True)
