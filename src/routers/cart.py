from fastapi import APIRouter

router = APIRouter(tags=["Cart"])


@router.post("/cart/")