import json
import re
from difflib import SequenceMatcher

def extract_json_from_response(response_text):
    cleaned = re.sub(r"```(json)?", "", response_text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {"error": "Failed to parse JSON from model response", "raw": cleaned}

def flatten_json(data, parent_key=''):
    flat_dict = {}
    if isinstance(data, list):
        for i, item in enumerate(data):
            new_key = f"{parent_key}_{i}" if parent_key else str(i)
            flat_dict.update(flatten_json(item, new_key))
    elif isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}_{key}" if parent_key else key
            flat_dict.update(flatten_json(value, new_key))
    else:
        flat_dict[parent_key] = str(data)
    return flat_dict

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()