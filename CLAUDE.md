# LogoGen

Local brand design system generator — MCP server for LLM-based marketing teams.

## Stack

- **Interface:** MCP server (stdio transport)
- **Backend:** Python (managed with `uv`)
- **Text LLM:** mlx-lm + Qwen3 8B 4-bit
- **Image Gen:** mflux + Flux.1-schnell 4-bit (no LoRA — prompt-driven)
- **Persistence:** SQLite via aiosqlite
- **Compositing:** Pillow (raster), drawsvg (vector), vtracer (SVG tracing)

## Commands

```bash
cd backend && uv run pytest              # Run tests
cd backend && uv run python -m logogen.server  # Run MCP server (stdio)
```

## Architecture

- MCP server exposes tools for brand CRUD, logo generation, asset rendering
- Template engine: adding a new asset = writing a BaseTemplate subclass
- Sequential pipeline: text model → unload → image model → unload → template render (CPU only)
- Never two ML models loaded simultaneously (24GB memory constraint)
- SQLite stores brands, specs, concepts, rendered asset records
- Brand assets stored under `data/brands/{id}/`

## Key Constraints

- All mflux dimensions must be multiples of 32
- Logo prompts enforce "white background, vector style, flat design" for consistency
- Qwen3 uses /nothink mode — output parsed as JSON, retry up to 3x on malformed output
- 24GB is the floor for memory budget
- MCP tools return images as base64 for multimodal agent inspection
