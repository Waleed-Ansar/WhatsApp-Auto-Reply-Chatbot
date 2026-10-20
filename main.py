import os
import uvicorn
from api_routes import app


# Docker Use
# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 8000))

#     uvicorn.run(
#         app,
#         host="0.0.0.0",
#         port=port
#     )

# Local Use
if __name__ == "__main__":
    uvicorn.run(
        "api_routes:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    )