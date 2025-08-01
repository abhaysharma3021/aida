from flask import Flask
from config import Config
import markdown
import json
import re
import logging
import os                                      
from markupsafe import Markup
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from logging.handlers import RotatingFileHandler                                                                                                

oauth = OAuth()
db = SQLAlchemy()

def setup_logger(app: Flask) -> None:
    """Configure logging for Flask application."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(app.instance_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Set up logger
    logger = logging.getLogger('my_flask_app')
    logger.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # Remove any existing handlers to prevent duplicate logs
    logger.handlers.clear()

    # Create formatter
    log_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] [%(module)s:%(lineno)d] - %(message)s'
    )

    # Console handler for development
    if app.debug:
    # Console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

        # Also log to file
        log_file = os.path.join(log_dir, 'app_debug.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

    else:
        # File handler for production with rotation
        log_file = os.path.join(log_dir, 'app.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5  # Keep 5 backup files
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

        # Error log file for critical errors
        error_log_file = os.path.join(log_dir, 'error.log')
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(log_format)
        logger.addHandler(error_handler)

    # Replace Flask's default logger
    app.logger.handlers = logger.handlers
    app.logger.setLevel(logger.level)
    app.logger.propagate = False
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    oauth.init_app(app)
    setup_logger(app)                                  

     # Register Azure AD provider
    oauth.register(
        name="azure",
        client_id=app.config["AZURE_CLIENT_ID"],
        client_secret=app.config["AZURE_CLIENT_SECRET"],
        server_metadata_url=app.config["AZURE_DISCOVERY_URL"],
        client_kwargs={"scope": "openid profile email"}
    )  
    
    # Register the existing nl2br filter
    @app.template_filter('nl2br')
    def nl2br(value):
        if value:
            return value.replace('\n', '<br>')
        return value
    
    # Register new template filters for material formatting
    @app.template_filter('markdown')
    def markdown_filter(text):
        """Convert markdown text to HTML"""
        if not text:
            return ""
        
        # Convert markdown to HTML
        html = markdown.markdown(
            str(text), 
            extensions=['extra', 'codehilite', 'toc'],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight'
                }
            }
        )
        return Markup(html)
    
    @app.template_filter('format_time_allocation')
    def format_time_allocation(time_data):
        """Format time allocation data nicely"""
        if not time_data:
            return ""
        
        if isinstance(time_data, str):
            return markdown_filter(time_data)
        
        if isinstance(time_data, dict):
            html = "<div class='time-allocation'>"
            for key, value in time_data.items():
                html += f"<div class='time-item'>"
                html += f"<strong>{key.replace('_', ' ').title()}:</strong> "
                html += f"<span class='time-value'>{value}</span>"
                html += f"</div>"
            html += "</div>"
            return Markup(html)
        
        return str(time_data)
    
    @app.template_filter('format_assessments')
    def format_assessments(assessment_data):
        """Format assessment data nicely"""
        if not assessment_data:
            return ""
        
        if isinstance(assessment_data, str):
            return markdown_filter(assessment_data)
        
        if isinstance(assessment_data, dict):
            html = "<div class='assessment-content'>"
            
            for key, value in assessment_data.items():
                if value:  # Only show non-empty values
                    html += f"<div class='assessment-item'>"
                    html += f"<h5 class='assessment-title'>"
                    html += f"<i class='fas fa-check-circle text-success'></i> "
                    html += f"{key.replace('_', ' ').title()}"
                    html += f"</h5>"
                    
                    if isinstance(value, str):
                        html += f"<div class='assessment-description'>{markdown_filter(value)}</div>"
                    elif isinstance(value, list):
                        html += "<ul class='assessment-list'>"
                        for item in value:
                            html += f"<li>{item}</li>"
                        html += "</ul>"
                    elif isinstance(value, dict):
                        html += "<div class='assessment-details'>"
                        for sub_key, sub_value in value.items():
                            html += f"<div class='detail-item'>"
                            html += f"<strong>{sub_key.replace('_', ' ').title()}:</strong> "
                            html += f"{sub_value}"
                            html += f"</div>"
                        html += "</div>"
                    
                    html += "</div>"
            
            html += "</div>"
            return Markup(html)
        
        return str(assessment_data)
    
    @app.template_filter('format_structured_data')
    def format_structured_data(data):
        """Format structured data in a readable way"""
        if not data:
            return ""
        
        def get_icon_for_key(key):
            """Get appropriate icon for data key"""
            icon_map = {
                'content': 'book',
                'objectives': 'bullseye',
                'activities': 'users',
                'assessment': 'tasks',
                'instructions': 'list',
                'materials': 'tools',
                'time': 'clock',
                'duration': 'clock',
                'examples': 'lightbulb',
                'resources': 'link',
                'tips': 'info-circle',
                'requirements': 'exclamation-circle',
                'overview': 'eye',
                'summary': 'list-alt',
                'preparation': 'clipboard-check',
                'facilitation': 'chalkboard-teacher',
                'troubleshooting': 'wrench'
            }
            
            for keyword, icon in icon_map.items():
                if keyword in key.lower():
                    return icon
            
            return 'circle'
        
        def format_value(value, level=0):
            if isinstance(value, dict):
                html = ""
                for key, val in value.items():
                    if key == 'metadata':  # Skip metadata for cleaner display
                        continue
                    
                    html += f"<div class='data-item level-{level}'>"
                    html += f"<div class='data-key'>"
                    html += f"<i class='fas fa-{get_icon_for_key(key)}'></i> "
                    html += f"<strong>{key.replace('_', ' ').title()}:</strong>"
                    html += f"</div>"
                    html += f"<div class='data-value'>{format_value(val, level + 1)}</div>"
                    html += f"</div>"
                return html
            
            elif isinstance(value, list):
                if not value:
                    return "<em>No items</em>"
                
                html = "<ul class='data-list'>"
                for item in value:
                    html += f"<li>{format_value(item, level + 1)}</li>"
                html += "</ul>"
                return html
            
            else:
                # Handle string values - convert markdown if it looks like markdown
                str_val = str(value)
                if len(str_val) > 100 or '\n' in str_val:
                    return f"<div class='formatted-text'>{markdown_filter(str_val)}</div>"
                else:
                    return f"<span class='simple-value'>{str_val}</span>"
        
        html = "<div class='structured-display'>"
        html += format_value(data)
        html += "</div>"
        
        return Markup(html)
    
    # Import and register blueprints
    from app.routes import main
    from app.auth import auth_bp
    app.register_blueprint(main)
    app.register_blueprint(auth_bp)
    
    return app