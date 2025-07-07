import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    UPLOAD_FOLDER = 'uploads'
    OCR_RESULTS_FOLDER = 'ocr_results'
    CSV_RESULTS_FOLDER = 'csv_results'
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = "gemini-2.5-flash-lite-preview-06-17"
    
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['OCR_RESULTS_FOLDER'], exist_ok=True)
        os.makedirs(app.config['CSV_RESULTS_FOLDER'], exist_ok=True)