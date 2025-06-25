import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-development'
    
    # Groq Configuration
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama3-8b-8192')
    AZURE_CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
    AZURE_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')
    AZURE_TENANT_ID = os.environ.get('AZURE_TENANT_ID')
    AZURE_DISCOVERY_URL = os.environ.get('AZURE_DISCOVERY_URL')
    AZURE_REDIRECT_URI = os.environ.get('AZURE_REDIRECT_URI')
    PREFERRED_URL_SCHEME = 'https'
    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="postgresql+psycopg2",
        username="postgres",
        password="1qaz@WSX",   # ← no manual encoding
        host="localhost",
        port=5432,
        database="ASID"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False