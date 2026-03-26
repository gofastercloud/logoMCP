from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from logogen.models.schemas import (
    BrandBrief,
    BrandDetail,
    BrandSpecs,
    BrandStatus,
    BrandSummary,
    ColorEntry,
    CreativeDirection,
    LogoConcept,
    TypographyRec,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


# --- Brands ---


async def create_brand(db: aiosqlite.Connection, brief: BrandBrief) -> str:
    brand_id = _uuid()
    now = _now()
    await db.execute(
        "INSERT INTO brands (id, name, brief_json, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (brand_id, brief.company_name, brief.model_dump_json(), BrandStatus.CREATED.value, now, now),
    )
    await db.commit()
    return brand_id


async def list_brands(db: aiosqlite.Connection) -> list[BrandSummary]:
    cursor = await db.execute(
        "SELECT id, name, status, created_at, updated_at FROM brands ORDER BY created_at DESC"
    )
    rows = await cursor.fetchall()
    return [
        BrandSummary(
            id=row["id"],
            name=row["name"],
            status=BrandStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
        for row in rows
    ]


async def get_brand(db: aiosqlite.Connection, brand_id: str) -> BrandDetail | None:
    cursor = await db.execute(
        "SELECT id, name, brief_json, status, created_at, updated_at FROM brands WHERE id = ?",
        (brand_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    brief = BrandBrief.model_validate_json(row["brief_json"])
    specs = await get_brand_specs(db, brand_id)
    concepts = await get_logo_concepts(db, brand_id)

    return BrandDetail(
        id=row["id"],
        name=row["name"],
        status=BrandStatus(row["status"]),
        brief=brief,
        specs=specs,
        concepts=concepts,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


async def update_brand_status(
    db: aiosqlite.Connection, brand_id: str, status: BrandStatus
) -> None:
    now = _now()
    await db.execute(
        "UPDATE brands SET status = ?, updated_at = ? WHERE id = ?",
        (status.value, now, brand_id),
    )
    await db.commit()


async def delete_brand(db: aiosqlite.Connection, brand_id: str) -> bool:
    cursor = await db.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
    await db.commit()
    return cursor.rowcount > 0


# --- Brand Specs ---


async def save_brand_specs(
    db: aiosqlite.Connection,
    brand_id: str,
    creative_direction: CreativeDirection,
    color_palette: list[ColorEntry],
    typography: TypographyRec,
) -> None:
    cd_json = creative_direction.model_dump_json()
    cp_json = json.dumps([c.model_dump() for c in color_palette])
    ty_json = typography.model_dump_json()
    tagline = creative_direction.tagline

    await db.execute(
        """INSERT OR REPLACE INTO brand_specs
           (brand_id, creative_direction_json, color_palette_json, typography_json, tagline)
           VALUES (?, ?, ?, ?, ?)""",
        (brand_id, cd_json, cp_json, ty_json, tagline),
    )
    await db.commit()


async def get_brand_specs(db: aiosqlite.Connection, brand_id: str) -> BrandSpecs | None:
    cursor = await db.execute(
        "SELECT creative_direction_json, color_palette_json, typography_json, tagline FROM brand_specs WHERE brand_id = ?",
        (brand_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    return BrandSpecs(
        creative_direction=CreativeDirection.model_validate_json(row["creative_direction_json"]),
        color_palette=[ColorEntry(**c) for c in json.loads(row["color_palette_json"])],
        typography=TypographyRec.model_validate_json(row["typography_json"]),
        tagline=row["tagline"],
    )


async def update_brand_specs(
    db: aiosqlite.Connection,
    brand_id: str,
    color_palette: list[ColorEntry] | None = None,
    typography: TypographyRec | None = None,
    tagline: str | None = None,
) -> None:
    updates = []
    params: list[Any] = []
    if color_palette is not None:
        updates.append("color_palette_json = ?")
        params.append(json.dumps([c.model_dump() for c in color_palette]))
    if typography is not None:
        updates.append("typography_json = ?")
        params.append(typography.model_dump_json())
    if tagline is not None:
        updates.append("tagline = ?")
        params.append(tagline)
    if not updates:
        return
    params.append(brand_id)
    await db.execute(
        f"UPDATE brand_specs SET {', '.join(updates)} WHERE brand_id = ?",
        params,
    )
    await db.commit()


# --- Logo Concepts ---


async def save_logo_concepts(
    db: aiosqlite.Connection,
    brand_id: str,
    concepts: list[dict],
    generation_run: int = 1,
) -> None:
    now = _now()
    for c in concepts:
        await db.execute(
            """INSERT INTO logo_concepts
               (id, brand_id, concept_index, prompt, image_path, is_selected, generation_run, created_at)
               VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
            (_uuid(), brand_id, c["concept_index"], c["prompt"], c["image_path"], generation_run, now),
        )
    await db.commit()


async def get_logo_concepts(
    db: aiosqlite.Connection, brand_id: str, current_run_only: bool = True
) -> list[LogoConcept]:
    if current_run_only:
        cursor = await db.execute(
            """SELECT concept_index, prompt, is_selected, image_path
               FROM logo_concepts
               WHERE brand_id = ? AND generation_run = (
                   SELECT MAX(generation_run) FROM logo_concepts WHERE brand_id = ?
               )
               ORDER BY concept_index""",
            (brand_id, brand_id),
        )
    else:
        cursor = await db.execute(
            "SELECT concept_index, prompt, is_selected, image_path FROM logo_concepts WHERE brand_id = ? ORDER BY generation_run, concept_index",
            (brand_id,),
        )
    rows = await cursor.fetchall()
    return [
        LogoConcept(
            concept_index=row["concept_index"],
            prompt=row["prompt"],
            is_selected=bool(row["is_selected"]),
            image_path=row["image_path"],
        )
        for row in rows
    ]


async def select_logo_concept(
    db: aiosqlite.Connection, brand_id: str, concept_index: int
) -> bool:
    # Deselect all for this brand's current run
    await db.execute(
        """UPDATE logo_concepts SET is_selected = 0
           WHERE brand_id = ? AND generation_run = (
               SELECT MAX(generation_run) FROM logo_concepts WHERE brand_id = ?
           )""",
        (brand_id, brand_id),
    )
    # Select the chosen concept
    cursor = await db.execute(
        """UPDATE logo_concepts SET is_selected = 1
           WHERE brand_id = ? AND concept_index = ? AND generation_run = (
               SELECT MAX(generation_run) FROM logo_concepts WHERE brand_id = ?
           )""",
        (brand_id, concept_index, brand_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def get_max_generation_run(db: aiosqlite.Connection, brand_id: str) -> int:
    cursor = await db.execute(
        "SELECT COALESCE(MAX(generation_run), 0) FROM logo_concepts WHERE brand_id = ?",
        (brand_id,),
    )
    row = await cursor.fetchone()
    return row[0]


# --- Rendered Assets ---


async def save_rendered_asset(
    db: aiosqlite.Connection,
    brand_id: str,
    template_slug: str,
    variant: str,
    fmt: str,
    scale: str,
    file_path: str,
    width: int,
    height: int,
) -> None:
    now = _now()
    await db.execute(
        """INSERT OR REPLACE INTO rendered_assets
           (id, brand_id, template_slug, variant, format, scale, file_path, width, height, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_uuid(), brand_id, template_slug, variant, fmt, scale, file_path, width, height, now),
    )
    await db.commit()


async def get_rendered_assets(
    db: aiosqlite.Connection, brand_id: str, category: str | None = None
) -> list[dict]:
    if category:
        cursor = await db.execute(
            """SELECT template_slug, variant, format, scale, file_path, width, height
               FROM rendered_assets WHERE brand_id = ? AND template_slug LIKE ?
               ORDER BY template_slug, variant, format""",
            (brand_id, f"{category}%"),
        )
    else:
        cursor = await db.execute(
            """SELECT template_slug, variant, format, scale, file_path, width, height
               FROM rendered_assets WHERE brand_id = ?
               ORDER BY template_slug, variant, format""",
            (brand_id,),
        )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def delete_rendered_assets(db: aiosqlite.Connection, brand_id: str) -> None:
    await db.execute("DELETE FROM rendered_assets WHERE brand_id = ?", (brand_id,))
    await db.commit()
