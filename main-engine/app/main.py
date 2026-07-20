import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global variables to hold our database pool and checkpointer
db_pool = None
checkpointer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager: Handles startup and shutdown events.
    This ensures we only create the database pool once.
    """
    global db_pool, checkpointer

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in the .env file.")

    # 1. Initialize the Connection Pool
    # autocommit=True and row_factory=dict_row are strictly required by LangGraph's PostgresSaver
    db_pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        min_size=2,  # Keep 2 connections warm
        max_size=20,  # Scale up to 20 under burst load
        kwargs={"autocommit": True, "row_factory": dict_row},
    )

    # 2. Attach the pool to the LangGraph Checkpointer
    checkpointer = AsyncPostgresSaver(db_pool)

    # 3. Create the necessary checkpoint tables if they don't exist
    # This is idempotent, meaning it's safe to run every time the server starts
    await checkpointer.setup()

    print("✅ Database pool and LangGraph checkpointer initialized.")

    yield  # The FastAPI server runs while yielding here

    # 4. Graceful shutdown
    await db_pool.close()
    print("🛑 Database pool closed.")


# Initialize FastAPI with the lifespan manager
app = FastAPI(title="AI Codebase Analyzer API", version="1.0.0", lifespan=lifespan)

# Configure CORS so your Next.js frontend can talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Simple endpoint to verify the server and database are running."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database pool not initialized")
    return {"status": "active", "service": "Agentic Backend"}


# --- Placeholder for your future LangGraph Endpoint ---
@app.post("/api/analyze")
async def analyze_repo(repo_url: str, thread_id: str):
    """
    Later, you will import your compiled LangGraph here, pass the `checkpointer`,
    and stream the results back using the `thread_id`.
    """
    return {"message": f"Ready to analyze {repo_url} using thread {thread_id}"}


if __name__ == "__main__":
    import uvicorn

    # Run the server with hot-reloading for local development
    print("\n🚀 FastAPI Server")
    print("📖 Swagger UI : http://127.0.0.1:8000/docs")
    print("📚 ReDoc      : http://127.0.0.1:8000/redoc")
    print("🔍 OpenAPI    : http://127.0.0.1:8000/openapi.json\n")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
