import os
import json
import pandas as pd
from werkzeug.utils import secure_filename
from app.utils.file_handling import save_json_file

def process_uploaded_csv(csv_file, upload_folder, results_folder):
    csv_path = os.path.join(upload_folder, secure_filename(csv_file.filename))
    csv_file.save(csv_path)
    
    try:
        df = pd.read_csv(
            csv_path,
            quotechar='"',
            escapechar='\\',
            engine='python',
            on_bad_lines='warn',
            encoding='utf-8'
        )
    except pd.errors.ParserError as e:
        raise ValueError(f"CSV parsing failed: {str(e)}")
    
    required_columns = {'ground_truth'}
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    
    output_list = []
    for idx, row in df.iterrows():
        image_path = str(row.get('image_path', f"row_{idx+1}")).strip()
        original_filename = image_path if pd.notna(image_path) else f"row_{idx+1}"
        standardized_filename = f"image_{idx}.json"
        
        gt_json_raw = row.get('ground_truth')
        if pd.isna(gt_json_raw) or gt_json_raw is None:
            gt_json_str = '{}'
            gt_json_obj = {}
        else:
            gt_json_str = str(gt_json_raw).strip()
            try:
                gt_json_obj = json.loads(gt_json_str)
            except json.JSONDecodeError as e:
                gt_json_obj = {"error": f"Invalid JSON in ground_truth: {str(e)}", "raw": gt_json_str}
        
        result_entry = {
            "filename": standardized_filename,
            "gt_parse": gt_json_obj.get("gt_parse", {})
        }
        
        if "error" in gt_json_obj:
            result_entry["error"] = gt_json_obj["error"]
            result_entry["raw_ground_truth"] = gt_json_obj.get("raw", "")
        
        output_path = os.path.join(results_folder, standardized_filename)
        save_json_file(output_path, result_entry)
        
        output_list.append(result_entry)
    
    return output_list