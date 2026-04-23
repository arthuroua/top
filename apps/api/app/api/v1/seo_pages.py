import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import SeoPage
from app.repositories.seo_pages import (
    create_seo_page,
    get_seo_page_by_slug,
    list_seo_pages,
    set_seo_page_active,
    soft_delete_seo_page,
    update_seo_page,
)
from app.schemas import SeoPageCreate, SeoPageListResponse, SeoPageRead, SeoPageToggle, SeoPageUpdate

router = APIRouter(prefix="/api/v1/seo-pages", tags=["seo-pages"])


def _admin_token() -> str:
    value = os.getenv("ADMIN_TOKEN", "").strip()
    if not value or value == "change-me-admin":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin token is not configured",
        )
    return value


def _require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token or not secrets.compare_digest(x_admin_token, _admin_token()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


def _to_read_model(record) -> SeoPageRead:
    return SeoPageRead(
        id=record.id,
        page_type=record.page_type,
        slug_path=record.slug_path,
        make=record.make,
        model=record.model,
        year=record.year,
        title=record.title,
        teaser=record.teaser,
        body=record.body,
        faq=record.faq_json or [],
        localized={
            "en": {
                "title": record.title_en,
                "teaser": record.teaser_en,
                "body": record.body_en,
                "faq": record.faq_json_en or [],
            },
            "uk": {
                "title": record.title_uk,
                "teaser": record.teaser_uk,
                "body": record.body_uk,
                "faq": record.faq_json_uk or [],
            },
            "ru": {
                "title": record.title_ru,
                "teaser": record.teaser_ru,
                "body": record.body_ru,
                "faq": record.faq_json_ru or [],
            },
        },
        sort_order=record.sort_order,
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("", response_model=SeoPageListResponse)
def list_all(
    active_only: bool = Query(default=False),
    page_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SeoPageListResponse:
    items = list_seo_pages(db, active_only=active_only, page_type=page_type)
    return SeoPageListResponse(items=[_to_read_model(item) for item in items])


@router.get("/{slug_path:path}", response_model=SeoPageRead)
def get_by_slug(
    slug_path: str,
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> SeoPageRead:
    item = get_seo_page_by_slug(db, slug_path, active_only=active_only)
    if item is None:
        raise HTTPException(status_code=404, detail="SEO page not found")
    return _to_read_model(item)


@router.post("", response_model=SeoPageRead, dependencies=[Depends(_require_admin)])
def create(payload: SeoPageCreate, db: Session = Depends(get_db)) -> SeoPageRead:
    existing = get_seo_page_by_slug(db, payload.slug_path, active_only=False)
    if existing:
        raise HTTPException(status_code=409, detail="Slug path already exists")
    page = create_seo_page(
        db,
        page_type=payload.page_type,
        slug_path=payload.slug_path,
        make=payload.make,
        model=payload.model,
        year=payload.year,
        title=payload.title,
        teaser=payload.teaser,
        body=payload.body,
        faq_json=[item.model_dump() for item in payload.faq],
        localized=payload.localized.model_dump(),
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    return _to_read_model(page)


@router.put("/{page_id}", response_model=SeoPageRead, dependencies=[Depends(_require_admin)])
def update(page_id: str, payload: SeoPageUpdate, db: Session = Depends(get_db)) -> SeoPageRead:
    page = db.get(SeoPage, page_id)
    if page is None or page.deleted_at is not None:
        raise HTTPException(status_code=404, detail="SEO page not found")

    existing = get_seo_page_by_slug(db, payload.slug_path, active_only=False)
    if existing and existing.id != page_id:
        raise HTTPException(status_code=409, detail="Slug path already exists")

    updated = update_seo_page(
        db,
        page,
        page_type=payload.page_type,
        slug_path=payload.slug_path,
        make=payload.make,
        model=payload.model,
        year=payload.year,
        title=payload.title,
        teaser=payload.teaser,
        body=payload.body,
        faq_json=[item.model_dump() for item in payload.faq],
        localized=payload.localized.model_dump(),
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    return _to_read_model(updated)


@router.patch("/{page_id}/active", response_model=SeoPageRead, dependencies=[Depends(_require_admin)])
def toggle_active(page_id: str, payload: SeoPageToggle, db: Session = Depends(get_db)) -> SeoPageRead:
    page = db.get(SeoPage, page_id)
    if page is None or page.deleted_at is not None:
        raise HTTPException(status_code=404, detail="SEO page not found")
    updated = set_seo_page_active(db, page, payload.is_active)
    return _to_read_model(updated)


@router.delete("/{page_id}", status_code=204, dependencies=[Depends(_require_admin)])
def delete(page_id: str, db: Session = Depends(get_db)) -> Response:
    page = db.get(SeoPage, page_id)
    if page is None or page.deleted_at is not None:
        raise HTTPException(status_code=404, detail="SEO page not found")
    soft_delete_seo_page(db, page)
    return Response(status_code=204)
