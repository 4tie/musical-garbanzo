"""
Tests for BaseRepository helper methods.
"""
import pytest
from datetime import datetime, timezone

from app.repositories.base import BaseRepository


class TestBaseRepository:
    """Test BaseRepository helper methods."""
    
    def test_now_returns_iso_format(self):
        """Test that _now returns ISO 8601 formatted timestamp."""
        result = BaseRepository._now()
        # Should be parseable as ISO 8601
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo == timezone.utc
    
    def test_uuid_returns_unique_strings(self):
        """Test that _uuid returns unique UUID strings."""
        uuid1 = BaseRepository._uuid()
        uuid2 = BaseRepository._uuid()
        assert uuid1 != uuid2
        assert len(uuid1) == 36  # Standard UUID format
        assert len(uuid2) == 36
    
    def test_json_dumps_serializes_dict(self):
        """Test that _json_dumps serializes dictionaries."""
        data = {"key": "value", "number": 42}
        result = BaseRepository._json_dumps(data)
        assert result == '{"key": "value", "number": 42}'
    
    def test_json_dumps_serializes_list(self):
        """Test that _json_dumps serializes lists."""
        data = [1, 2, 3, "four"]
        result = BaseRepository._json_dumps(data)
        assert result == '[1, 2, 3, "four"]'
    
    def test_json_loads_deserializes_dict(self):
        """Test that _json_loads deserializes dictionaries."""
        json_str = '{"key": "value", "number": 42}'
        result = BaseRepository._json_loads(json_str)
        assert result == {"key": "value", "number": 42}
    
    def test_json_loads_with_default(self):
        """Test that _json_loads returns default on invalid JSON."""
        result = BaseRepository._json_loads("invalid json", default={"default": True})
        assert result == {"default": True}
    
    def test_json_loads_with_none_value(self):
        """Test that _json_loads returns default for None."""
        result = BaseRepository._json_loads(None, default={"default": True})
        assert result == {"default": True}
    
    def test_json_loads_with_empty_string(self):
        """Test that _json_loads returns default for empty string."""
        result = BaseRepository._json_loads("", default={"default": True})
        assert result == {"default": True}
    
    def test_require_allowed_passes_for_valid_value(self):
        """Test that _require_allowed passes for valid values."""
        # Should not raise
        BaseRepository._require_allowed("long", ["long", "short", "both"], "direction")
    
    def test_require_allowed_raises_for_invalid_value(self):
        """Test that _require_allowed raises for invalid values."""
        with pytest.raises(ValueError) as exc_info:
            BaseRepository._require_allowed("invalid", ["long", "short", "both"], "direction")
        
        assert "Invalid direction" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)
        assert "long, short, both" in str(exc_info.value)
    
    def test_normalize_limit_with_none(self):
        """Test that _normalize_limit uses default when limit is None."""
        result = BaseRepository._normalize_limit(None, default=50, max_value=500)
        assert result == 50
    
    def test_normalize_limit_with_valid_value(self):
        """Test that _normalize_limit returns valid limit."""
        result = BaseRepository._normalize_limit(100, default=50, max_value=500)
        assert result == 100
    
    def test_normalize_limit_clamps_negative(self):
        """Test that _normalize_limit clamps negative values to default."""
        result = BaseRepository._normalize_limit(-10, default=50, max_value=500)
        assert result == 50
    
    def test_normalize_limit_clamps_exceeds_max(self):
        """Test that _normalize_limit clamps values exceeding max."""
        result = BaseRepository._normalize_limit(1000, default=50, max_value=500)
        assert result == 500
    
    def test_normalize_limit_with_zero(self):
        """Test that _normalize_limit handles zero."""
        result = BaseRepository._normalize_limit(0, default=50, max_value=500)
        assert result == 50
    
    def test_normalize_limit_default_values(self):
        """Test that _normalize_limit uses correct defaults."""
        result = BaseRepository._normalize_limit(None)
        assert result == 50  # Default default
