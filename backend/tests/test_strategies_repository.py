"""
Tests for StrategyRepository.
"""
import pytest

from app.repositories.strategies import (
    StrategyRepository,
    StrategyNotFoundError,
    StrategyVersionNotFoundError,
)
from app.schemas.strategies import StrategyCreate, StrategyUpdate, StrategyVersionCreate
from app.db.sqlite import get_connection


@pytest.fixture
def strategy_repo():
    """Create a StrategyRepository instance."""
    return StrategyRepository()


@pytest.fixture
def clean_db():
    """Clean the strategies and strategy_versions tables before each test."""
    conn = get_connection()
    conn.execute("DELETE FROM strategy_versions")
    conn.execute("DELETE FROM strategies")
    conn.commit()
    conn.close()
    yield
    # Clean up after test
    conn = get_connection()
    conn.execute("DELETE FROM strategy_versions")
    conn.execute("DELETE FROM strategies")
    conn.commit()
    conn.close()


class TestStrategyRepository:
    """Test StrategyRepository operations."""
    
    def test_create_strategy(self, strategy_repo, clean_db):
        """Test creating a strategy."""
        data = StrategyCreate(
            name="Test Strategy",
            source_type="generated",
            timeframe="1h",
            direction="both",
        )
        
        strategy = strategy_repo.create_strategy(data)
        
        assert strategy is not None
        assert strategy["name"] == "Test Strategy"
        assert strategy["source_type"] == "generated"
        assert strategy["status"] == "draft"
        assert strategy["direction"] == "both"
        assert strategy["timeframe"] == "1h"
        assert strategy["is_demo"] is False
        assert strategy["id"] is not None
        assert strategy["created_at"] is not None
    
    def test_get_strategy(self, strategy_repo, clean_db):
        """Test getting a strategy by ID."""
        data = StrategyCreate(name="Test Strategy", source_type="generated")
        created = strategy_repo.create_strategy(data)
        
        retrieved = strategy_repo.get_strategy(created["id"])
        
        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["name"] == "Test Strategy"
    
    def test_get_strategy_not_found(self, strategy_repo, clean_db):
        """Test getting a non-existent strategy."""
        result = strategy_repo.get_strategy("non-existent-id")
        assert result is None
    
    def test_list_strategies(self, strategy_repo, clean_db):
        """Test listing strategies."""
        strategy_repo.create_strategy(StrategyCreate(name="Strategy 1", source_type="generated"))
        strategy_repo.create_strategy(StrategyCreate(name="Strategy 2", source_type="uploaded"))
        strategy_repo.create_strategy(StrategyCreate(name="Strategy 3", source_type="manual"))
        
        strategies = strategy_repo.list_strategies()
        
        assert len(strategies) == 3
    
    def test_list_strategies_with_status_filter(self, strategy_repo, clean_db):
        """Test listing strategies with status filter."""
        strategy_repo.create_strategy(StrategyCreate(name="Strategy 1", source_type="generated"))
        strategy_repo.create_strategy(StrategyCreate(name="Strategy 2", source_type="uploaded", status="active"))
        
        strategies = strategy_repo.list_strategies(status="draft")
        
        assert len(strategies) == 1
        assert strategies[0]["status"] == "draft"
    
    def test_list_strategies_with_source_type_filter(self, strategy_repo, clean_db):
        """Test listing strategies with source_type filter."""
        strategy_repo.create_strategy(StrategyCreate(name="Strategy 1", source_type="generated"))
        strategy_repo.create_strategy(StrategyCreate(name="Strategy 2", source_type="uploaded"))
        strategy_repo.create_strategy(StrategyCreate(name="Strategy 3", source_type="generated"))
        
        strategies = strategy_repo.list_strategies(source_type="generated")
        
        assert len(strategies) == 2

    def test_imported_source_type_allowed(self, strategy_repo, clean_db):
        """Test that imported strategy source type is accepted."""
        strategy = strategy_repo.create_strategy(
            StrategyCreate(name="Imported Strategy", source_type="imported")
        )

        assert strategy["source_type"] == "imported"
    
    def test_list_strategies_with_limit(self, strategy_repo, clean_db):
        """Test listing strategies with limit."""
        for i in range(10):
            strategy_repo.create_strategy(StrategyCreate(name=f"Strategy {i}", source_type="generated"))
        
        strategies = strategy_repo.list_strategies(limit=5)
        
        assert len(strategies) == 5
    
    def test_update_strategy(self, strategy_repo, clean_db):
        """Test updating a strategy."""
        data = StrategyCreate(name="Test Strategy", source_type="generated")
        strategy = strategy_repo.create_strategy(data)
        
        update_data = StrategyUpdate(
            name="Updated Strategy",
            timeframe="4h",
            status="active",
        )
        updated = strategy_repo.update_strategy(strategy["id"], update_data)
        
        assert updated["name"] == "Updated Strategy"
        assert updated["timeframe"] == "4h"
        assert updated["status"] == "active"
    
    def test_update_strategy_not_found(self, strategy_repo, clean_db):
        """Test updating a non-existent strategy."""
        with pytest.raises(StrategyNotFoundError):
            strategy_repo.update_strategy("non-existent-id", StrategyUpdate(name="Test"))
    
    def test_archive_strategy(self, strategy_repo, clean_db):
        """Test archiving a strategy."""
        data = StrategyCreate(name="Test Strategy", source_type="generated")
        strategy = strategy_repo.create_strategy(data)
        
        archived = strategy_repo.archive_strategy(strategy["id"])
        
        assert archived["status"] == "archived"
    
    def test_create_version(self, strategy_repo, clean_db):
        """Test creating a strategy version."""
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        
        version_data = StrategyVersionCreate(
            strategy_id=strategy["id"],
            version_number=1,
            py_path="/path/to/strategy.py",
            json_path="/path/to/strategy.json",
            spec={"indicators": ["RSI"]},
            params={"stoploss": -0.1},
        )
        
        version = strategy_repo.create_version(version_data)
        
        assert version is not None
        assert version["strategy_id"] == strategy["id"]
        assert version["version_number"] == 1
        assert version["py_path"] == "/path/to/strategy.py"
        assert version["spec"] == {"indicators": ["RSI"]}
        assert version["params"] == {"stoploss": -0.1}
    
    def test_create_version_auto_increment(self, strategy_repo, clean_db):
        """Test that version number auto-increments if not provided."""
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        
        # Create version 1
        strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy["id"], version_number=1))
        
        # Create version without number - should auto-increment to 2
        version = strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy["id"]))
        
        assert version["version_number"] == 2
    
    def test_create_version_first_version_becomes_current(self, strategy_repo, clean_db):
        """Test that version 1 automatically becomes current."""
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        
        version = strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy["id"], version_number=1))
        
        # Refresh strategy
        strategy = strategy_repo.get_strategy(strategy["id"])
        
        assert strategy["current_version_id"] == version["id"]
    
    def test_get_version(self, strategy_repo, clean_db):
        """Test getting a version by ID."""
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        created = strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy["id"], version_number=1))
        
        retrieved = strategy_repo.get_version(created["id"])
        
        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["version_number"] == 1
    
    def test_get_version_not_found(self, strategy_repo, clean_db):
        """Test getting a non-existent version."""
        result = strategy_repo.get_version("non-existent-id")
        assert result is None
    
    def test_list_versions(self, strategy_repo, clean_db):
        """Test listing versions for a strategy."""
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy["id"], version_number=1))
        strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy["id"], version_number=2))
        strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy["id"], version_number=3))
        
        versions = strategy_repo.list_versions(strategy["id"])
        
        assert len(versions) == 3
        # Should be in descending order
        assert versions[0]["version_number"] == 3
        assert versions[1]["version_number"] == 2
        assert versions[2]["version_number"] == 1
    
    def test_set_current_version(self, strategy_repo, clean_db):
        """Test setting the current version."""
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        v1 = strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy["id"], version_number=1))
        v2 = strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy["id"], version_number=2))
        
        updated_strategy = strategy_repo.set_current_version(strategy["id"], v2["id"])
        
        assert updated_strategy["current_version_id"] == v2["id"]
    
    def test_set_current_version_not_found_strategy(self, strategy_repo, clean_db):
        """Test setting current version for non-existent strategy."""
        with pytest.raises(StrategyNotFoundError):
            strategy_repo.set_current_version("non-existent-id", "version-id")
    
    def test_set_current_version_not_found_version(self, strategy_repo, clean_db):
        """Test setting current version with non-existent version."""
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        
        with pytest.raises(StrategyVersionNotFoundError):
            strategy_repo.set_current_version(strategy["id"], "non-existent-version-id")
    
    def test_set_current_version_wrong_strategy(self, strategy_repo, clean_db):
        """Test setting current version from wrong strategy."""
        strategy1 = strategy_repo.create_strategy(StrategyCreate(name="Strategy 1", source_type="generated"))
        strategy2 = strategy_repo.create_strategy(StrategyCreate(name="Strategy 2", source_type="generated"))
        version = strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy1["id"], version_number=1))
        
        with pytest.raises(StrategyVersionNotFoundError):
            strategy_repo.set_current_version(strategy2["id"], version["id"])
    
    def test_get_current_version(self, strategy_repo, clean_db):
        """Test getting the current version."""
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        version = strategy_repo.create_version(StrategyVersionCreate(strategy_id=strategy["id"], version_number=1))
        
        current = strategy_repo.get_current_version(strategy["id"])
        
        assert current is not None
        assert current["id"] == version["id"]
        assert current["is_current"] is True
    
    def test_get_current_version_none(self, strategy_repo, clean_db):
        """Test getting current version when none is set."""
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        
        current = strategy_repo.get_current_version(strategy["id"])
        
        assert current is None
    
    def test_delete_demo_strategies(self, strategy_repo, clean_db):
        """Test deleting demo strategies."""
        strategy_repo.create_strategy(StrategyCreate(name="Demo 1", source_type="generated", is_demo=True))
        strategy_repo.create_strategy(StrategyCreate(name="Demo 2", source_type="uploaded", is_demo=True))
        strategy_repo.create_strategy(StrategyCreate(name="Real Strategy", source_type="generated", is_demo=False))
        
        deleted_count = strategy_repo.delete_demo_strategies()
        
        assert deleted_count == 2
        
        strategies = strategy_repo.list_strategies()
        assert len(strategies) == 1
        assert strategies[0]["name"] == "Real Strategy"
    
    def test_json_spec_params_roundtrip(self, strategy_repo, clean_db):
        """Test that spec and params serialize/deserialize correctly."""
        spec = {"indicators": ["RSI", "MACD"], "timeframe": "1h"}
        params = {"stoploss": -0.1, "roi": {"0": 0.1, "60": 0.05}}
        
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        version = strategy_repo.create_version(
            StrategyVersionCreate(
                strategy_id=strategy["id"],
                spec=spec,
                params=params,
            )
        )
        
        assert version["spec"] == spec
        assert version["params"] == params
        assert isinstance(version["spec"], dict)
        assert isinstance(version["params"], dict)
    
    def test_invalid_source_type_rejected(self, strategy_repo, clean_db):
        """Test that invalid source_type is rejected."""
        data = StrategyCreate(name="Test Strategy", source_type="invalid_type")
        
        with pytest.raises(ValueError):
            strategy_repo.create_strategy(data)
    
    def test_invalid_direction_rejected(self, strategy_repo, clean_db):
        """Test that invalid direction is rejected."""
        data = StrategyCreate(name="Test Strategy", source_type="generated", direction="invalid")
        
        with pytest.raises(ValueError):
            strategy_repo.create_strategy(data)
    
    def test_invalid_status_rejected(self, strategy_repo, clean_db):
        """Test that invalid status is rejected."""
        data = StrategyCreate(name="Test Strategy", source_type="generated", status="invalid")
        
        with pytest.raises(ValueError):
            strategy_repo.create_strategy(data)
    
    def test_invalid_direction_in_update_rejected(self, strategy_repo, clean_db):
        """Test that invalid direction in update is rejected."""
        strategy = strategy_repo.create_strategy(StrategyCreate(name="Test Strategy", source_type="generated"))
        
        with pytest.raises(ValueError):
            strategy_repo.update_strategy(strategy["id"], StrategyUpdate(direction="invalid"))
