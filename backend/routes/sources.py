"""Compliant external-source fetching (GitHub API, portfolio sites, job posts).

Returns normalized profile-style text the user can drop straight into /analyze.
LinkedIn is deliberately refused here (ToS) with a 422 pointing at the upload
path — see :mod:`services.scrape_service`.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from models.schemas import FetchRequest, FetchResponse
from routes.deps import get_scrape_service
from services.scrape_service import FetchError, ScrapeService, UnsupportedSource

router = APIRouter(prefix="/fetch", tags=["sources"])


@router.post("", response_model=FetchResponse)
def fetch_source(
    payload: FetchRequest, scraper: ScrapeService = Depends(get_scrape_service)
) -> FetchResponse:
    try:
        src = scraper.fetch(payload.url, kind=payload.kind)
    except UnsupportedSource as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except FetchError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return FetchResponse(
        url=src.url,
        kind=src.kind,  # type: ignore[arg-type]
        title=src.title,
        text=src.text,
        char_count=len(src.text),
        metadata=src.metadata,
    )
