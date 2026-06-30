"""
Repository for Part 06 decision result persistence.
"""
from typing import Any, Optional

from app.core.constants import (
    DECISION_CLASSIFICATIONS,
    DECISION_GATE_STATUSES,
    DECISION_POLICY_NAMES,
    DECISION_REASON_SEVERITIES,
)
from app.db.sqlite import fetch_all, fetch_one, transaction
from app.repositories.base import BaseRepository
from app.schemas.decisions import DecisionResult


class DecisionRepository(BaseRepository):
    """Persistence-only repository for decision_results rows."""

    def create_decision_result(self, result: DecisionResult) -> dict:
        """
        Create a decision result row.

        This method does not update runs.classification or strategy state.
        """
        serialized = self.serialize_decision(result)
        decision_id = serialized.get("id") or self._uuid()
        created_at = serialized.get("created_at") or self._now()
        evidence = serialized.get("evidence") or {}

        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO decision_results (
                    id, run_id, classification, confidence_score, policy_name,
                    risk_profile, timeframe, decision_json, gates_json,
                    reasons_json, evidence_json, warnings_json,
                    blocking_failures_json, normalized_result_artifact_path,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    serialized["run_id"],
                    serialized["classification"],
                    serialized.get("confidence_score"),
                    serialized["policy_name"],
                    serialized.get("risk_profile"),
                    serialized.get("timeframe"),
                    self._json_dumps(serialized),
                    self._json_dumps(serialized.get("gates", [])),
                    self._json_dumps(serialized.get("reasons", [])),
                    self._json_dumps(evidence),
                    self._json_dumps(serialized.get("warnings", [])),
                    self._json_dumps(serialized.get("blocking_failures", [])),
                    evidence.get("normalized_result_artifact_path"),
                    created_at,
                ),
            )

        return self.get_decision_result(decision_id)

    def get_decision_result(self, decision_id: str) -> Optional[dict]:
        """Get a decision result by ID."""
        row = fetch_one(
            "SELECT * FROM decision_results WHERE id = ?",
            (decision_id,),
        )
        return self.deserialize_decision(row) if row else None

    def get_latest_decision_for_run(self, run_id: str) -> Optional[dict]:
        """Get the newest decision result for a run."""
        row = fetch_one(
            """
            SELECT * FROM decision_results
            WHERE run_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (run_id,),
        )
        return self.deserialize_decision(row) if row else None

    def list_decisions_for_run(self, run_id: str, limit: int = 20) -> list[dict]:
        """List recent decision results for a run."""
        normalized_limit = self._normalize_limit(limit, default=20, max_value=200)
        rows = fetch_all(
            """
            SELECT * FROM decision_results
            WHERE run_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (run_id, normalized_limit),
        )
        return [self.deserialize_decision(row) for row in rows]

    def delete_decisions_for_run(self, run_id: str) -> int:
        """Delete all decision results for a run and return deleted count."""
        with transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM decision_results WHERE run_id = ?",
                (run_id,),
            )
            return cursor.rowcount

    def serialize_decision(self, result: DecisionResult | dict) -> dict:
        """Convert a DecisionResult or dict to a sanitized persistence dict."""
        if isinstance(result, DecisionResult):
            if hasattr(result, "model_dump"):
                data = result.model_dump()
            else:
                data = result.dict()
        else:
            data = dict(result)

        self._validate_decision_payload(data)
        return self._sanitize_secret_like(data)

    def deserialize_decision(self, row: dict) -> dict:
        """Deserialize a decision_results row into API-friendly dictionaries."""
        decision = self._json_loads(row.get("decision_json"), default={}) or {}
        decision["id"] = row["id"]
        decision["run_id"] = row["run_id"]
        decision["classification"] = row["classification"]
        decision["confidence_score"] = row.get("confidence_score")
        decision["policy_name"] = row["policy_name"]
        decision["risk_profile"] = row.get("risk_profile")
        decision["timeframe"] = row.get("timeframe")
        decision["gates"] = self._json_loads(row.get("gates_json"), default=[])
        decision["reasons"] = self._json_loads(row.get("reasons_json"), default=[])
        decision["evidence"] = self._json_loads(row.get("evidence_json"), default={})
        decision["warnings"] = self._json_loads(row.get("warnings_json"), default=[])
        decision["blocking_failures"] = self._json_loads(
            row.get("blocking_failures_json"),
            default=[],
        )
        decision["normalized_result_artifact_path"] = row.get(
            "normalized_result_artifact_path"
        )
        decision["created_at"] = row["created_at"]
        return decision

    def _validate_decision_payload(self, data: dict[str, Any]) -> None:
        """Validate persistence-level enum values."""
        self._require_allowed(
            data.get("classification"),
            DECISION_CLASSIFICATIONS,
            "decision classification",
        )
        self._require_allowed(
            data.get("policy_name"),
            DECISION_POLICY_NAMES,
            "decision policy name",
        )

        for gate in data.get("gates") or []:
            self._require_allowed(
                gate.get("status"),
                DECISION_GATE_STATUSES,
                "decision gate status",
            )
            self._require_allowed(
                gate.get("severity"),
                DECISION_REASON_SEVERITIES,
                "decision gate severity",
            )

        for reason in data.get("reasons") or []:
            self._require_allowed(
                reason.get("severity"),
                DECISION_REASON_SEVERITIES,
                "decision reason severity",
            )
