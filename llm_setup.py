from langchain_community.chat_models import ChatOpenAI
from langchain_community.vectorstores import Chroma
from config import config
import warnings

warnings.filterwarnings("ignore")

def initialize_vectordb(embedding_model):
    """Initialize the Chroma vector database"""
    return Chroma(
        persist_directory=config.VECTORDB_PERSIST_DIR,
        embedding_function=embedding_model,
        collection_name=config.VECTORDB_COLLECTION_NAME
    )

def initialize_llm():
    return ChatOpenAI(
        model=config.DEEP_SEEK_MODEL,
        api_key=config.DEEP_SEEK_API,
        base_url=config.DEEP_SEEK_URI,
        temperature=0
    )

llm = initialize_llm()