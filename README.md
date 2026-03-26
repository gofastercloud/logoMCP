# logoMCP

A local MCP server that generates complete brand design systems using AI. Give it a brand brief, get back logo concepts, color palettes, typography, and a full asset library — all running locally on Apple Silicon.

Built for LLM-based marketing teams: Claude or other agents submit briefs, visually review generated logos, iterate on brand specs, and export production-ready assets.

## What It Does

1. **Brand Brief** → You describe the brand (name, industry, audience, mood)
2. **AI Brand Specs** → Local text LLM generates creative direction, tagline, color palette, typography
3. **Logo Concepts** → Local image model generates 3 logo mark concepts at 1024×1024
4. **Template Rendering** → Selecting a logo triggers automatic generation of all brand assets:
   - Logo variants (mark, primary horizontal, stacked, wordmark, favicon)
   - Each in light/dark/transparent backgrounds
   - PNG (1x + 2x), JPEG, and SVG formats
   - Favicon at 16, 32, 48, and 192px

**~3 minutes** from brief to 47 production-ready assets. No cloud APIs, no subscriptions, everything on your Mac.

## Requirements

- **macOS** with Apple Silicon (M1 or later)
- **24GB+ RAM** (32GB recommended)
- **Python 3.12+** via [uv](https://docs.astral.sh/uv/)
- **HuggingFace account** with access to [FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell) (free, gated model — accept terms then `hf auth login`)

## Installation

```bash
# Clone
git clone https://github.com/gofastercloud/logoMCP.git
cd logoMCP

# Install Python dependencies
cd backend
uv sync

# Authenticate with HuggingFace (required for Flux model access)
hf auth login
# Or: cd backend && uv run python -c "from huggingface_hub import login; login()"

# Run tests to verify everything works
uv run pytest
```

Models are downloaded automatically on first use (~12GB total for Qwen3 8B + Flux.1-schnell).

## Using with Claude Code

Add logoMCP as an MCP server in your Claude Code settings:

**Option 1: Project-level** — add to `.claude/settings.json` in any project:

```json
{
  "mcpServers": {
    "logomcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/logoMCP/backend", "python", "-m", "logogen.server"],
      "env": {}
    }
  }
}
```

**Option 2: User-level** — add to `~/.claude/settings.json` to make it available in all projects:

```json
{
  "mcpServers": {
    "logomcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/logoMCP/backend", "python", "-m", "logogen.server"],
      "env": {}
    }
  }
}
```

Replace `/path/to/logoMCP` with the actual path where you cloned the repo.

### Using with Claude Code Cowork

When running Claude Code in cowork/team mode, any team member with access to the MCP server can call logoMCP tools. Configure the MCP server at the user level (Option 2 above) so all spawned agents inherit access.

Example cowork workflow — a marketing team lead agent can:

```
1. create_brand("Solaris", "Solar Energy", "Eco-conscious homeowners", ["sustainable", "bright"])
2. update_brand_specs(brand_id, colors=[...], typography={...})  # optional pre-set preferences
3. generate_logos(brand_id)  # generates specs + 3 logo concepts
4. [visually review the 3 returned concept images]
5. select_logo(brand_id, concept_index=1)  # triggers template rendering
6. get_brand_assets(brand_id)  # browse all rendered assets
7. get_asset(brand_id, "logo-primary", "dark", "png")  # inspect specific asset
8. export_brand(brand_id)  # download ZIP
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `create_brand` | Create a brand from a brief (name, industry, audience, mood keywords) |
| `list_brands` | List all brands with status |
| `get_brand` | Get full brand details (specs, concepts, assets) |
| `delete_brand` | Delete a brand and all generated assets |
| `update_brand_specs` | Set or override colors, fonts, tagline, creative direction |
| `generate_logos` | Run AI pipeline: text LLM → image model → 3 logo concepts |
| `get_logo_concepts` | Review logo concept images |
| `select_logo` | Pick a concept → triggers template rendering of all assets |
| `get_logo_prompts` | View current image generation prompts |
| `update_logo_prompts` | Revise prompts (with safety guardrails enforced) |
| `get_brand_assets` | Browse rendered assets with thumbnails |
| `get_asset` | Get a specific asset image in any format/variant/scale |

## Architecture

```
Brand Brief → Text LLM (Qwen3 8B) → Image Model (Flux.1-schnell) → Template Engine → Assets
                  ↓                         ↓                            ↓
           Creative direction        3 logo concepts           47 production files
           Color palette             1024×1024 each            PNG/JPEG/SVG
           Typography                                          Light/Dark/Transparent
           Tagline                                             1x + 2x resolution
```

**Memory management:** Models load sequentially — text model generates all specs, unloads, then image model generates logos, unloads. Template rendering is pure CPU (Pillow). This keeps peak memory under 16GB, fitting comfortably on 24GB machines.

**Template system:** Each asset type is a Python class inheriting from `BaseTemplate`. Adding a new asset = writing a `render()` method. The engine handles all variant/format/scale permutations automatically.

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
# Model selection
TEXT_MODEL_ID=mlx-community/Qwen3-8B-4bit    # Text LLM
IMAGE_MODEL_NAME=schnell                       # Flux variant (schnell or dev)
IMAGE_MODEL_QUANTIZE=4                         # Quantization (4 or 8 bit)

# Generation parameters
LOGO_STEPS=4          # Inference steps (schnell: 2-4, dev: 20-25)
LOGO_WIDTH=1024       # Logo dimensions (must be multiples of 32)
LOGO_HEIGHT=1024
```

Use `IMAGE_MODEL_NAME=dev` for higher quality logos (slower, needs 32GB+ RAM).

## Development

```bash
cd backend

# Run tests
uv run pytest

# Run tests verbose
uv run pytest -v

# Run E2E test with real models (slow, generates actual logos)
uv run python test_e2e.py

# Run MCP server directly (for debugging)
uv run python -m logogen.server
```

## Dependency Licenses

All dependencies use permissive licenses compatible with MIT:

| Dependency | License | Purpose |
|-----------|---------|---------|
| [mlx](https://github.com/ml-explore/mlx) / [mlx-lm](https://github.com/ml-explore/mlx-examples) | MIT | Apple Silicon ML framework + LLM inference |
| [mflux](https://github.com/filipstrand/mflux) | MIT | Flux image generation on MLX |
| [Pillow](https://github.com/python-pillow/Pillow) | HPND | Image compositing and template rendering |
| [drawsvg](https://github.com/cduck/drawsvg) | MIT | SVG generation |
| [vtracer](https://github.com/visioncortex/vtracer) | MIT | Bitmap to SVG tracing |
| [pydantic](https://github.com/pydantic/pydantic) | MIT | Data validation and schemas |
| [aiosqlite](https://github.com/omnilib/aiosqlite) | MIT | Async SQLite |
| [mcp](https://github.com/modelcontextprotocol/python-sdk) | MIT | MCP server SDK |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | BSD-3-Clause | Environment variable loading |

## License

MIT — see [LICENSE](LICENSE).
