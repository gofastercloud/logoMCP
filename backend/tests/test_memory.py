from unittest.mock import MagicMock, patch

from logogen.pipeline.memory import unload_model


@patch("logogen.pipeline.memory.gc.collect")
def test_unload_calls_gc(mock_gc):
    obj = MagicMock()
    unload_model(obj)
    mock_gc.assert_called_once()


@patch("logogen.pipeline.memory.gc.collect")
@patch("mlx.core.metal.clear_cache")
def test_unload_clears_mlx_cache(mock_clear, mock_gc):
    unload_model(MagicMock())
    mock_clear.assert_called_once()


@patch("logogen.pipeline.memory.gc.collect")
def test_unload_multiple_refs(mock_gc):
    a, b, c = MagicMock(), MagicMock(), MagicMock()
    unload_model(a, b, c)
    mock_gc.assert_called_once()
