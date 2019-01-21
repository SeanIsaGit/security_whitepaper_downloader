import json
from pprint import pprint


def read_json(json_file):
    with open(json_file) as conf_file:
        data = json.load(conf_file)
    return data

def write_json(data, out_file):
    with open(out_file, 'w') as f:
        json.dump(data, f, ensure_ascii=False, sort_keys=True, indent=4)
