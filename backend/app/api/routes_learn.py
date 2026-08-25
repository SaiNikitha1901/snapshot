from fastapi import APIRouter

from app.schemas.learn import LearnGenerateRequest, LearnGenerateResponse
from app.services import learn_service

router = APIRouter()


@router.post("/api/learn/generate", response_model=LearnGenerateResponse)
async def generate_learn_card(request: LearnGenerateRequest) -> LearnGenerateResponse:
    return await learn_service.generate_enriched_card(request.context)
