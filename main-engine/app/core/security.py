import os
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

# HTTPBearer tells FastAPI to look for an "Authorization: Bearer <token>" header
security = HTTPBearer()

CLERK_FRONTEND_API = os.getenv("CLERK_FRONTEND_API")
if not CLERK_FRONTEND_API:
    raise ValueError("CLERK_FRONTEND_API environment variable is missing")

# Clerk publishes its public keys at this specific URL
jwks_url = f"{CLERK_FRONTEND_API}"
jwk_client = PyJWKClient(jwks_url)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """
    Dependency that intercepts the request, grabs the token,
    verifies it against Clerk's public keys, and returns the User ID.
    """

    token = credentials.credentials

    try:
        # 1. Fetch the public key that matches the token's signature
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        # 2. Decode and verify the token
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            # In a strict production environment you would verify the audience,
            # but for our decoupled setup, disabling it is standard.
            options={"verify_aud": False},
        )

        # 3. Extract the 'sub' (Subject), which is the Clerk User ID (e.g., user_2t...)
        user_id = data.get("sub")
        if not user_id:
            raise ValueError("Token is missing the subject claim")

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
        )
