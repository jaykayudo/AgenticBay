from fastapi import APIRouter

from app.api.routes.auth import auto_pay, email, oauth, tokens

router = APIRouter()
router.include_router(tokens.router)
router.include_router(oauth.router)
router.include_router(email.router)
router.include_router(auto_pay.router)

__all__ = ["router"]
