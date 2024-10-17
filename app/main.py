# main.py

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.apis import main_router  # Ensure this path is correct based on your project structure
from app.database import database  # Adjust the import based on your project structure
from app.apis.main_router import sanitize_error_message  # Import the sanitize function

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the FastAPI app
app = FastAPI(
    title="Map Action API",
    description="API for Map Action classification and chat functionalities.",
    version="1.0.0",
)

# CORS middleware configuration
# Adjust `allow_origins` to specify the exact origins allowed in production for better security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific origins like ["https://yourdomain.com"] in production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods; restrict if necessary
    allow_headers=["*"],  # Allow all headers; restrict if necessary
)

# Custom exception handler to sanitize error messages
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles HTTPExceptions by sanitizing error messages to avoid leaking sensitive information.

    Args:
        request (Request): The incoming request.
        exc (HTTPException): The exception instance.

    Returns:
        JSONResponse: A JSON response with the sanitized error detail.
    """
    # Retrieve sensitive structures from request state if available
    sensitive_structures = getattr(request.state, 'sensitive_structures', [])
    sanitized_detail = sanitize_error_message(str(exc.detail), sensitive_structures)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": sanitized_detail},
    )

# Middleware to log all incoming requests and outgoing responses
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Logs each incoming request and its corresponding response.

    Args:
        request (Request): The incoming HTTP request.
        call_next (Callable): The next middleware or endpoint handler.

    Returns:
        Response: The HTTP response generated by the endpoint.
    """
    logger.info(f"Received request: {request.method} {request.url}")
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise e
    logger.info(f"Finished processing: {request.method} {request.url} - Status: {response.status_code}")
    return response

# Event handler for application startup
@app.on_event("startup")
async def startup():
    """
    Handles tasks to be performed on application startup, such as connecting to the database.
    """
    logger.info("Starting up the Map Action API...")
    try:
        await database.connect()
        logger.info("Connected to the database successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to the database: {e}")
        raise e

# Event handler for application shutdown
@app.on_event("shutdown")
async def shutdown():
    """
    Handles tasks to be performed on application shutdown, such as disconnecting from the database.
    """
    logger.info("Shutting down the Map Action API...")
    try:
        await database.disconnect()
        logger.info("Disconnected from the database successfully.")
    except Exception as e:
        logger.error(f"Failed to disconnect from the database: {e}")
        raise e

# Include the main_router without a prefix to keep routes as defined in main_router.py
app.include_router(main_router.router, prefix="/api1")

# Root endpoint to verify API is running
@app.get("/")
async def root():
    """
    Root endpoint that returns a welcome message.

    Returns:
        dict: A simple welcome message.
    """
    return {"message": "Welcome to the Map Action API"}

# Health check endpoint to verify application health
@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify that the API is operational.

    Returns:
        dict: A status message indicating health.
    """
    return {"status": "healthy"}

# If running this file directly, start the Uvicorn server
if __name__ == "__main__":
    import uvicorn

    # Configure Uvicorn settings as needed
    uvicorn.run(
        "main:app",  # Module and app instance
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,       # Port number
        reload=True,
        ws="websockets",     # Enable auto-reload for development
        log_level="info",# Set log level
    )