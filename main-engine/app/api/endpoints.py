from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Import the two functions you just wrote
from app.db.database import get_db
from app.core.security import get_current_user

router = APIRouter()


@router.get("/my-profile")
async def get_profile(
    # 1. FastAPI automatically verifies the JWT and gives you the user_id
    user_id: str = Depends(get_current_user),
    # 2. FastAPI automatically opens a DB session and closes it when done
    db: AsyncSession = Depends(get_db),
):
    # Now you can safely query the database knowing the user is authenticated!
    return {"message": f"Hello {user_id}", "status": "success"}
