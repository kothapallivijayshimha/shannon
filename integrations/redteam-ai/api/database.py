from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import struct
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from llm.config import LLMConfig

logger = logging.getLogger("IntelStore")


@dataclass
class IntelRecord:
    target: str
    category: str  # RECON, VULN, SIM, STRATEGY
    data: dict[str, Any]
    timestamp: str | None = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class IntelligenceDatabase:
    """
    The Sovereign Memory Layer.
    Persists all red team findings to a local SQLite database for
    cross-target analysis and historical tracking.
    """

    def __init__(self, db_path: str = "redteam_intel.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT,
                    data TEXT,
                    timestamp TEXT
                )''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vulnerabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT,
                    severity TEXT,
                    finding TEXT,
                    evidence TEXT,
                    timestamp TEXT
                )''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attack_paths (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT,
                    chain TEXT,
                    risk_level TEXT,
                    timestamp TEXT
                )''')
            conn.commit()
        logger.info(f"Sovereign Intelligence Database initialized at {self.db_path}")

    def store_recon(self, target: str, data: dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO assets (target, data, timestamp) VALUES (?, ?, ?)",
                (target, json.dumps(data), datetime.now().isoformat()),
            )
            conn.commit()

    def store_vulnerability(self, target: str, severity: str, finding: str, evidence: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO vulnerabilities (target, severity, finding, evidence, timestamp) VALUES (?, ?, ?, ?, ?)",
                (target, severity, finding, evidence, datetime.now().isoformat()),
            )
            conn.commit()

    def store_attack_path(self, target: str, chain: list[str], risk: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO attack_paths (target, chain, risk_level, timestamp) VALUES (?, ?, ?, ?)",
                (target, json.dumps(chain), risk, datetime.now().isoformat()),
            )
            conn.commit()

    def get_history(self, target: str) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data FROM assets WHERE target = ? ORDER BY timestamp DESC LIMIT 1",
                (target,),
            )
            asset_row = cursor.fetchone()
            cursor.execute(
                "SELECT severity, finding FROM vulnerabilities WHERE target = ?", (target,)
            )
            vulns = cursor.fetchall()
            cursor.execute(
                "SELECT chain FROM attack_paths WHERE target = ?", (target,)
            )
            paths = cursor.fetchall()
            return {
                "last_assets": json.loads(asset_row[0]) if asset_row else None,
                "vulns": [{"severity": v[0], "finding": v[1]} for v in vulns],
                "paths": [json.loads(p[0]) for p in paths],
            }


# ---------------------------------------------------------------------------
# Episodic Memory System
# ---------------------------------------------------------------------------


class MemoryDatabase:
    """Full episodic memory with conversation storage and embedding-based retrieval.

    Tables:
      conversations — per-session chat history (user, assistant, tool turns)
      episodic_memory — reasoning traces + tool results for each assessment step
      embeddings_cache — cached embedding vectors keyed by text hash
    """

    def __init__(self, db_path: str = "memory.db", llm_config: LLMConfig | None = None) -> None:
        self.db_path = db_path
        self._config = llm_config or LLMConfig.from_env()
        self._init_db()

    # ---- schema ---------------------------------------------------------

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_name TEXT,
                    tool_result TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_conv_session
                    ON conversations(session_id);

                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    phase TEXT,
                    reasoning TEXT NOT NULL,
                    tool_name TEXT,
                    tool_result TEXT,
                    embedding BLOB,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_memory_target
                    ON episodic_memory(target);

                CREATE TABLE IF NOT EXISTS embeddings_cache (
                    text_hash TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
            """)
            conn.commit()
        logger.info(f"MemoryDatabase initialized at {self.db_path}")

    # ---- conversations --------------------------------------------------

    async def store_conversation_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_result: str | None = None,
    ) -> None:
        import uuid

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT COALESCE(MAX(turn_number), 0) + 1 FROM conversations WHERE session_id = ?", (session_id,))
            turn = c.fetchone()[0]
            c.execute(
                """INSERT INTO conversations
                   (id, session_id, turn_number, role, content, tool_name, tool_result, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    session_id,
                    turn,
                    role,
                    content,
                    tool_name,
                    tool_result,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    async def get_session_history(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """SELECT turn_number, role, content, tool_name
                   FROM conversations
                   WHERE session_id = ?
                   ORDER BY turn_number ASC
                   LIMIT ?""",
                (session_id, limit),
            )
            return [
                {
                    "turn": row[0],
                    "role": row[1],
                    "content": row[2],
                    "tool_name": row[3],
                }
                for row in c.fetchall()
            ]

    # ---- episodic memory ------------------------------------------------

    async def store_episode(
        self,
        session_id: str,
        target: str,
        phase: str,
        reasoning: str,
        tool_name: str,
        tool_result: str,
    ) -> None:
        import uuid

        embedding = await self._compute_embedding(reasoning)
        embedding_blob = _pack_embedding(embedding) if embedding else None

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """INSERT INTO episodic_memory
                   (id, session_id, target, phase, reasoning, tool_name, tool_result, embedding)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    session_id,
                    target,
                    phase,
                    reasoning[:5000],
                    tool_name,
                    tool_result[:5000] if tool_result else "",
                    embedding_blob,
                ),
            )
            conn.commit()

    async def get_episodes_for_target(self, target: str, limit: int = 10) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """SELECT session_id, target, phase, reasoning, tool_name, created_at
                   FROM episodic_memory
                   WHERE target = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (target, limit),
            )
            return [
                {
                    "session_id": row[0],
                    "target": row[1],
                    "phase": row[2],
                    "reasoning": row[3][:1000],
                    "tool_name": row[4],
                    "created_at": row[5],
                }
                for row in c.fetchall()
            ]

    async def search_memory(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search episodic memory by embedding similarity or keyword fallback."""
        query_embedding = await self._compute_embedding(query)
        if query_embedding:
            return await self._search_by_embedding(query_embedding, limit)

        return await self._search_by_keyword(query, limit)

    # ---- embedding helpers ----------------------------------------------

    async def _compute_embedding(self, text: str) -> list[float] | None:
        """Compute an embedding vector, using cache if available."""
        if not text.strip():
            return None

        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Check cache
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT embedding FROM embeddings_cache WHERE text_hash = ?",
                (text_hash,),
            )
            row = c.fetchone()
            if row:
                return _unpack_embedding(row[0])

        # Compute via OpenAI (Anthropic fallback not supported)
        try:
            from llm import get_llm_client
            client = get_llm_client(self._config)
            embedding = await client.embed(text)
        except (ImportError, NotImplementedError):
            return None
        except Exception:
            logger.exception("Embedding computation failed")
            return None

        # Cache it
        if embedding:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT OR REPLACE INTO embeddings_cache (text_hash, embedding, model) VALUES (?, ?, ?)",
                    (text_hash, _pack_embedding(embedding), self._config.openai_embedding_model),
                )
                conn.commit()

        return embedding

    async def _search_by_embedding(
        self, query_emb: list[float], limit: int
    ) -> list[dict[str, Any]]:
        """Cosine similarity search over stored embeddings (brute force, ok for small DB)."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT session_id, target, phase, reasoning, tool_name, created_at, embedding "
                "FROM episodic_memory WHERE embedding IS NOT NULL "
                "ORDER BY created_at DESC LIMIT 200"
            )
            rows = c.fetchall()

        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            stored_emb = _unpack_embedding(row[6])
            if stored_emb:
                sim = _cosine_similarity(query_emb, stored_emb)
                scored.append((
                    sim,
                    {
                        "session_id": row[0],
                        "target": row[1],
                        "phase": row[2],
                        "reasoning": row[3][:1000],
                        "tool_name": row[4],
                        "created_at": row[5],
                        "similarity": round(sim, 4),
                    },
                ))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    async def _search_by_keyword(self, query: str, limit: int) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            like = f"%{query}%"
            c.execute(
                """SELECT session_id, target, phase, reasoning, tool_name, created_at
                   FROM episodic_memory
                   WHERE reasoning LIKE ? OR target LIKE ? OR tool_name LIKE ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (like, like, like, limit),
            )
            return [
                {
                    "session_id": row[0],
                    "target": row[1],
                    "phase": row[2],
                    "reasoning": row[3][:1000],
                    "tool_name": row[4],
                    "created_at": row[5],
                }
                for row in c.fetchall()
            ]


# ---------------------------------------------------------------------------
# Embedding serialisation helpers
# ---------------------------------------------------------------------------


def _pack_embedding(vec: list[float]) -> bytes:
    """Pack a list of floats into compact binary."""
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack_embedding(data: bytes) -> list[float]:
    """Unpack binary back into a list of floats."""
    return list(struct.unpack(f"{len(data) // 4}f", data))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)




# ---------------------------------------------------------------------------
# Standalone helpers (used by orchestrator)
# ---------------------------------------------------------------------------


class AuthzDatabase:
    """Manages authorized targets with scope and expiry."""

    def __init__(self, db_path: str = "authz.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS authorized_targets (
                    id TEXT PRIMARY KEY,
                    target TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    phases TEXT DEFAULT '*',
                    tools TEXT DEFAULT '*',
                    expires_at TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    created_by TEXT DEFAULT 'admin'
                );
                CREATE INDEX IF NOT EXISTS idx_authz_target
                    ON authorized_targets(target);
            """)
            conn.commit()
        logger.info(f"AuthzDatabase initialized at {self.db_path}")

    def add_target(self, target: str, description: str = "",
                   phases: str = "*", tools: str = "*",
                   expires_at: str | None = None,
                   created_by: str = "admin") -> dict:
        import uuid
        record_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """INSERT INTO authorized_targets
                   (id, target, description, phases, tools, expires_at, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (record_id, target, description, phases, tools, expires_at, created_by),
            )
            conn.commit()
        return {"id": record_id, "target": target, "phases": phases, "tools": tools}

    def remove_target(self, target: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM authorized_targets WHERE target = ?", (target,))
            deleted = c.rowcount
            conn.commit()
        return deleted > 0

    def remove_by_id(self, record_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM authorized_targets WHERE id = ?", (record_id,))
            deleted = c.rowcount
            conn.commit()
        return deleted > 0

    def is_authorized(self, target: str, phase: str | None = None,
                      tool_name: str | None = None) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT phases, tools, expires_at FROM authorized_targets WHERE target = ?",
                (target,),
            )
            row = c.fetchone()
        if not row:
            return False

        phases, tools, expires_at = row

        # Check expiry
        if expires_at:
            try:
                from datetime import datetime as dt
                if dt.now().isoformat() > expires_at:
                    return False
            except Exception:
                pass

        # Check phase scope
        if phase and phases != "*":
            allowed = [p.strip() for p in phases.split(",")]
            if phase not in allowed:
                return False

        # Check tool scope
        if tool_name and tools != "*":
            allowed = [t.strip() for t in tools.split(",")]
            if tool_name not in allowed:
                return False

        return True

    def list_targets(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, target, description, phases, tools, expires_at, created_at, created_by "
                "FROM authorized_targets ORDER BY created_at DESC"
            )
            return [
                {
                    "id": row[0],
                    "target": row[1],
                    "description": row[2],
                    "phases": row[3],
                    "tools": row[4],
                    "expires_at": row[5],
                    "created_at": row[6],
                    "created_by": row[7],
                }
                for row in c.fetchall()
            ]


# ---------------------------------------------------------------------------
# Audit Database
# ---------------------------------------------------------------------------


class AuditDatabase:
    """Tamper-evident audit log with SHA-256 chain hashing."""

    def __init__(self, db_path: str = "audit.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT NOT NULL,
                    target TEXT NOT NULL,
                    phase TEXT,
                    user TEXT DEFAULT 'agent',
                    session_id TEXT,
                    command TEXT,
                    exit_code INTEGER,
                    success INTEGER,
                    result_summary TEXT,
                    chain_hash TEXT NOT NULL,
                    previous_hash TEXT,
                    timestamp TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_audit_target
                    ON audit_log(target);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                    ON audit_log(timestamp);
            """)
            conn.commit()
        logger.info(f"AuditDatabase initialized at {self.db_path}")

    def log(self, tool_name: str, target: str, phase: str | None = None,
            user: str = "agent", session_id: str | None = None,
            command: str = "", exit_code: int = -1, success: bool = False,
            result_summary: str = "") -> dict:
        import hashlib

        # Get previous hash for chain
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT chain_hash FROM audit_log ORDER BY id DESC LIMIT 1")
            prev = c.fetchone()
            previous_hash = prev[0] if prev else ""

        # Build chain entry
        entry = f"{tool_name}|{target}|{phase}|{exit_code}|{success}|{previous_hash}"
        chain_hash = hashlib.sha256(entry.encode()).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """INSERT INTO audit_log
                   (tool_name, target, phase, user, session_id, command,
                    exit_code, success, result_summary, chain_hash, previous_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tool_name, target, phase, user, session_id, command,
                 exit_code, 1 if success else 0, result_summary[:2000],
                 chain_hash, previous_hash),
            )
            conn.commit()

        return {"id": c.lastrowid, "chain_hash": chain_hash, "previous_hash": previous_hash}

    def query(self, target: str | None = None, tool_name: str | None = None,
              limit: int = 100, offset: int = 0) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            where = []
            params = []
            if target:
                where.append("target = ?")
                params.append(target)
            if tool_name:
                where.append("tool_name = ?")
                params.append(tool_name)

            query = "SELECT * FROM audit_log"
            if where:
                query += " WHERE " + " AND ".join(where)
            query += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            c.execute(query, params)
            return [
                {
                    "id": row[0],
                    "tool_name": row[1],
                    "target": row[2],
                    "phase": row[3],
                    "user": row[4],
                    "session_id": row[5],
                    "command": row[6],
                    "exit_code": row[7],
                    "success": bool(row[8]),
                    "result_summary": row[9],
                    "chain_hash": row[10],
                    "previous_hash": row[11],
                    "timestamp": row[12],
                }
                for row in c.fetchall()
            ]

    def verify_chain(self) -> bool:
        """Verify the integrity of the audit chain."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT id, tool_name, target, phase, exit_code, success, "
                      "chain_hash, previous_hash FROM audit_log ORDER BY id ASC")
            rows = c.fetchall()

        prev_hash = ""
        for row in rows:
            entry = f"{row[1]}|{row[2]}|{row[3]}|{row[4]}|{row[5]}|{prev_hash}"
            expected = hashlib.sha256(entry.encode()).hexdigest()
            if expected != row[6]:
                return False
            if row[7] != prev_hash:
                return False
            prev_hash = row[6]
        return True


# ---------------------------------------------------------------------------
# Detection Database
# ---------------------------------------------------------------------------


class DetectionDatabase:
    """Stores detection events from the DetectionEngine."""

    def __init__(self, db_path: str = "detection.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS detection_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    severity TEXT DEFAULT 'info',
                    source TEXT,
                    details TEXT,
                    raw_data TEXT,
                    interface TEXT,
                    timestamp TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_detection_type
                    ON detection_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_detection_severity
                    ON detection_events(severity);
                CREATE INDEX IF NOT EXISTS idx_detection_ts
                    ON detection_events(timestamp);
            """)
            conn.commit()
        logger.info(f"DetectionDatabase initialized at {self.db_path}")

    def store_event(self, event_type: str, severity: str = "info",
                    source: str = "", details: str = "",
                    raw_data: str = "", interface: str = "") -> dict:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """INSERT INTO detection_events
                   (event_type, severity, source, details, raw_data, interface)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (event_type, severity, source, details[:2000], raw_data[:5000], interface),
            )
            conn.commit()
            return {"id": c.lastrowid, "event_type": event_type, "severity": severity}

    def query(self, event_type: str | None = None, severity: str | None = None,
              limit: int = 100, offset: int = 0) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            where = []
            params = []
            if event_type:
                where.append("event_type = ?")
                params.append(event_type)
            if severity:
                where.append("severity = ?")
                params.append(severity)

            query = "SELECT * FROM detection_events"
            if where:
                query += " WHERE " + " AND ".join(where)
            query += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            c.execute(query, params)
            return [
                {
                    "id": row[0],
                    "event_type": row[1],
                    "severity": row[2],
                    "source": row[3],
                    "details": row[4],
                    "raw_data": row[5],
                    "interface": row[6],
                    "timestamp": row[7],
                }
                for row in c.fetchall()
            ]


# Global instances
db = IntelligenceDatabase()
memory_db = MemoryDatabase()
authz_db = AuthzDatabase()
audit_db = AuditDatabase()
detection_db = DetectionDatabase()


# ---------------------------------------------------------------------------
# Standalone helpers (used by orchestrator)
# ---------------------------------------------------------------------------

def save_phase_result(domain: str, phase: str, status: str, result: dict) -> None:
    """Persist a phase result to the assessment_results table for history."""
    try:
        with sqlite3.connect("results.db") as conn:
            c = conn.cursor()
            c.execute(
                """CREATE TABLE IF NOT EXISTS phase_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT, phase TEXT, status TEXT,
                    result_json TEXT, created_at TEXT
                )"""
            )
            c.execute(
                "INSERT INTO phase_results (domain, phase, status, result_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (domain, phase, status, json.dumps(result, default=str), datetime.utcnow().isoformat()),
            )
            conn.commit()
    except Exception:
        logger.exception("Failed to save phase result")


def get_phase_results(domain: str) -> dict[str, Any]:
    """Retrieve all phase results for a given domain."""
    try:
        with sqlite3.connect("results.db") as conn:
            c = conn.cursor()
            c.execute(
                """CREATE TABLE IF NOT EXISTS phase_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT, phase TEXT, status TEXT,
                    result_json TEXT, created_at TEXT
                )"""
            )
            c.execute(
                "SELECT phase, result_json FROM phase_results WHERE domain = ? ORDER BY created_at ASC",
                (domain,),
            )
            rows = c.fetchall()
            return {row[0]: json.loads(row[1]) for row in rows}
    except Exception:
        logger.exception("Failed to load phase results")
        return {}

