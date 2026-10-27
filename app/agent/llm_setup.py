from langchain_openai import ChatOpenAI
import warnings

from app.core.config import config


warnings.filterwarnings("ignore")

def initialize_llm():
    return ChatOpenAI(
        model=config.OPENAI_API_MODEL,
        api_key=config.OPENAI_API_KEY,
        max_retries=10,
        timeout=60,
        request_timeout=60
        )

llm = initialize_llm()