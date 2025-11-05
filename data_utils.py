import os
import json
import chardet
import pandas as pd


default_file = '2022-01-01-2025-06-11-Europe.csv'


def update_available_files(data_path: str = 'data/') -> set:
    available_files = set()
    available_files.add(default_file)
    try:
        files = os.listdir(data_path)
        for file in files:
            if file.endswith('.csv'):
                available_files.add(file)
    except FileNotFoundError:
        pass
    return available_files


def load_data(file_name: str, data_path: str = 'data/') -> pd.DataFrame:
    path = os.path.join(data_path, file_name)
    try:
        with open(path, 'r') as f:
            data = pd.read_csv(f)
            print('Loaded data from local file')
    except FileNotFoundError:
        os.makedirs(data_path, exist_ok=True)
        print('Local file not found, downloading from URL, this may take a minute')
        url = 'http://www.jannik-rosendahl.com/data/' + file_name
        data = pd.read_csv(url)
        data.to_csv(path, index=False)
        print('Downloaded data from URL and saved to local file')

    data['event_date'] = pd.to_datetime(data['event_date'])
    data['event_date_i'] = data['event_date'].apply(lambda x: int(pd.Timestamp(x).timestamp()))
    return data
