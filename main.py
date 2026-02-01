import uvicorn
from api_routes import app

if __name__ == "__main__":
    uvicorn.run(
        "api_routes:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    )