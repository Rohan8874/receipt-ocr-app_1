import os
import json
from app.utils.json_utils import flatten_json, similarity

def compare_files(csv_filename, ocr_filename, csv_folder, ocr_folder):
    csv_path = os.path.join(csv_folder, csv_filename)
    ocr_path = os.path.join(ocr_folder, ocr_filename)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    if not os.path.exists(ocr_path):
        raise FileNotFoundError(f"OCR file not found: {ocr_path}")

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

    return {
        "csv_filename": os.path.basename(csv_path),
        "ocr_filename": os.path.basename(ocr_path),
        "matched": match_result,
        "unmatched": unmatched,
        "accuracy_percent": accuracy
    }

def compare_all_files(csv_folder, ocr_folder):
    results = []
    total_accuracy = 0.0
    total_files = 0

    for filename in os.listdir(csv_folder):
        if filename.endswith('.json'):
            csv_path = os.path.join(csv_folder, filename)
            ocr_path = os.path.join(ocr_folder, filename)

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

    return {
        "total_files": total_files,
        "overall_accuracy_percent": overall_accuracy,
        "file_results": results
    }