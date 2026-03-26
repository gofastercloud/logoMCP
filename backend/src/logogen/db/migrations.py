from __future__ import annotations

import aiosqlite

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS brands (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    brief_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brand_specs (
    brand_id TEXT PRIMARY KEY REFERENCES brands(id) ON DELETE CASCADE,
    creative_direction_json TEXT NOT NULL,
    color_palette_json TEXT NOT NULL,
    typography_json TEXT NOT NULL,
    tagline TEXT
);

CREATE TABLE IF NOT EXISTS logo_concepts (
    id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    concept_index INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    image_path TEXT NOT NULL,
    is_selected INTEGER NOT NULL DEFAULT 0,
    generation_run INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE(brand_id, concept_index, generation_run)
);

CREATE TABLE IF NOT EXISTS rendered_assets (
    id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    template_slug TEXT NOT NULL,
    variant TEXT NOT NULL,
    format TEXT NOT NULL,
    scale TEXT NOT NULL DEFAULT '1x',
    file_path TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(brand_id, template_slug, variant, format, scale)
);
"""


async def run_migrations(db: aiosqlite.Connection) -> None:
    await db.executescript(SCHEMA_SQL)
    await db.commit()
