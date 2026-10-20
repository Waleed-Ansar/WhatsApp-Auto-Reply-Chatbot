# RTD Property LLM RAG API - Modular Version

This is a modular version of the RTD Property LLM RAG API that provides real estate project information and appointment booking functionality using Large Language Models and Retrieval-Augmented Generation (RAG).

## Project Structure

```
rtd_llm_modular_project/
├── main.py                 # Main application entry point
├── config.py              # Configuration and environment variables
├── models.py              # Pydantic models for API requests/responses
├── llm_setup.py           # LLM and embedding model initialization
├── token_manager.py       # Get auth token logic
├── datetime_utils.py      # Date/time parsing utilities
├── memory_service.py      # Memory management for conversations
├── session.py             # Session management for users
├── mcp_services.py        # Contains the executable functions
├── mcp_server.py          # Run the MCP Server
├── mcp_client.py          # Initialize and run the MCP Client
├── tools.py               # Tools used by LLM
├── chat_system.py         # Core LLM functionality
├── api_routes.py          # FastAPI routes and endpoints
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Module Descriptions

### `main.py`
The main entry point that runs the FastAPI application using uvicorn.

### `config.py`
Contains all configuration settings including:
- API keys and endpoints
- Vector database settings
- Embedding model configuration
- Default values for appointments

### `models.py`
Pydantic models for API data validation:
- `SourceDocument`: For document metadata
- `AnswerResponse`: For API responses
- `AskRequest`: For incoming chat requests

### `llm_setup.py`
Initializes and configures:
- HuggingFace embedding models
- Chroma vector database
- ChatOpenAI LLM instances

### `intent_classifier.py`
Handles intent classification for user queries:
- Booking appointments
- Checking availability
- Project queries
- Greetings and farewells

### `datetime_utils.py`
Utilities for date/time processing:
- Natural language date extraction
- DateTime formatting
- Time validation

### `memory_service.py`
Manages conversation memory:
- User chat history
- Slot suggestions storage
- Memory cleanup

### `appointment_service.py`
Handles all appointment-related operations:
- Booking appointments
- Checking availability
- Managing suggested slots
- API communication with calendar service

### `rag_service.py`
Retrieval-Augmented Generation functionality:
- Vector database queries
- Context-aware responses
- Real estate project information

### `api_routes.py`
FastAPI routes and endpoint definitions:
- `/ask` - Main chat endpoint
- `/memory/{chat_id}` - Memory management
- `/health` - Health check
- Other utility endpoints

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in a `.env` file:
```env
DEEP_SEEK_API=your_api_key
DEEP_SEEK_MODEL=your_model_name
DEEP_SEEK_URI=your_api_endpoint
```

3. Ensure you have the vector database data in `data/rtd_project_vectordb/`

## Running the Application

### Method 1: Using main.py
```bash
python main.py
```

### Method 2: Using uvicorn directly
```bash
uvicorn api_routes:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: Using Docker

#### Build and run with Docker
```bash
# Build the Docker image
docker build -t rtd-llm-api .

# Run the container
docker run -d \
  --name rtd-llm-api \
  -p 8000:8000 \
  -e DEEP_SEEK_API=your_api_key \
  -e DEEP_SEEK_MODEL=your_model \
  -e DEEP_SEEK_URI=your_uri \
  -v $(pwd)/data:/app/data \
  rtd-llm-api
```

#### Using Docker Compose (Recommended)
```bash
# Create .env file with your API keys
cp .env.example .env
# Edit .env with your actual values

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## Features

- **Intent Classification**: Automatically classifies user intents (booking, queries, greetings, etc.)
- **Appointment Booking**: Full appointment management with calendar integration
- **RAG-based Responses**: Context-aware responses about real estate projects
- **Memory Management**: Maintains conversation history per user
- **Natural Language Processing**: Understands natural language date/time expressions
- **Modular Architecture**: Clean separation of concerns for easy maintenance

## Environment Variables

Required environment variables:
- `DEEP_SEEK_API`: API key for the LLM service
- `DEEP_SEEK_MODEL`: Model name to use
- `DEEP_SEEK_URI`: API endpoint URI

## Docker Support

The application includes full Docker support with:

### Files
- `Dockerfile`: Multi-stage build with security best practices
- `.dockerignore`: Optimized for smaller image sizes
- `docker-compose.yml`: Complete orchestration setup

### Features
- **Security**: Non-root user execution
- **Health Checks**: Built-in health monitoring
- **Volume Mounts**: Persistent data storage
- **Environment Variables**: Secure configuration
- **Optimized Build**: Layered caching for faster builds

### Docker Commands
```bash
# Build image
docker build -t rtd-llm-api .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f rtd-llm-api

# Scale service
docker-compose up -d --scale rtd-llm-api=3

# Stop services
docker-compose down
```

## Dependencies

Key dependencies include:
- FastAPI for the web framework
- LangChain for LLM operations
- ChromaDB for vector storage
- Sentence Transformers for embeddings
- DateParser for natural language date parsing
- HTTPX for async HTTP requests