from datetime import datetime, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.data.seo_seed import SEO_PAGE_SEED
from app.models import SeoPage


def _localized_value(localized: dict | None, locale: str, field: str):
    if not localized:
        return None
    locale_data = localized.get(locale) or {}
    return locale_data.get(field)


def seed_seo_pages(db: Session) -> None:
    existing_count = db.execute(select(func.count()).select_from(SeoPage)).scalar_one()
    if existing_count > 0:
        return

    for item in SEO_PAGE_SEED:
        db.add(
            SeoPage(
                page_type=item["page_type"],
                slug_path=item["slug_path"],
                make=item.get("make"),
                model=item.get("model"),
                year=item.get("year"),
                title=item["title"],
                teaser=item["teaser"],
                title_uk=item["title"],
                teaser_uk=item["teaser"],
                sort_order=item.get("sort_order", 0),
                is_active=True,
            )
        )
    db.commit()


def _base_query(active_only: bool = False) -> Select[tuple[SeoPage]]:
    query = select(SeoPage).where(SeoPage.deleted_at.is_(None))
    if active_only:
        query = query.where(SeoPage.is_active.is_(True))
    return query


def list_seo_pages(
    db: Session,
    *,
    active_only: bool = False,
    page_type: str | None = None,
) -> list[SeoPage]:
    query = _base_query(active_only=active_only)
    if page_type:
        query = query.where(SeoPage.page_type == page_type)
    query = query.order_by(SeoPage.sort_order.asc(), SeoPage.title.asc())
    return list(db.execute(query).scalars().all())


def get_seo_page_by_slug(db: Session, slug_path: str, *, active_only: bool = False) -> SeoPage | None:
    query = _base_query(active_only=active_only).where(SeoPage.slug_path == slug_path)
    return db.execute(query).scalar_one_or_none()


def create_seo_page(
    db: Session,
    *,
    page_type: str,
    slug_path: str,
    make: str | None,
    model: str | None,
    year: int | None,
    title: str,
    teaser: str,
    body: str | None,
    faq_json: list[dict] | None,
    localized: dict | None,
    sort_order: int,
    is_active: bool,
) -> SeoPage:
    page = SeoPage(
        page_type=page_type,
        slug_path=slug_path,
        make=make,
        model=model,
        year=year,
        title=title,
        teaser=teaser,
        body=body,
        faq_json=faq_json,
        title_en=_localized_value(localized, "en", "title"),
        teaser_en=_localized_value(localized, "en", "teaser"),
        body_en=_localized_value(localized, "en", "body"),
        faq_json_en=_localized_value(localized, "en", "faq"),
        title_uk=_localized_value(localized, "uk", "title"),
        teaser_uk=_localized_value(localized, "uk", "teaser"),
        body_uk=_localized_value(localized, "uk", "body"),
        faq_json_uk=_localized_value(localized, "uk", "faq"),
        title_ru=_localized_value(localized, "ru", "title"),
        teaser_ru=_localized_value(localized, "ru", "teaser"),
        body_ru=_localized_value(localized, "ru", "body"),
        faq_json_ru=_localized_value(localized, "ru", "faq"),
        sort_order=sort_order,
        is_active=is_active,
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def update_seo_page(
    db: Session,
    page: SeoPage,
    *,
    page_type: str,
    slug_path: str,
    make: str | None,
    model: str | None,
    year: int | None,
    title: str,
    teaser: str,
    body: str | None,
    faq_json: list[dict] | None,
    localized: dict | None,
    sort_order: int,
    is_active: bool,
) -> SeoPage:
    page.page_type = page_type
    page.slug_path = slug_path
    page.make = make
    page.model = model
    page.year = year
    page.title = title
    page.teaser = teaser
    page.body = body
    page.faq_json = faq_json
    page.title_en = _localized_value(localized, "en", "title")
    page.teaser_en = _localized_value(localized, "en", "teaser")
    page.body_en = _localized_value(localized, "en", "body")
    page.faq_json_en = _localized_value(localized, "en", "faq")
    page.title_uk = _localized_value(localized, "uk", "title")
    page.teaser_uk = _localized_value(localized, "uk", "teaser")
    page.body_uk = _localized_value(localized, "uk", "body")
    page.faq_json_uk = _localized_value(localized, "uk", "faq")
    page.title_ru = _localized_value(localized, "ru", "title")
    page.teaser_ru = _localized_value(localized, "ru", "teaser")
    page.body_ru = _localized_value(localized, "ru", "body")
    page.faq_json_ru = _localized_value(localized, "ru", "faq")
    page.sort_order = sort_order
    page.is_active = is_active
    db.commit()
    db.refresh(page)
    return page


def set_seo_page_active(db: Session, page: SeoPage, is_active: bool) -> SeoPage:
    page.is_active = is_active
    db.commit()
    db.refresh(page)
    return page


def soft_delete_seo_page(db: Session, page: SeoPage) -> None:
    page.deleted_at = datetime.now(timezone.utc)
    db.commit()
