import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Configuration
    DEEP_SEEK_API = os.getenv("DEEP_SEEK_API")
    DEEP_SEEK_MODEL = os.getenv("DEEP_SEEK_MODEL")
    DEEP_SEEK_URI = os.getenv("DEEP_SEEK_URI")
    
    # Vector Database Configuration
    VECTORDB_PERSIST_DIR = "data/rtd_project_vectordb"
    VECTORDB_COLLECTION_NAME = "rtd_projects"
    
    # External API Configuration
    API_BASE_URL = "https://rtdhub.azurewebsites.net"
    
    # Appointment Configuration
    DEFAULT_APPOINTMENT_DURATION_MINUTES = 30
    SLOT_TOLERANCE_SECONDS = 300  # 5 minutes

    # JWT settings
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    CLIENT_ID = os.getenv("CLIENT_ID")
    AUTH_URL = os.getenv("AUTH_URL")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = 60
    
    @classmethod
    def validate_config(cls):
        """Validate that all required environment variables are set"""
        if not cls.DEEP_SEEK_API:
            raise EnvironmentError("DEEP_SEEK_API is not set in environment.")
        if not cls.DEEP_SEEK_MODEL:
            raise EnvironmentError("DEEP_SEEK_MODEL is not set in environment.")
        return True

# Initialize and validate configuration
config = Config()
config.validate_config()