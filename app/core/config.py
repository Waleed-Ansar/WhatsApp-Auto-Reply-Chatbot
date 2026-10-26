import os
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig


load_dotenv()

class Config:
    # API Configuration
    OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
    OPENAI_API_MODEL=os.getenv("OPENAI_API_MODEL")

    # External API Configuration
    API_BASE_URL = "https://rtdhub.azurewebsites.net"
    # API_BASE_URL = "https://devrtdhub.azurewebsites.net"
    
    MSSQL_DATABASE_PASSWORD = os.getenv("MSSQL_DATABASE_PASSWORD" ,"")
    MSSQL_DATABASE_USERNAME = os.getenv("MSSQL_DATABASE_USERNAME" ,"")
    
    # Appointment Configuration
    DEFAULT_APPOINTMENT_DURATION_MINUTES = 30
    SLOT_TOLERANCE_SECONDS = 300  # 5 minutes

    # JWT settings
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    CLIENT_ID = os.getenv("CLIENT_ID")
    AUTH_URL = os.getenv("AUTH_URL")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = 60

    DB_NAME = "otp_verification.db"
    OTP_EXPIRY_SECONDS = 60

    email_conf = ConnectionConfig(
        MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
        MAIL_FROM=os.getenv("MAIL_FROM", ""),
        MAIL_PORT=587,
        MAIL_SERVER=os.getenv("MAIL_SERVER", ""),
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True
    )
    
    @classmethod
    def validate_config(cls):
        """Validate that all required environment variables are set"""
        if not cls.OPENAI_API_KEY:
            raise EnvironmentError("OPENAI_API_KEY is not set in environment.")
        if not cls.OPENAI_API_MODEL:
            raise EnvironmentError("OPENAI_API_MODEL is not set in environment.")
        return True

# Initialize and validate configuration
config = Config()
config.validate_config()