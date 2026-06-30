"""
Repository for Part 13 validation evidence persistence.
"""
from __future__ import annotations

from typing import Any, Optional

from app.core.constants import (
    VALIDATION_DECISION_STATUSES,
    VALIDATION_EVIDENCE_TYPES,
    VALIDATION_SOURCE_TYPES,
    VALIDATION_STATUSES,
)
from app.db.sqlite import fetch_all, fetch_one, transaction
from app.repositories.base import BaseRepository


class ValidationRepository(BaseRepository):
    """Repository for validation_runs and validation_evidence tables."""

    RUN_JSON_FIELDS = {
        "pairs": "pairs_json",
        "wfo_config": "wfo_config_json",
        "policy": "policy_json",
        "request": "request_json",
        "decision": "decision_json",
        "summary": "summary_json",
    }
    EVIDENCE_JSON_FIELDS = {
        "metrics": "metrics_json",
        "decision": "decision_json",
        "issues": "issues_json",
        "warnings": "warnings_json",
        "artifact_paths": "artifact_paths_json",
    }

    def create_validation_run(self, run_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a validation run record.

        This only persists metadata. It does not run validation or Freqtrade.
        """
        source_type = run_data["source_type"]
        status = run_data.get("status", "pending")
        decision_status = run_data.get("decision_status", "not_validated")
        self._require_allowed(source_type, VALIDATION_SOURCE_TYPES, "validation source_type")
        self._require_allowed(status, VALIDATION_STATUSES, "validation status")
        if decision_status is not None:
            self._require_allowed(
                decision_status,
                VALIDATION_DECISION_STATUSES,
                "validation decision_status",
            )

        run_id = run_data.get("id") or self._uuid()
        now = run_data.get("created_at") or self._now()
        updated_at = run_data.get("updated_at") or now

        pairs = run_data.get("pairs")
        if not pairs:
            raise ValueError("pairs must be non-empty")

        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO validation_runs (
                    id, source_type, source_run_id, strategy_name, timeframe,
                    pairs_json, exchange, risk_profile, status, decision_status,
                    timerange, oos_timerange, wfo_config_json, policy_json,
                    request_json, decision_json, summary_json, report_artifact_path,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    source_type,
                    run_data.get("source_run_id"),
                    run_data["strategy_name"],
                    run_data["timeframe"],
                    self._json_dumps(pairs),
                    run_data.get("exchange", "binance"),
                    run_data.get("risk_profile"),
                    status,
                    decision_status,
                    run_data.get("timerange"),
                    run_data.get("oos_timerange"),
                    self._json_dumps(run_data.get("wfo_config")) if run_data.get("wfo_config") is not None else None,
                    self._json_dumps(run_data.get("policy")) if run_data.get("policy") is not None else None,
                    self._json_dumps(run_data.get("request")) if run_data.get("request") is not None else None,
                    self._json_dumps(run_data.get("decision")) if run_data.get("decision") is not None else None,
                    self._json_dumps(run_data.get("summary")) if run_data.get("summary") is not None else None,
                    run_data.get("report_artifact_path"),
                    now,
                    updated_at,
                ),
            )

        return self.get_validation_run(run_id)

    def update_validation_run(
        self,
        validation_run_id: str,
        updates: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Update a validation run record."""
        if not updates:
            return self.get_validation_run(validation_run_id)

        update_fields = []
        values = []
        for field, value in updates.items():
            if field == "source_type":
                self._require_allowed(value, VALIDATION_SOURCE_TYPES, "validation source_type")
                update_fields.append("source_type = ?")
                values.append(value)
            elif field == "status":
                self._require_allowed(value, VALIDATION_STATUSES, "validation status")
                update_fields.append("status = ?")
                values.append(value)
            elif field == "decision_status":
                if value is not None:
                    self._require_allowed(
                        value,
                        VALIDATION_DECISION_STATUSES,
                        "validation decision_status",
                    )
                update_fields.append("decision_status = ?")
                values.append(value)
            elif field in {
                "source_run_id",
                "strategy_name",
                "timeframe",
                "exchange",
                "risk_profile",
                "timerange",
                "oos_timerange",
                "report_artifact_path",
            }:
                update_fields.append(f"{field} = ?")
                values.append(value)
            elif field in self.RUN_JSON_FIELDS:
                update_fields.append(f"{self.RUN_JSON_FIELDS[field]} = ?")
                values.append(self._json_dumps(value) if value is not None else None)

        if not update_fields:
            return self.get_validation_run(validation_run_id)

        update_fields.append("updated_at = ?")
        values.append(self._now())
        values.append(validation_run_id)

        with transaction() as conn:
            conn.execute(
                f"UPDATE validation_runs SET {', '.join(update_fields)} WHERE id = ?",
                tuple(values),
            )

        return self.get_validation_run(validation_run_id)

    def get_validation_run(self, validation_run_id: str) -> Optional[dict[str, Any]]:
        """Get a validation run by ID."""
        row = fetch_one(
            "SELECT * FROM validation_runs WHERE id = ?",
            (validation_run_id,),
        )
        return self.serialize_run(row) if row else None

    def list_validation_runs(
        self,
        strategy_name: Optional[str] = None,
        status: Optional[str] = None,
        decision_status: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List validation runs with optional filters."""
        normalized_limit = self._normalize_limit(limit, default=50, max_value=500)
        conditions = []
        params: list[Any] = []

        if strategy_name:
            conditions.append("strategy_name = ?")
            params.append(strategy_name)
        if status:
            self._require_allowed(status, VALIDATION_STATUSES, "validation status")
            conditions.append("status = ?")
            params.append(status)
        if decision_status:
            self._require_allowed(
                decision_status,
                VALIDATION_DECISION_STATUSES,
                "validation decision_status",
            )
            conditions.append("decision_status = ?")
            params.append(decision_status)
        if source_type:
            self._require_allowed(source_type, VALIDATION_SOURCE_TYPES, "validation source_type")
            conditions.append("source_type = ?")
            params.append(source_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([normalized_limit, offset])

        rows = fetch_all(
            f"""
            SELECT * FROM validation_runs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )
        return [self.serialize_run(row) for row in rows]

    def create_evidence(self, evidence_data: dict[str, Any]) -> dict[str, Any]:
        """Create one validation evidence record."""
        evidence_id = evidence_data.get("id") or self._uuid()
        evidence_type = evidence_data["evidence_type"]
        status = evidence_data["status"]
        self._require_allowed(evidence_type, VALIDATION_EVIDENCE_TYPES, "validation evidence_type")
        if status not in VALIDATION_STATUSES and status not in VALIDATION_DECISION_STATUSES:
            raise ValueError(
                "Invalid validation evidence status: "
                f"'{status}'. Allowed values: {', '.join(VALIDATION_STATUSES + VALIDATION_DECISION_STATUSES)}"
            )

        now = evidence_data.get("created_at") or self._now()

        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO validation_evidence (
                    id, validation_run_id, evidence_type, status, window_index,
                    timerange, metrics_json, decision_json, issues_json,
                    warnings_json, artifact_paths_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    evidence_data["validation_run_id"],
                    evidence_type,
                    status,
                    evidence_data.get("window_index"),
                    evidence_data.get("timerange"),
                    self._json_dumps(evidence_data.get("metrics")) if evidence_data.get("metrics") is not None else None,
                    self._json_dumps(evidence_data.get("decision")) if evidence_data.get("decision") is not None else None,
                    self._json_dumps(evidence_data.get("issues")) if evidence_data.get("issues") is not None else None,
                    self._json_dumps(evidence_data.get("warnings")) if evidence_data.get("warnings") is not None else None,
                    self._json_dumps(evidence_data.get("artifact_paths")) if evidence_data.get("artifact_paths") is not None else None,
                    now,
                ),
            )

        return self.get_evidence(evidence_id)

    def bulk_create_evidence(self, evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create multiple validation evidence records."""
        created = []
        for evidence_data in evidence_items:
            created.append(self.create_evidence(evidence_data))
        return created

    def list_evidence(
        self,
        validation_run_id: str,
        evidence_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List evidence records for a validation run."""
        conditions = ["validation_run_id = ?"]
        params: list[Any] = [validation_run_id]

        if evidence_type:
            self._require_allowed(evidence_type, VALIDATION_EVIDENCE_TYPES, "validation evidence_type")
            conditions.append("evidence_type = ?")
            params.append(evidence_type)
        if status:
            if status not in VALIDATION_STATUSES and status not in VALIDATION_DECISION_STATUSES:
                raise ValueError("status must be a known validation status")
            conditions.append("status = ?")
            params.append(status)

        rows = fetch_all(
            f"""
            SELECT * FROM validation_evidence
            WHERE {' AND '.join(conditions)}
            ORDER BY
                CASE WHEN window_index IS NULL THEN 1 ELSE 0 END,
                window_index ASC,
                created_at ASC
            """,
            tuple(params),
        )
        return [self.serialize_evidence(row) for row in rows]

    def get_evidence(self, evidence_id: str) -> Optional[dict[str, Any]]:
        """Get an evidence record by ID."""
        row = fetch_one(
            "SELECT * FROM validation_evidence WHERE id = ?",
            (evidence_id,),
        )
        return self.serialize_evidence(row) if row else None

    def save_decision(
        self,
        validation_run_id: str,
        decision: dict[str, Any],
        decision_status: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Persist the aggregate validation decision on validation_runs."""
        resolved_status = decision_status or decision.get("decision_status")
        if not resolved_status:
            raise ValueError("decision_status is required")
        self._require_allowed(
            resolved_status,
            VALIDATION_DECISION_STATUSES,
            "validation decision_status",
        )
        return self.update_validation_run(
            validation_run_id,
            {
                "decision_status": resolved_status,
                "decision": decision,
            },
        )

    def get_decision(self, validation_run_id: str) -> Optional[dict[str, Any]]:
        """Return the aggregate validation decision payload for a run."""
        run = self.get_validation_run(validation_run_id)
        if not run:
            return None
        return run.get("decision")

    def serialize_run(self, row: dict[str, Any]) -> dict[str, Any]:
        """Deserialize a validation_runs row into an API-friendly dictionary."""
        result = dict(row)
        result["pairs"] = self._json_loads(result.pop("pairs_json", None), default=[])
        result["wfo_config"] = self._json_loads(result.pop("wfo_config_json", None), default=None)
        result["policy"] = self._json_loads(result.pop("policy_json", None), default=None)
        result["request"] = self._json_loads(result.pop("request_json", None), default=None)
        result["decision"] = self._json_loads(result.pop("decision_json", None), default=None)
        result["summary"] = self._json_loads(result.pop("summary_json", None), default=None)
        return result

    def serialize_evidence(self, row: dict[str, Any]) -> dict[str, Any]:
        """Deserialize a validation_evidence row into an API-friendly dictionary."""
        result = dict(row)
        result["metrics"] = self._json_loads(result.pop("metrics_json", None), default={})
        result["decision"] = self._json_loads(result.pop("decision_json", None), default={})
        result["issues"] = self._json_loads(result.pop("issues_json", None), default=[])
        result["warnings"] = self._json_loads(result.pop("warnings_json", None), default=[])
        result["artifact_paths"] = self._json_loads(
            result.pop("artifact_paths_json", None),
            default=[],
        )
        return result
