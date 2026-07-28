import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is missing")

database_url = DATABASE_URL

# Neon connection strings often start with postgres://.
# SQLAlchemy async requires it to strictly start with postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    database_url = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    database_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# 1. Create the async engine
engine = create_async_engine(
    database_url,
    echo=False,  # Set to True if you want to see raw SQL logs in your terminal
    pool_pre_ping=True,  # Automatically checks and revives dead database connections
)

# 2. Create the session maker
# Create a Session Factory (Generates unique database sessions)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# 3. Base class that our models will inherit from
Base = declarative_base()


# Dependency provider to inject database sessions into routes cleanly
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
