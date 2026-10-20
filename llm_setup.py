from langchain_openai import ChatOpenAI
from config import config
import warnings

warnings.filterwarnings("ignore")

def initialize_llm():
    return ChatOpenAI(
        model=config.DEEP_SEEK_MODEL,
        api_key=config.DEEP_SEEK_API,
        base_url=config.DEEP_SEEK_URI,
        temperature=0
    )

llm = initialize_llm()