import os
import json
from werkzeug.utils import secure_filename

def save_json_file(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_ocr_result(filename, data, results_folder):
    base_name = os.path.splitext(secure_filename(filename))[0]
    output_path = os.path.join(results_folder, f"{base_name}.json")
    save_json_file(output_path, data)
    return output_path