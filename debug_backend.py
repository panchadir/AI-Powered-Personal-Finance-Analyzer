import uvicorn
from dotenv import load_dotenv

# Load database and anthropic API keys
load_dotenv()

if __name__ == "__main__":
    # Start the backend server directly without auto-reload or sub-processes.
    # This prevents the PyCharm debugger from crashing on Windows path space resolution.
    uvicorn.run(
        app="finance_app.finance_app:app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
