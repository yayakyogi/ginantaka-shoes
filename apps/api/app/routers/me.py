from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.core.errors import error_responses
from app.schemas.auth import UserOut

router = APIRouter(tags=["auth"], responses=error_responses((401, "UNAUTHENTICATED")))


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    """AUTH-5: the logged-in user, any role."""
    return UserOut.model_validate(user, from_attributes=True)
