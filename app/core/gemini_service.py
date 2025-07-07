import google.generativeai as genai

def init_gemini(app):
    genai.configure(api_key=app.config['GEMINI_API_KEY'])

def get_model():
    return genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")

RECEIPT_PROMPT = """
You are an intelligent receipt OCR extractor. Analyze the uploaded cash memo image and return structured data in valid raw JSON format only (no explanations, no markdown formatting, no code block, no text outside JSON).

The JSON structure must include:
{
    "menu": [
        {
            "nm": "Item name",
            "unitprice": "string with commas",
            "cnt": "string with x",
            "price": "item total price as string",
            "sub": {"nm": "Optional sub-item description, e.g., 'WELL DONE'"} (optional)
        }
    ],
    "sub_total": {
        "subtotal_price": "string with commas",
        "discount_price": "string with commas",
        "service_price": "string with commas",
        "tax_price": "string with commas",
        "etc": "string with commas"
    },
    "total": {
        "total_price": "string with commas",
        "cashprice": "string with commas",
        "changeprice": "string with commas",
        "employeeprice": "string with commas",
        "manutype_cnt": "string with commas",
        "manuqty_cnt": "string with commas"
    }
}

Important instructions:
- Do NOT include any key or field with a null, empty, or zero value in the output.
- Sub-items like "WELL DONE" or "MEDIUM WELL" must appear inside a "sub" object if present.
- Output only valid raw JSON — do NOT add markdown, code block, comments, or explanations.
"""