"""Authentication and authorization dependencies for FastAPI."""

from fastapi import Depends, HTTPException, Request, status

# In production, this would validate a real JWT token from a proper auth provider.
# For now, we check for a simple Bearer token in the Authorization header.


async def get_current_user(request: Request) -> dict[str, str]:
    """Extract and validate the current user from the Authorization header.

    Expects: Authorization: Bearer <token>
    In production, this verifies JWTs against Keycloak or similar.
    For development, any non-empty Bearer token is accepted.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In production: decode and validate JWT here
    # For now, parse a simple format: "user_id:role" or just accept any token
    parts = token.split(":")
    user = {
        "sub": parts[0] if len(parts) > 0 else token,
        "role": parts[1] if len(parts) > 1 else "user",
    }
    return user


async def require_admin(user: dict[str, str] = Depends(get_current_user)) -> dict[str, str]:
    """Ensure the current user has admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
