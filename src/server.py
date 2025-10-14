import os
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from dotenv import load_dotenv
import uvicorn

from src.line_bot import router as line_router
from src.restaurant_finder import router as restaurant_router
from src.broadcast_router import router as broadcast_router

# Load environment variables
load_dotenv()

# Define host and port
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "8000")

# Create FastAPI application
app = FastAPI(
    title="GeoDine-AI Multi-Bot Platform",
    description="Multi-bot LINE platform for restaurant finding and weather outfit recommendations"
)

# Register routers
app.include_router(line_router)
app.include_router(restaurant_router)
app.include_router(broadcast_router)

# Create MCP server
mcp = FastApiMCP(
    app,
    name="Restaurant Finder MCP",
    description="MCP server for restaurant finding with LINE integration"
)

# Mount MCP server
mcp.mount()

if __name__ == "__main__":
    uvicorn.run(
        "src.server:app",
        host=host,
        port=int(port),
        reload=True
    )
