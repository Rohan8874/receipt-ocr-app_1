from flask import Flask
from app.config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # Initialize extensions
    from app.core.gemini_service import init_gemini
    init_gemini(app)
    
    # Register blueprints
    from app.routes.views import main_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app