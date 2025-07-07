from flask import Blueprint, request, jsonify, current_app
from app.core.file_processor import process_uploaded_csv
from app.core.comparison_service import compare_files, compare_all_files

api_bp = Blueprint('api', __name__)

@api_bp.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'csv' not in request.files:
        return jsonify({"error": "No CSV file uploaded"}), 400

    csv_file = request.files['csv']
    if not csv_file.filename.lower().endswith('.csv'):
        return jsonify({"error": "Invalid file type. Please upload a CSV file"}), 400

    try:
        output_list = process_uploaded_csv(
            csv_file,
            current_app.config['UPLOAD_FOLDER'],
            current_app.config['CSV_RESULTS_FOLDER']
        )
        
        return jsonify({
            "status": "success",
            "processed": len(output_list),
            "results": output_list
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@api_bp.route('/compare', methods=['GET'])
def compare():
    csv_file = request.args.get('csv_file')
    ocr_file = request.args.get('ocr_file')
    
    if not csv_file or not ocr_file:
        return jsonify({"error": "Both csv_file and ocr_file parameters are required"}), 400
    
    try:
        result = compare_files(
            csv_file,
            ocr_file,
            current_app.config['CSV_RESULTS_FOLDER'],
            current_app.config['OCR_RESULTS_FOLDER']
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@api_bp.route('/compare_all', methods=['GET'])
def compare_all():
    try:
        results = compare_all_files(
            current_app.config['CSV_RESULTS_FOLDER'],
            current_app.config['OCR_RESULTS_FOLDER']
        )
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500