from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.core.gemini_service import get_model, RECEIPT_PROMPT
from app.utils.file_handling import save_ocr_result
from app.utils.json_utils import extract_json_from_response
from app.core.comparison_service import compare_files
import os
import json
import pandas as pd
from difflib import SequenceMatcher

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template("index.html")

@main_bp.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    image_file = request.files['image']
    image_bytes = image_file.read()
    
    try:
        model = get_model()
        response = model.generate_content(
            [
                {"text": RECEIPT_PROMPT},
                {"mime_type": image_file.mimetype, "data": image_bytes}
            ],
            generation_config={"temperature": 0.2}
        )
        
        parsed = extract_json_from_response(response.text)
        saved_path = save_ocr_result(
            image_file.filename, 
            parsed,
            current_app.config['OCR_RESULTS_FOLDER']
        )
        
        return render_template(
            "result.html",
            image_name=image_file.filename,
            result_json=json.dumps(parsed, indent=2, ensure_ascii=False),
            saved_path=saved_path
        )
    except Exception as e:
        return render_template("result.html", image_name="Error", result_json=json.dumps({"error": str(e)}))

@main_bp.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'csv' not in request.files:
        return jsonify({"error": "No CSV file uploaded"}), 400

    csv_file = request.files['csv']
    if not csv_file.filename.lower().endswith('.csv'):
        return jsonify({"error": "Invalid file type. Please upload a CSV file"}), 400

    try:
        csv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(csv_file.filename))
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
            return jsonify({"error": f"CSV parsing failed: {str(e)}"}), 400

        required_columns = {'ground_truth'}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            return jsonify({
                "error": f"Missing required columns: {', '.join(missing)}",
                "available_columns": list(df.columns)
            }), 400

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

            output_path = os.path.join(current_app.config['CSV_RESULTS_FOLDER'], standardized_filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result_entry, f, indent=2, ensure_ascii=False)
            
            output_list.append(result_entry)

        complete_results_path = os.path.join(current_app.config['CSV_RESULTS_FOLDER'], f"{secure_filename(csv_file.filename)}_results.json")
        with open(complete_results_path, 'w', encoding='utf-8') as f:
            json.dump(output_list, f, indent=2, ensure_ascii=False)

        return render_template('csv_result.html', 
                            results=output_list,
                            saved_path=complete_results_path)

    except pd.errors.EmptyDataError:
        return jsonify({"error": "The CSV file is empty"}), 400
    except Exception as e:
        return jsonify({"error": f"CSV processing failed: {str(e)}"}), 500

@main_bp.route('/compare_files', methods=['GET', 'POST'])
def compare_files_route():
    if request.method == 'POST':
        csv_file = request.form.get('csv_file')
        ocr_file = request.form.get('ocr_file')
    else:
        csv_file = request.args.get('csv_file')
        ocr_file = request.args.get('ocr_file')
    
    if not csv_file or not ocr_file:
        return jsonify({"error": "Both csv_file and ocr_file parameters are required"}), 400
    
    csv_path = os.path.join(current_app.config['CSV_RESULTS_FOLDER'], csv_file) if not csv_file.startswith('csv_results/') else csv_file
    ocr_path = os.path.join(current_app.config['OCR_RESULTS_FOLDER'], ocr_file) if not ocr_file.startswith('ocr_results/') else ocr_file

    if not os.path.exists(csv_path):
        return jsonify({"error": f"CSV file not found: {csv_path}"}), 404
    if not os.path.exists(ocr_path):
        return jsonify({"error": f"OCR file not found: {ocr_path}"}), 404

    with open(csv_path, 'r', encoding='utf-8') as f1:
        csv_data = flatten_json(json.load(f1).get('gt_parse', {}))
    with open(ocr_path, "r", encoding="utf-8") as f2:
        ocr_data = flatten_json(json.load(f2))

    match_result = {}
    unmatched = {}
    total_fields = len(csv_data)
    matched_fields = 0

    for k1, v1 in csv_data.items():
        best_match = None
        highest_score = 0.0
        for k2, v2 in ocr_data.items():
            score = similarity(v1, v2)
            if score > highest_score:
                highest_score = score
                best_match = (k2, v2)
        if highest_score >= 0.80:
            matched_fields += 1
            match_result[k1] = {
                "csv_value": v1,
                "ocr_value": best_match[1],
                "similarity": round(highest_score, 2)
            }
        else:
            unmatched[k1] = {
                "csv_value": v1,
                "ocr_guess": best_match[1] if best_match else None,
                "similarity": round(highest_score, 2)
            }

    accuracy = round((matched_fields / total_fields) * 100, 2) if total_fields > 0 else 0.0

    return render_template(
        'comparison_result.html',
        csv_filename=os.path.basename(csv_path),
        ocr_filename=os.path.basename(ocr_path),
        matched=match_result,
        unmatched=unmatched,
        accuracy_percent=accuracy
    )

@main_bp.route('/compare_files_page')
def compare_files_page():
    csv_files = [f for f in os.listdir(current_app.config['CSV_RESULTS_FOLDER']) if f.endswith('.json')]
    ocr_files = [f for f in os.listdir(current_app.config['OCR_RESULTS_FOLDER']) if f.endswith('.json')]
    
    return render_template(
        'compare_files.html',
        csv_files=csv_files,
        ocr_files=ocr_files
    )

@main_bp.route('/compare_all', methods=['GET'])
def compare_all_jsons():
    results = []
    total_accuracy = 0.0
    total_files = 0

    for filename in os.listdir(current_app.config['CSV_RESULTS_FOLDER']):
        if filename.endswith('.json'):
            csv_path = os.path.join(current_app.config['CSV_RESULTS_FOLDER'], filename)
            ocr_path = os.path.join(current_app.config['OCR_RESULTS_FOLDER'], filename)

            if not os.path.exists(ocr_path):
                results.append({
                    "file": filename,
                    "error": "OCR file not found"
                })
                continue

            with open(csv_path, 'r', encoding='utf-8') as f1:
                csv_data = flatten_json(json.load(f1).get('gt_parse', {}))
            with open(ocr_path, 'r', encoding='utf-8') as f2:
                ocr_data = flatten_json(json.load(f2))

            total_fields = len(csv_data)
            matched_fields = 0

            for k1, v1 in csv_data.items():
                best_match_score = 0.0
                for v2 in ocr_data.values():
                    score = similarity(v1, v2)
                    best_match_score = max(best_match_score, score)

                if best_match_score >= 0.80:
                    matched_fields += 1

            accuracy = round((matched_fields / total_fields) * 100, 2) if total_fields > 0 else 0.0
            total_accuracy += accuracy
            total_files += 1

            results.append({
                "file": filename,
                "matched_fields": matched_fields,
                "total_fields": total_fields,
                "accuracy_percent": accuracy
            })

    overall_accuracy = round((total_accuracy / total_files), 2) if total_files > 0 else 0.0

    return jsonify({
        "total_files": total_files,
        "overall_accuracy_percent": overall_accuracy,
        "file_results": results
    })

# Helper functions
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