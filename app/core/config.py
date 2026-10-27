import os
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig


load_dotenv()


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable, falling back on parse errors."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    """Read a float environment variable, falling back on parse errors."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


class Config:
    # API Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_MODEL_STANDARD = os.getenv("OPENAI_API_MODEL_STANDARD")
    OPENAI_API_MODEL_PREMIUM = os.getenv("OPENAI_API_MODEL_PREMIUM")

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

    # Two-tier conversation memory settings. ``CHAT_MEMORY_DB_PATH`` is the
    # SQLite file used for long-term memory and must be writable.
    CHAT_MEMORY_DB_PATH = os.getenv("CHAT_MEMORY_DB_PATH", "chat_memory.db")
    CHAT_MEMORY_SESSION_TTL_SECONDS = _env_int(
        "CHAT_MEMORY_SESSION_TTL_SECONDS", 3600
    )
    CHAT_MEMORY_LONG_TERM_TTL_DAYS = _env_int(
        "CHAT_MEMORY_LONG_TERM_TTL_DAYS", 7
    )
    CHAT_MEMORY_LONG_TERM_TTL_SECONDS = CHAT_MEMORY_LONG_TERM_TTL_DAYS * 24 * 60 * 60
    CHAT_MEMORY_WINDOW_SIZE = _env_int("CHAT_MEMORY_WINDOW_SIZE", 100)
    CHAT_MEMORY_TOP_K = _env_int("CHAT_MEMORY_TOP_K", 5)
    CHAT_MEMORY_EMBEDDING_MODEL = os.getenv(
        "CHAT_MEMORY_EMBEDDING_MODEL", "text-embedding-3-small"
    )
    CHAT_MEMORY_PRUNE_INTERVAL_SECONDS = _env_float(
        "CHAT_MEMORY_PRUNE_INTERVAL_SECONDS", 3600
    )

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
        if not cls.OPENAI_API_MODEL_STANDARD:
            raise EnvironmentError("OPENAI_API_MODEL_STANDARD is not set in environment.")
        if not cls.OPENAI_API_MODEL_PREMIUM:
            raise EnvironmentError("OPENAI_API_MODEL_PREMIUM is not set in environment.")
        return True

# Initialize and validate configuration
config = Config()
config.validate_config()
