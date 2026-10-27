from langchain_openai import ChatOpenAI
import warnings

from app.core.config import config


warnings.filterwarnings("ignore")

def initialize_llm(is_premium: bool = False):
    if is_premium == True:
        return ChatOpenAI(
            model=config.OPENAI_API_MODEL_PREMIUM,
            api_key=config.OPENAI_API_KEY,
            max_retries=10,
            timeout=60,
            request_timeout=60
        )

    else:
        return ChatOpenAI(
            model=config.OPENAI_API_MODEL_STANDARD,
            api_key=config.OPENAI_API_KEY,
            max_retries=10,
            timeout=60,
            request_timeout=60
        )