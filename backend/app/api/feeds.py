"""GET /v1/feeds/breaking-news et GET /v1/feeds/research : veille pour la page d'accueil des médecins."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import current_user
from app.domain.feeds.sources import NEWS, RESEARCH
from app.schemas.feeds import FeedItemOut, FeedResponse, SourceStatusOut
from app.services.feed_service import FeedAggregator, FeedBundle, get_aggregator

router = APIRouter(prefix="/v1/feeds", tags=["feeds"])


def _response(bundle: FeedBundle, response: Response) -> FeedResponse:
    response.headers["Cache-Control"] = "private, max-age=60"
    return FeedResponse(
        items=[FeedItemOut(**vars(i)) for i in bundle.items],
        sources=[SourceStatusOut(**vars(s)) for s in bundle.sources],
        generated_at=bundle.generated_at)


@router.get("/breaking-news", response_model=FeedResponse)
def breaking_news(
    response: Response, refresh: bool = Query(False),
    _user: str = Depends(current_user), feeds: FeedAggregator = Depends(get_aggregator),
) -> FeedResponse:
    # `def` : FastAPI l'exécute dans un thread, les téléchargements ne bloquent pas le serveur.
    return _response(feeds.get_group(NEWS, refresh=refresh), response)


@router.get("/research", response_model=FeedResponse)
def research(
    response: Response, refresh: bool = Query(False),
    _user: str = Depends(current_user), feeds: FeedAggregator = Depends(get_aggregator),
) -> FeedResponse:
    return _response(feeds.get_group(RESEARCH, refresh=refresh), response)
