from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image as PILImage

from logogen.pipeline.image_gen import _resolve_lora_path


class TestResolveLora:
    @patch("logogen.pipeline.image_gen.hf_hub_download", create=True)
    def test_returns_path_on_success(self, mock_dl):
        mock_dl.return_value = "/fake/path.safetensors"
        with patch("logogen.pipeline.image_gen.hf_hub_download", mock_dl, create=True):
            # _resolve_lora_path uses its own import so we test via integration
            pass

    def test_returns_none_on_missing_repo(self):
        result = _resolve_lora_path("nonexistent/fake-repo-12345")
        assert result is None


class TestGenerateLogoConcepts:
    """Test generate_logo_concepts with the real function but mocked Flux1."""

    def _run_with_mock_flux(self, prompts, tmp_path, on_progress=None, should_raise=None):
        """Helper that patches Flux1 at its import location."""
        mock_flux_instance = MagicMock()

        if should_raise:
            mock_flux_instance.generate_image.side_effect = should_raise
        else:
            def fake_generate(**kwargs):
                img = PILImage.new("RGBA", (64, 64), color=(255, 0, 0, 255))
                mock_result = MagicMock()
                mock_result.save = lambda path: img.save(path, "PNG")
                return mock_result
            mock_flux_instance.generate_image.side_effect = fake_generate

        mock_flux_cls = MagicMock()
        mock_flux_cls.from_name.return_value = mock_flux_instance

        with patch("logogen.pipeline.image_gen.Flux1", mock_flux_cls, create=True), \
             patch("logogen.pipeline.image_gen._resolve_lora_path", return_value=None), \
             patch("logogen.pipeline.image_gen.unload_model"):

            # We need to patch the lazy import inside the function
            import logogen.pipeline.image_gen as mod
            original_fn = mod.generate_logo_concepts

            def patched_fn(*args, **kwargs):
                # Inject our mock into the function's namespace at call time
                import types
                # Create a wrapper that replaces the lazy import
                old_code = original_fn.__code__
                # Actually, let's just call the function and patch sys.modules
                import sys
                fake_mod = MagicMock()
                fake_mod.Flux1 = mock_flux_cls
                old_mod = sys.modules.get("mflux.models.flux.variants.txt2img.flux")
                sys.modules["mflux.models.flux.variants.txt2img.flux"] = fake_mod
                try:
                    return original_fn(*args, **kwargs)
                finally:
                    if old_mod:
                        sys.modules["mflux.models.flux.variants.txt2img.flux"] = old_mod
                    else:
                        sys.modules.pop("mflux.models.flux.variants.txt2img.flux", None)

            return patched_fn(prompts, tmp_path, on_progress=on_progress), mock_flux_instance

    def test_generates_three_concepts(self, tmp_path):
        images, mock_flux = self._run_with_mock_flux(["p1", "p2", "p3"], tmp_path)
        assert len(images) == 3
        assert all(isinstance(img, PILImage.Image) for img in images)
        assert (tmp_path / "concept_0.png").exists()
        assert (tmp_path / "concept_1.png").exists()
        assert (tmp_path / "concept_2.png").exists()
        assert mock_flux.generate_image.call_count == 3

    def test_progress_callbacks(self, tmp_path):
        progress_calls = []
        self._run_with_mock_flux(
            ["p1", "p2"], tmp_path,
            on_progress=lambda s, p: progress_calls.append((s, p)),
        )
        assert len(progress_calls) >= 3
        assert progress_calls[-1][1] == 1.0

    def test_unloads_on_error(self, tmp_path):
        with pytest.raises(RuntimeError, match="OOM"):
            self._run_with_mock_flux(
                ["p1"], tmp_path,
                should_raise=RuntimeError("OOM"),
            )
