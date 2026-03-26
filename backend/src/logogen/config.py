from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
DATABASE_PATH: Path = DATA_DIR / "logogen.db"
BRANDS_DIR: Path = DATA_DIR / "brands"
FONTS_DIR: Path = DATA_DIR / "fonts"

# Model configuration
TEXT_MODEL_ID: str = os.getenv("TEXT_MODEL_ID", "mlx-community/Qwen3-8B-4bit")
IMAGE_MODEL_NAME: str = os.getenv("IMAGE_MODEL_NAME", "schnell")
IMAGE_MODEL_QUANTIZE: int = int(os.getenv("IMAGE_MODEL_QUANTIZE", "4"))
LORA_REPO_ID: str = os.getenv(
    "LORA_REPO_ID", "Shakker-Labs/FLUX.1-dev-LoRA-Logo-Design"
)

# Logo generation (3 concepts, all same size)
LOGO_WIDTH: int = 1024
LOGO_HEIGHT: int = 1024
LOGO_STEPS: int = 4
LOGO_LORA_SCALE: str = "0.8"
LOGO_CONCEPT_COUNT: int = 3

# Text generation
TEXT_MAX_TOKENS: int = 2048
TEXT_MAX_RETRIES: int = 3
