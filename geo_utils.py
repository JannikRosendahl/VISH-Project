import os
import json
import copy
import chardet


def load_geojson_files_with_featureid(dir):
    geojson_data = {}

    def load_file_with_encoding(file_path):
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']
        with open(file_path, 'r', encoding=encoding) as f:
            return json.load(f)

    for filename in os.listdir(dir):
        if filename.endswith('.geojson'):
            f = load_file_with_encoding(os.path.join(dir, filename))
            features = [f]
            for feature in features:
                name = feature['properties'].get('name:en') or feature['properties'].get('name')
                if name == 'Kiev Oblast':
                    name = 'Kyiv'
                if name == 'Odessa Oblast':
                    name = 'Odesa'
                if name == 'Autonomous Republic of Crimea':
                    name = 'Crimea'
                if isinstance(name, str):
                    cleaned = name.replace('Oblast', '').strip()
                else:
                    cleaned = str(name)
                feature['properties']['name:en'] = cleaned
                feature_id = cleaned
                feature['id'] = feature_id
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
