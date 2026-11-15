"""Local retrieval-augmented support for the NASA health-monitoring demo."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import sqlite3
import socket
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import chromadb
import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_DIR = os.path.join(PROJECT_ROOT, "knowledge_base")
CHROMA_PATH = os.environ.get(
    "CHROMA_DB_PATH", os.path.join(PROJECT_ROOT, "chroma_db")
)
CHROMA_COLLECTION = "nasa_hrp_knowledge"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_EMBEDDING_MODEL = os.environ.get(
    "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest"
)
TELEMETRY_DB_PATH = Path(PROJECT_ROOT) / "data" / "mission_telemetry.db"
LOCAL_HASH_DIMENSIONS = 384
STATUS_COLORS = {
    "No Data": "#8b9aaa",
    "Green": "#00e676",
    "Amber": "#ffab00",
    "Red": "#ff1744",
}
COUNTERMEASURE_NAMES = {
    "Water-Wall Shelter (design concept)",
    "ARED Resistance Protocol (+30 min)",
    "Thigh Cuff & Fluid Load",
    "Circadian Blue-Light Reset",
}

NASA_BONE_SOURCE = {
    "title": "NASA HRP — Risk of Spaceflight-Induced Bone Changes",
    "url": "https://www.nasa.gov/reference/risk-of-spaceflight-induced-bone-changes/",
}
CSA_RADI_N2_SOURCE = {
    "title": "Canadian Space Agency — Radi-N2: Tracking space radiation and its risks",
    "url": "https://www.asc-csa.gc.ca/eng/sciences/radi-n2.asp",
}

_PROJECT_RISK_TAGS = [
    "HRP-RED-SANS",
    "HRP-RED-BONE",
    "HRP-RED-BHPC",
    "HRP-RED-RAD",
    "HRP-MOD-CARDIO",
]
_PROJECT_TAG_SOURCE_URLS = {
    "HRP-RED-SANS": "https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans/",
    "HRP-RED-BONE": NASA_BONE_SOURCE["url"],
    "HRP-RED-BHPC": "https://www.nasa.gov/directorates/esdmd/hhp/behavioral-health-risk/",
    "HRP-RED-RAD": "https://www.nasa.gov/directorates/esdmd/hhp/space-radiation/",
    "HRP-MOD-CARDIO": "https://www.nasa.gov/directorates/esdmd/hhp/cv-risk/",
}

_SCENARIO_FIXTURES = [
    {
        "scenario_id": "iss_leo_baseline",
        "name": "ISS Low Earth Orbit",
        "mission_phase": "LEO",
        "scenario_type": "synthetic_design_fixture",
        "risk_tags": [
            "HRP-RED-SANS",
            "HRP-RED-BONE",
            "HRP-RED-BHPC",
            "HRP-RED-RAD",
            "HRP-MOD-CARDIO",
        ],
        "measurements": {
            "neutron_radiation_msv": {
                "value": 0.15,
                "evidence_status": "csa_radi_n2_empirical",
                "source": CSA_RADI_N2_SOURCE,
                "note": (
                    "CSA-reported early Radi-N2 neutron dose result. Repeated "
                    "as a constant scenario reference, not 14 daily observations "
                    "and not a total-dose rate."
                ),
            },
            "radiation_dose_rate_msv_day": {
                "value": None,
                "evidence_status": "not_available",
                "note": "No total/unspecified ISS dose-rate value is asserted.",
            },
            "cabin_co2_partial_pressure_mmhg": {
                "value": 2.8,
                "evidence_status": "synthetic_assumption",
                "note": (
                    "Synthetic fixture: 2.8 mmHg; not an EDA empirical "
                    "baseline."
                ),
            },
        },
        "verified_context": [
            {
                "claim": (
                    "CSA reports an early Radi-N2 neutron dose result of "
                    "about 150 µSv/day (0.15 mSv/day); it is neutron-only "
                    "and is not a total-dose rate or operational limit."
                ),
                "source": CSA_RADI_N2_SOURCE,
            }
        ],
        "risk_tag_notice": (
            "These are project-defined tags, not NASA-issued risk IDs or "
            "NASA severity classifications."
        ),
    },
    {
        "scenario_id": "artemis_lunar_spe",
        "name": "Artemis Lunar Solar Particle Event",
        "mission_phase": "lunar surface",
        "scenario_type": "synthetic_design_fixture",
        "risk_tags": ["HRP-RED-RAD", "HRP-MOD-CARDIO"],
        "measurements": {
            "radiation_spike_msv_day": {
                "value": 18.5,
                "particle_components": ["neutron", "proton"],
                "evidence_status": "synthetic_assumption",
                "note": (
                    "Project stress test (synthetic); not an Artemis "
                    "measurement, event baseline, forecast, alarm threshold, "
                    "or crew action criterion."
                ),
            }
        },
        "verified_context": [
            {
                "claim": (
                    "NASA describes space radiation and solar particle "
                    "events as human-spaceflight hazards and supports "
                    "mission-specific monitoring; no generic dose-rate "
                    "action threshold is provided here."
                ),
                "source": {
                    "title": "NASA Human Health and Performance — Space Radiation",
                    "url": "https://www.nasa.gov/directorates/esdmd/hhp/space-radiation/",
                },
            }
        ],
        "risk_tag_notice": (
            "These are project-defined tags, not NASA-issued risk IDs or "
            "NASA severity classifications."
        ),
    },
    {
        "scenario_id": "mars_surface_day_210",
        "name": "Day 210 Mars Transit Extrapolation",
        "mission_phase": "Mars surface",
        "mission_day": 210,
        "scenario_type": "synthetic_design_fixture",
        "risk_tags": _PROJECT_RISK_TAGS,
        "measurements": {
            "cumulative_bmd_change_percent": {
                "value": -8.4,
                "start_value": -7.8,
                "evidence_status": "synthetic_extrapolation",
                "note": (
                    "Synthetic 14-day interpolation from -7.8% on mission Day "
                    "197 to -8.4% on Day 210. NASA's published 1.0–1.5%/month "
                    "population average is context only; it does not validate "
                    "this daily trajectory or a Mars prediction."
                ),
            },
            "cabin_co2_partial_pressure_mmhg": {
                "value": 4.3,
                "evidence_status": "synthetic_assumption",
                "note": (
                    "Project stress test (synthetic): 4.3 mmHg on Day 210; "
                    "not a measured Mars habitat baseline or limit."
                ),
            },
            "plasma_volume_shift_percent_range": {
                "value": [10, 15],
                "evidence_status": "synthetic_assumption",
                "note": (
                    "Not verified as a NASA HRP empirical range in the "
                    "sources reviewed for this project."
                ),
            },
        },
        "verified_context": [
            {
                "claim": (
                    "NASA reports a population-average BMD loss of 1.0–1.5% "
                    "per month during four-to-six-month missions; that evidence "
                    "does not establish this synthetic Mars trajectory."
                ),
                "source": NASA_BONE_SOURCE,
            }
        ],
        "risk_tag_notice": (
            "These are project-defined tags, not NASA-issued risk IDs or "
            "NASA severity classifications."
        ),
    },
]

ENVIRONMENT_CONSTRAINTS = {
    "ISS (LEO - 0.5s Latency)": {
        "latency_label": "0.5s latency (demo profile)",
        "comms_state": "Near-real-time link profile; connectivity is not verified.",
        "measurement_feasibility": (
            "ISS demonstration profile: cabin CO2 monitoring, Radi-N2 bubble "
            "detectors, and ARED. Radi-N2 is passive/integrating, not a "
            "real-time SPE alarm; software does not verify instrument availability."
        ),
    },
    "Artemis Lunar Transit (~1.3s One-Way / ~2.6s Round-Trip)": {
        "latency_label": "Artemis Lunar Transit (~1.3s One-Way / ~2.6s Round-Trip)",
        "comms_state": "Delayed-communications profile; link is not verified.",
        "measurement_feasibility": (
            "Lunar Orion demonstration profile: portable dosimeter, cuff/finger "
            "pulse-ox, and Amsler grid. This software does not verify vehicle "
            "installation, availability, or telemetry."
        ),
    },
    "Mars Surface Base (Up to ~22-Min One-Way / ~44-Min Round-Trip)": {
        "latency_label": (
            "Mars Surface Base (Up to ~22-Min One-Way / ~44-Min Round-Trip)"
        ),
        "comms_state": (
            "Delayed or unavailable ground consultation profile; actual "
            "communications are not simulated or verified."
        ),
        "measurement_feasibility": (
            "Mars habitat demonstration profile: habitat environmental loop, "
            "portable ultrasound/tonometer, and dosimeter. This software does "
            "not verify vehicle installation, availability, or telemetry."
        ),
    },
}


def environment_constraints(environment_mode: str) -> dict[str, str]:
    """Return descriptive demo-profile comms and measurement constraints."""
    try:
        return dict(ENVIRONMENT_CONSTRAINTS[environment_mode])
    except KeyError as exc:
        raise ValueError(f"Unknown environment_mode: {environment_mode}") from exc


def compute_demo_readiness(systems: dict[str, dict[str, Any]]) -> float:
    """Compute a non-clinical demo score; unknown systems do not reduce it."""
    deductions = {"No Data": 0, "Green": 0, "Amber": 20, "Red": 50}
    unknown = {
        system.get("status")
        for system in systems.values()
        if system.get("status") not in deductions
    }
    if unknown:
        raise ValueError(f"Unknown health-system statuses: {sorted(unknown)}")
    return float(
        max(
            0,
            100
            - sum(deductions[system["status"]] for system in systems.values()),
        )
    )


def _ollama_reachable(base_url: str, timeout: float = 0.5) -> bool:
    """Check the local Ollama TCP endpoint without waiting for HTTP timeouts."""
    try:
        parsed_url = urlsplit(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
            return False
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
        with socket.create_connection(
            (parsed_url.hostname, port), timeout=timeout
        ):
            return True
    except (OSError, ValueError):
        return False


class OllamaEmbeddingFunction:
    """Generate Chroma embeddings from the configured local Ollama server."""

    def __init__(
        self,
        model: str = OLLAMA_EMBEDDING_MODEL,
        base_url: str = OLLAMA_BASE_URL,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.last_backend: str | None = None

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        if not input:
            return []
        if not _ollama_reachable(self.base_url, timeout=0.25):
            self.last_backend = f"local-hash-{LOCAL_HASH_DIMENSIONS}-v1"
            return [_hash_embedding(text) for text in input]

        payload = json.dumps({"model": self.model, "input": list(input)}).encode(
            "utf-8"
        )
        request = Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=2) as response:
                body = json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama embedding request failed ({exc.code}): {detail}"
            ) from exc
        except (URLError, ConnectionError, TimeoutError):
            self.last_backend = f"local-hash-{LOCAL_HASH_DIMENSIONS}-v1"
            return [_hash_embedding(text) for text in input]

        embeddings = body.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(input):
            raise RuntimeError(
                f"Ollama returned {len(embeddings) if isinstance(embeddings, list) else 'no'} "
                f"embeddings for {len(input)} input texts."
            )
        self.last_backend = f"ollama:{self.model}"
        return embeddings


def _hash_embedding(text: str) -> list[float]:
    """Return a deterministic signed feature-hash vector using only stdlib."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    features = tokens + [
        f"{left}_{right}" for left, right in zip(tokens, tokens[1:])
    ]
    vector = [0.0] * LOCAL_HASH_DIMENSIONS
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=16).digest()
        index = int.from_bytes(digest[:8], "little") % LOCAL_HASH_DIMENSIONS
        vector[index] += 1.0 if digest[8] & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def seed_scenario() -> list[dict[str, Any]]:
    """Return the three named demo fixtures with provenance on each value."""
    return copy.deepcopy(_SCENARIO_FIXTURES)


def _client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=CHROMA_PATH)


def _collection() -> Any:
    return _client().get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )


def _sources_for_chunk(metadata: dict[str, Any]) -> list[dict[str, str]]:
    raw_sources = metadata.get("citations_json", "[]")
    sources = json.loads(raw_sources)
    if not isinstance(sources, list):
        raise RuntimeError("Invalid citation metadata in the Chroma collection.")
    return [
        source
        for source in sources
        if isinstance(source, dict)
        and isinstance(source.get("title"), str)
        and isinstance(source.get("url"), str)
    ]


def _relevant_sources(
    document: str, sources: list[dict[str, str]], limit: int = 4
) -> list[dict[str, str]]:
    stop_words = {
        "and",
        "the",
        "for",
        "from",
        "with",
        "risk",
        "risks",
        "nasa",
        "canadian",
        "human",
        "space",
        "spaceflight",
        "mission",
        "metadata",
        "changes",
        "hazard",
        "osd",
        "osdr",
        "study",
        "due",
        "associated",
    }
    document_accessions = {
        accession.upper()
        for accession in re.findall(r"\bOSD-\d+\b", document, re.IGNORECASE)
    }

    def terms(value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", value.lower())
            if len(token) > 2 and token not in stop_words
        }

    document_terms = terms(document)
    ranked = []
    for source in sources:
        source_accession = re.search(r"\bOSD-\d+\b", source["title"], re.IGNORECASE)
        if (
            source_accession
            and document_accessions
            and source_accession.group(0).upper() not in document_accessions
        ):
            continue
        title_terms = terms(source["title"])
        overlap = document_terms & title_terms
        if overlap:
            accession_match = bool(
                source_accession
                and source_accession.group(0).upper() in document_accessions
            )
            ranked.append((len(overlap) + (10 if accession_match else 0), source))
    ranked.sort(key=lambda item: (-item[0], item[1]["title"]))
    return [source for _, source in ranked[:limit]]


def _format_cited_output(
    answer: str, retrieved: list[dict[str, Any]]
) -> str:
    """Attach the exact retrieved references and evidence excerpts to an answer."""
    sources_by_url: dict[str, dict[str, str]] = {}
    for item in retrieved:
        item["sources"] = _relevant_sources(item["document"], item["sources"])
        for source in item["sources"]:
            sources_by_url.setdefault(source["url"], source)
    source_ids = {
        url: f"S{index}"
        for index, url in enumerate(sources_by_url, start=1)
    }

    lines = [answer.strip()]
    related_tags = [
        tag
        for tag in _PROJECT_RISK_TAGS
        if any(tag in item["document"] for item in retrieved)
    ]
    if related_tags:
        tag_mentions = []
        for tag in related_tags:
            citation_id = source_ids.get(_PROJECT_TAG_SOURCE_URLS[tag])
            mention = f"`{tag}`"
            if citation_id:
                mention += f" [{citation_id}]"
            tag_mentions.append(mention)
        lines.extend(
            [
                "",
                "**Related project-defined HRP tags:** "
                + ", ".join(tag_mentions)
                + ".",
                "These labels are not NASA-issued risk IDs or severity "
                "classifications; cited NASA pages describe the associated "
                "research risks, not these project labels.",
            ]
        )
    lines.extend(["", "### Retrieved evidence and citations"])
    for index, item in enumerate(retrieved, start=1):
        source_file = item["metadata"].get("source_file", "unknown source")
        section = item["metadata"].get("section", "document")
        excerpt = re.sub(r"\s+", " ", item["document"]).strip()
        if len(excerpt) > 360:
            excerpt = excerpt[:357].rstrip() + "..."
        citation_ids = [
            source_ids[source["url"]]
            for source in item["sources"]
            if source["url"] in source_ids
        ]
        reference = ", ".join(f"[{citation_id}]" for citation_id in citation_ids)
        if not reference:
            reference = f"`{source_file}` (no external URL recorded for this passage)"
        lines.append(
            f"{index}. **{source_file} — {section}:** “{excerpt}” {reference}"
        )

    if sources_by_url:
        lines.extend(["", "### References"])
        for url, citation_id in source_ids.items():
            source = sources_by_url[url]
            lines.append(f"- [{citation_id}] [{source['title']}]({url})")
    return "\n".join(lines)


def _offline_answer(
    question: str, retrieved: list[dict[str, Any]]
) -> str:
    """Build a clearly labeled extractive response when Ollama is unreachable."""
    lines = [
        "**Offline evidence summary**",
        "",
        "Ollama is unreachable; this extractive summary uses retrieved text only. "
        "It is not a clinical assessment or mission procedure.",
        "",
        f"**Question:** {question}",
    ]
    for item in retrieved:
        source_file = item["metadata"].get("source_file", "unknown source")
        section = item["metadata"].get("section", "document")
        excerpt = re.sub(r"\s+", " ", item["document"]).strip()
        if len(excerpt) > 500:
            excerpt = excerpt[:497].rstrip() + "..."
        lines.extend(["", f"- **{source_file} — {section}:** {excerpt}"])
        for source in item["sources"]:
            lines.append(f"  - Source: [{source['title']}]({source['url']})")
    return "\n".join(lines)


def _generate_answer(
    question: str,
    retrieved: list[dict[str, Any]],
    model: str,
    base_url: str,
) -> str:
    if not _ollama_reachable(base_url, timeout=0.25):
        return _offline_answer(question, retrieved)

    context_parts = []
    for index, item in enumerate(retrieved, start=1):
        citation_lines = "\n".join(
            f"- {source['title']}: {source['url']}"
            for source in item["sources"]
        )
        context_parts.append(
            f"[Evidence {index}: {item['metadata'].get('source_file', 'unknown')} "
            f"— {item['metadata'].get('section', 'document')}]\n"
            f"{item['document']}\n"
            f"Source candidates for this passage:\n"
            f"{citation_lines or '- No external URL recorded.'}"
        )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a source-grounded assistant for an educational "
                "spaceflight health-monitoring demo, not a flight surgeon. "
                "Do not diagnose, prescribe, set operational limits, or "
                "replace mission procedures. Answer only from the evidence "
                "provided. Cite factual claims with the exact source URL in "
                "Markdown when one is provided. Clearly label synthetic "
                "scenario values and project-defined risk tags; never "
                "present them as NASA/CSA findings. When an OSDR record is "
                "relevant, give its exact accession and preserve the study "
                "model/type (such as ground, animal, or ex-vivo); do not "
                "present those data as direct astronaut measurements. Cite "
                "NASA HRP risk pages and CSA Radi-N2/CANS separately when "
                "they support the relevant context. If the evidence does not "
                "support a claim, say that it is unverified."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question: {question}\n\n"
                "Retrieved knowledge:\n"
                + "\n\n".join(context_parts)
            ),
        },
    ]
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1},
        }
    ).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2) as response:
            body = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Ollama answer request failed ({exc.code}): {detail}"
        ) from exc
    except (URLError, ConnectionError, TimeoutError):
        return _offline_answer(question, retrieved)

    content = body.get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Ollama returned an empty answer.")
    return content.strip()


def _is_embedding_mismatch_error(error: RuntimeError) -> bool:
    """Identify only backend/dimension mismatches that ingestion can resolve."""
    message = str(error).lower()
    if "embedding backend" in message and "match" in message:
        return True
    return (
        "dimension" in message
        and ("embedding" in message or "vector" in message or "collection" in message)
    )


def query_flight_surgeon_copilot(
    question: str,
    top_k: int = 5,
    model: str | None = None,
) -> str:
    """Retrieve cited knowledge and produce a locally generated, caveated answer."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string.")
    if not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k must be a positive integer.")

    def retrieve() -> tuple[list[str], list[dict[str, Any]]]:
        collection = _collection()
        count = collection.count()
        if count == 0:
            raise RuntimeError(
                "The Chroma knowledge base is empty. Run `python ingest_rag.py` first."
            )

        collection_metadata = collection.metadata or {}
        stored_backend = collection_metadata.get("embedding_backend")
        stored_dimension = collection_metadata.get("embedding_dimension")
        if stored_backend == f"local-hash-{LOCAL_HASH_DIMENSIONS}-v1":
            query_backend = stored_backend
            query_embedding = [_hash_embedding(question.strip())]
        else:
            embedder = OllamaEmbeddingFunction()
            query_embedding = embedder([question.strip()])
            query_backend = embedder.last_backend

        query_dimension = len(query_embedding[0])
        if stored_backend != query_backend or stored_dimension != query_dimension:
            raise RuntimeError(
                "Chroma embedding backend/dimension mismatch; rebuilding the "
                "local index with the active offline/Ollama backend."
            )

        result = collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        if not documents or len(documents) != len(metadatas):
            raise RuntimeError("Chroma returned no usable retrieved evidence.")
        return documents, metadatas

    try:
        documents, metadatas = retrieve()
    except RuntimeError as exc:
        if not _is_embedding_mismatch_error(exc):
            raise
        from ingest_rag import ingest

        ingest()
        documents, metadatas = retrieve()

    retrieved = [
        {
            "document": document,
            "metadata": metadata,
            "sources": _relevant_sources(
                document, _sources_for_chunk(metadata)
            ),
        }
        for document, metadata in zip(documents, metadatas)
    ]
    answer = _generate_answer(
        question=question.strip(),
        retrieved=retrieved,
        model=model or OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
    return _format_cited_output(answer, retrieved)


@contextmanager
def _db_connection():
    connection = sqlite3.connect(TELEMETRY_DB_PATH, timeout=30)
    connection.execute("PRAGMA busy_timeout = 30000")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db() -> None:
    """Create the local demo telemetry and gamification tables if absent."""
    TELEMETRY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mission_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id TEXT NOT NULL DEFAULT 'manual',
                mission_day INTEGER NOT NULL,
                environment TEXT NOT NULL,
                heart_rate REAL,
                bp_sys REAL,
                bp_dia REAL,
                blood_glucose REAL,
                body_temp REAL,
                sleep_hours REAL,
                mood_score REAL,
                neutron_radiation_msv REAL,
                radiation_dose_rate_msv_day REAL,
                bone_bmd_delta REAL,
                cabin_co2 REAL,
                status_overall TEXT NOT NULL,
                evidence_status TEXT NOT NULL DEFAULT 'user_entered_unverified',
                radiation_metric_note TEXT,
                metric_evidence_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(mission_telemetry)"
            ).fetchall()
        }
        if "metric_evidence_json" not in columns:
            connection.execute(
                "ALTER TABLE mission_telemetry ADD COLUMN metric_evidence_json TEXT"
            )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_mission_telemetry_scenario_day
            ON mission_telemetry (scenario_id, mission_day)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS gamification_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                streak_days INTEGER NOT NULL DEFAULT 0,
                readiness_score REAL,
                completed_tasks INTEGER NOT NULL DEFAULT 0,
                last_checkin_date TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO gamification_stats
                (id, streak_days, readiness_score, completed_tasks)
            VALUES (1, 0, NULL, 0)
            """
        )


def _row_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, sqlite3.Row):
        return dict(row)
    if isinstance(row, dict):
        return row
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    raise TypeError("latest_row must be a mapping or sqlite row.")


def _number(row: dict[str, Any], *names: str) -> float | None:
    for name in names:
        value = row.get(name)
        if value is not None:
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                return None
            return numeric_value if math.isfinite(numeric_value) else None
    return None


def validate_telemetry_plausibility(row: dict[str, Any]) -> list[str]:
    """Flag values outside broad demo plausibility bounds; not a diagnostic check."""
    bounds = {
        "heart_rate": (25, 240, "bpm"),
        "bp_sys": (50, 260, "mmHg systolic"),
        "bp_dia": (30, 160, "mmHg diastolic"),
        "blood_glucose": (30, 600, "mg/dL"),
        "body_temp": (32.0, 43.0, "°C"),
        "cabin_co2": (0.1, 30.0, "mmHg"),
        "cabin_co2_partial_pressure_mmhg": (0.1, 30.0, "mmHg"),
        "radiation_dose_rate_msv_day": (0, 500, "mSv/day"),
        "bone_bmd_delta": (-40, 20, "%"),
    }
    warnings = []
    for metric, (minimum, maximum, unit) in bounds.items():
        value = row.get(metric)
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            warnings.append(
                f"Likely sensor error: {metric} value {value!r} is not numeric."
            )
            continue
        if not math.isfinite(numeric_value) or not minimum <= numeric_value <= maximum:
            warnings.append(
                f"Likely sensor error: {metric}={value} {unit} is outside the "
                f"broad demo plausibility range {minimum}–{maximum} {unit}."
            )
    return warnings


_TELEMETRY_METRICS = (
    "heart_rate",
    "bp_sys",
    "bp_dia",
    "blood_glucose",
    "body_temp",
    "sleep_hours",
    "mood_score",
    "neutron_radiation_msv",
    "radiation_dose_rate_msv_day",
    "bone_bmd_delta",
    "cabin_co2",
)


def effective_latest_state(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Carry forward latest non-null readings without inventing fallback values."""
    if not history:
        return {}
    if not all(isinstance(row, dict) for row in history):
        raise TypeError("history must contain telemetry dictionaries.")

    state: dict[str, Any] = dict(history[-1])
    metric_evidence_status = {}
    for metric in _TELEMETRY_METRICS:
        for row in reversed(history):
            if row.get(metric) is not None:
                state[metric] = row[metric]
                evidence_status = row.get(
                    "evidence_status", "unknown_provenance"
                )
                recorded_metric_evidence = row.get("metric_evidence_json")
                if recorded_metric_evidence:
                    metric_evidence = json.loads(recorded_metric_evidence)
                    if not isinstance(metric_evidence, dict):
                        raise RuntimeError(
                            "Invalid per-metric telemetry provenance JSON."
                        )
                    evidence_status = metric_evidence.get(
                        metric, evidence_status
                    )
                source_scenario = row.get("scenario_id")
                if (
                    evidence_status == "synthetic_design_fixture"
                    and source_scenario
                ):
                    if (
                        metric == "neutron_radiation_msv"
                        and source_scenario == "iss_leo_baseline"
                    ):
                        evidence_status = "csa_radi_n2_empirical"
                    elif (
                        metric == "bone_bmd_delta"
                        and source_scenario == "mars_surface_day_210"
                    ):
                        evidence_status = "synthetic_extrapolation"
                    elif (
                        metric == "cabin_co2"
                        and source_scenario in {
                            "iss_leo_baseline",
                            "mars_surface_day_210",
                        }
                    ):
                        evidence_status = "synthetic_assumption"
                    elif (
                        metric == "radiation_dose_rate_msv_day"
                        and source_scenario == "artemis_lunar_spe"
                    ):
                        evidence_status = "synthetic_assumption"
                metric_evidence_status[metric] = evidence_status
                break
        else:
            state[metric] = None
    state["metric_evidence_status"] = metric_evidence_status
    return state


def _classify(
    missing: bool, red: bool = False, amber: bool = False
) -> str:
    if red:
        return "Red"
    if amber:
        return "Amber"
    if missing:
        return "No Data"
    return "Green"


def _overall_status(systems: dict[str, dict[str, Any]]) -> str:
    severity = {"No Data": 0, "Green": 1, "Amber": 2, "Red": 3}
    return max(
        (system["status"] for system in systems.values()),
        key=lambda status: severity[status],
        default="No Data",
    )


def evaluate_health_systems(latest_row: Any) -> dict[str, dict[str, Any]]:
    """Return illustrative UI groupings, not clinical or operational alerts."""
    row = _row_dict(latest_row)
    heart_rate = _number(row, "heart_rate")
    systolic = _number(row, "bp_sys")
    diastolic = _number(row, "bp_dia")
    sleep = _number(row, "sleep_hours")
    mood = _number(row, "mood_score")
    radiation = _number(row, "radiation_dose_rate_msv_day")
    radiation_observation = (
        radiation
        if radiation is not None
        else _number(row, "neutron_radiation_msv")
    )
    bone_delta = _number(row, "bone_bmd_delta")
    cabin_co2 = _number(row, "cabin_co2", "cabin_co2_partial_pressure_mmhg")
    glucose = _number(row, "blood_glucose")
    body_temp = _number(row, "body_temp")

    behavioral_red = (
        (sleep is not None and sleep < 5)
        or (mood is not None and mood <= 3)
        or (cabin_co2 is not None and cabin_co2 > 5.0)
    )
    behavioral_amber = (
        (sleep is not None and sleep < 7)
        or (mood is not None and mood <= 6)
        or (cabin_co2 is not None and cabin_co2 > 3.0)
    )
    behavioral_missing = (
        sleep is None and mood is None and cabin_co2 is None
    )

    cardio_red = (
        (heart_rate is not None and (heart_rate < 40 or heart_rate > 120))
        or (systolic is not None and (systolic < 80 or systolic >= 180))
        or (diastolic is not None and (diastolic < 50 or diastolic >= 120))
    )
    cardio_amber = (
        (heart_rate is not None and (heart_rate < 50 or heart_rate > 100))
        or (systolic is not None and (systolic < 90 or systolic > 139))
        or (diastolic is not None and (diastolic < 60 or diastolic > 89))
    )
    cardio_missing = (
        heart_rate is None and systolic is None and diastolic is None
    )

    bone_missing = bone_delta is None
    bone_red = bone_delta is not None and bone_delta < -5
    bone_amber = bone_delta is not None and bone_delta < 0

    radiation_missing = radiation_observation is None
    radiation_red = (
        radiation_observation is not None and radiation_observation >= 10
    )
    radiation_amber = (
        radiation_observation is not None
        and 0.5 <= radiation_observation < 10
    )
    glucose_red = glucose is not None and (glucose < 55 or glucose > 250)
    glucose_amber = glucose is not None and (glucose < 70 or glucose > 180)
    temperature_red = body_temp is not None and (
        body_temp < 35.0 or body_temp >= 38.5
    )
    temperature_amber = body_temp is not None and (
        body_temp < 36.0 or body_temp >= 37.8
    )
    immune_red = radiation_red or glucose_red or temperature_red
    immune_amber = radiation_amber or glucose_amber or temperature_amber
    immune_missing = radiation_missing

    compounding = []
    if (
        cabin_co2 is not None
        and cabin_co2 > 3
        and radiation_observation is not None
        and radiation_observation > 0
        and sleep is not None
        and sleep < 6
    ):
        compounding.append(
            "Synthetic co-occurrence of cabin CO2 above the illustrative 3 mmHg "
            "band, a radiation fixture value, and short sleep; this is not a "
            "causal finding or operational alert."
        )
    if (
        bone_delta is not None
        and bone_delta < 0
        and radiation_observation is not None
        and radiation_observation > 0
    ):
        compounding.append(
            "Synthetic bone-change and radiation indicators co-occur; this "
            "does not establish causation or a clinical risk level."
        )

    specifications = {
        "neuro_ocular_behavioral": (
            _classify(behavioral_missing, behavioral_red, behavioral_amber),
            ["HRP-RED-SANS", "HRP-RED-BHPC"],
            {
                "sleep_hours": sleep,
                "mood_score": mood,
                "cabin_co2": cabin_co2,
            },
            [
                alert
                for alert in compounding
                if "short sleep" in alert
            ]
            + (
                [
                    "Cabin CO2 is above the illustrative 3.0 mmHg watch band; "
                    "this is a demo display condition, not an exposure limit."
                ]
                if cabin_co2 is not None and cabin_co2 > 3.0
                else []
            ),
            "Sleep, mood, and cabin CO2 are demo indicators; no SANS-specific eye or optic-nerve exam is represented.",
        ),
        "cardiovascular": (
            _classify(cardio_missing, cardio_red, cardio_amber),
            ["HRP-MOD-CARDIO"],
            {
                "heart_rate": heart_rate,
                "bp_sys": systolic,
                "bp_dia": diastolic,
            },
            list(compounding),
            "Illustrative display bands only; these values do not diagnose cardiovascular status.",
        ),
        "skeletal_bone": (
            _classify(bone_missing, bone_red, bone_amber),
            ["HRP-RED-BONE"],
            {"bone_bmd_delta": bone_delta},
            [
                alert
                for alert in compounding
                if "bone-change" in alert
            ],
            "BMD status bands are synthetic UI groupings, not NASA limits or individual predictions.",
        ),
        "immune_radiation": (
            _classify(immune_missing, immune_red, immune_amber),
            ["HRP-RED-RAD"],
            {
                "radiation_dose_rate_msv_day": radiation,
                "neutron_radiation_msv": _number(row, "neutron_radiation_msv"),
                "blood_glucose": glucose,
                "body_temp": body_temp,
            },
            [
                alert
                for alert in compounding
                if "radiation" in alert
            ],
            "Radiation, glucose, and temperature bands are synthetic; this grouping does not measure immune markers or define exposure limits.",
        ),
    }

    return {
        name: {
            "status": status,
            "color": STATUS_COLORS[status],
            "project_tag": project_tag,
            "key_metrics": key_metrics,
            "compounding_alerts": alerts,
            "classification_note": (
                "Non-operational demo classification; project-defined tags "
                "are not NASA severity ratings."
            ),
            "system_note": system_note,
        }
        for name, (
            status,
            project_tag,
            key_metrics,
            alerts,
            system_note,
        ) in specifications.items()
    }


def load_scenario_to_db(scenario_id: str) -> int:
    """Load 14 synthetic demo days; exact fixture endpoints remain labeled."""
    scenarios = {scenario["scenario_id"]: scenario for scenario in seed_scenario()}
    if scenario_id not in scenarios:
        raise ValueError(f"Unknown scenario_id: {scenario_id}")
    scenario = scenarios[scenario_id]
    measurements = scenario["measurements"]
    mission_end_day = int(scenario.get("mission_day", 14))
    mission_start_day = mission_end_day - 13
    environment = scenario["mission_phase"]
    records = []

    for index in range(14):
        is_endpoint = index == 13
        mission_day = mission_start_day + index
        heart_rate = float(68 + index % 4)
        systolic = float(115 + index % 3)
        diastolic = float(74 + index % 4)
        glucose = float(90 + (index % 5) * 2)
        body_temp = 36.5 + (index % 3) * 0.1
        sleep = 6.8 + (index % 4) * 0.2
        mood = float(6 + index % 3)

        radiation_rate = None
        neutron_radiation = None
        radiation_note = None
        if scenario_id == "iss_leo_baseline":
            neutron_radiation = measurements["neutron_radiation_msv"]["value"]
            cabin_co2 = measurements["cabin_co2_partial_pressure_mmhg"]["value"]
            radiation_note = (
                "Neutron value is a constant scenario reference from CSA "
                "Radi-N2's reported 0.15 mSv/day, not 14 daily observations "
                "or a total-dose rate. Cabin CO2 is a synthetic 2.8 mmHg fixture."
            )
        elif scenario_id == "artemis_lunar_spe":
            radiation_rate = (
                measurements["radiation_spike_msv_day"]["value"]
                if is_endpoint
                else None
            )
            cabin_co2 = None
            radiation_note = (
                "Project stress test (synthetic): mixed neutron/proton spike "
                "on the scenario endpoint; not a pure neutron dose or an "
                "Artemis measurement."
            )
        else:
            radiation_rate = None
            cabin_co2 = (
                measurements["cabin_co2_partial_pressure_mmhg"]["value"]
                if is_endpoint
                else None
            )
            radiation_note = "No radiation value is specified by this fixture."

        bone_delta = None
        if scenario_id == "mars_surface_day_210":
            bone_delta = round(-7.8 - (index * 0.6 / 13), 2)
            radiation_note = (
                "Synthetic BMD interpolation informed by NASA HRP's published "
                "population-average monthly rate, not a NASA-derived daily "
                "trajectory. Day 210 cabin CO2 is a project stress test "
                "(synthetic)."
            )

        row = {
            "heart_rate": heart_rate,
            "bp_sys": systolic,
            "bp_dia": diastolic,
            "blood_glucose": glucose,
            "body_temp": body_temp,
            "sleep_hours": sleep,
            "mood_score": mood,
            "neutron_radiation_msv": neutron_radiation,
            "radiation_dose_rate_msv_day": radiation_rate,
            "bone_bmd_delta": bone_delta,
            "cabin_co2": cabin_co2,
        }
        metric_evidence = {
            metric: "synthetic_design_fixture"
            for metric, value in row.items()
            if value is not None
        }
        if scenario_id == "iss_leo_baseline":
            metric_evidence["neutron_radiation_msv"] = (
                "csa_radi_n2_empirical"
            )
            metric_evidence["cabin_co2"] = "synthetic_assumption"
        elif scenario_id == "artemis_lunar_spe":
            metric_evidence["radiation_dose_rate_msv_day"] = (
                "synthetic_assumption"
            )
        elif scenario_id == "mars_surface_day_210":
            metric_evidence["bone_bmd_delta"] = "synthetic_extrapolation"
            if cabin_co2 is not None:
                metric_evidence["cabin_co2"] = "synthetic_assumption"
        status = _overall_status(evaluate_health_systems(row))
        records.append(
            (
                scenario_id,
                mission_day,
                environment,
                heart_rate,
                systolic,
                diastolic,
                glucose,
                body_temp,
                sleep,
                mood,
                neutron_radiation,
                radiation_rate,
                bone_delta,
                cabin_co2,
                status,
                "synthetic_design_fixture",
                radiation_note,
                json.dumps(metric_evidence, sort_keys=True),
            )
        )

    init_db()
    with _db_connection() as connection:
        connection.execute(
            "DELETE FROM mission_telemetry WHERE scenario_id = ?",
            (scenario_id,),
        )
        connection.executemany(
            """
            INSERT INTO mission_telemetry (
                scenario_id, mission_day, environment, heart_rate, bp_sys,
                bp_dia, blood_glucose, body_temp, sleep_hours, mood_score,
                neutron_radiation_msv, radiation_dose_rate_msv_day,
                bone_bmd_delta, cabin_co2, status_overall, evidence_status,
                radiation_metric_note, metric_evidence_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
    return len(records)


def log_vitals(
    vitals: dict[str, Any] | None = None, **values: Any
) -> int:
    """Append one telemetry row; values default to unverified user-entered data."""
    row = dict(vitals or {})
    row.update(values)
    if "mission_day" not in row:
        raise ValueError("mission_day is required.")
    if not row.get("environment"):
        raise ValueError("environment is required.")

    scenario_id = str(row.get("scenario_id", "manual"))
    evidence_status = str(row.get("evidence_status", "user_entered_unverified"))
    status = row.get("status_overall")
    if status not in STATUS_COLORS:
        status = _overall_status(evaluate_health_systems(row))

    fields = (
        "mission_day",
        "environment",
        "heart_rate",
        "bp_sys",
        "bp_dia",
        "blood_glucose",
        "body_temp",
        "sleep_hours",
        "mood_score",
        "neutron_radiation_msv",
        "radiation_dose_rate_msv_day",
        "bone_bmd_delta",
        "cabin_co2",
    )
    record = [scenario_id] + [row.get(field) for field in fields] + [
        status,
        evidence_status,
        row.get("radiation_metric_note"),
        json.dumps(
            row.get(
                "metric_evidence",
                {
                    field: evidence_status
                            for field in _TELEMETRY_METRICS
                            if row.get(field) is not None
                },
            ),
            sort_keys=True,
        ),
    ]
    init_db()
    with _db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO mission_telemetry (
                scenario_id, mission_day, environment, heart_rate, bp_sys,
                bp_dia, blood_glucose, body_temp, sleep_hours, mood_score,
                neutron_radiation_msv, radiation_dose_rate_msv_day,
                bone_bmd_delta, cabin_co2, status_overall, evidence_status,
                radiation_metric_note, metric_evidence_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            record,
        )
        return int(cursor.lastrowid)


def get_vitals_history(
    limit: int = 14, scenario_id: str | None = None
) -> list[dict[str, Any]]:
    """Return the newest telemetry rows in chronological order."""
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer.")
    init_db()
    with _db_connection() as connection:
        connection.row_factory = sqlite3.Row
        if scenario_id is None:
            rows = connection.execute(
                """
                SELECT * FROM mission_telemetry
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM mission_telemetry
                WHERE scenario_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (scenario_id, limit),
            ).fetchall()
    return [dict(row) for row in reversed(rows)]


def get_gamification_stats() -> dict[str, Any]:
    """Return local check-in counters; readiness_score is game UI only."""
    init_db()
    with _db_connection() as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM gamification_stats WHERE id = 1"
        ).fetchone()
    if row is None:
        raise RuntimeError("The gamification stats row was not initialized.")
    return dict(row)


def _demo_readiness_score(latest_row: dict[str, Any]) -> float:
    return compute_demo_readiness(evaluate_health_systems(latest_row))


def complete_daily_checkin(
    readiness_score: float | None = None,
) -> dict[str, Any]:
    """Increment local gamification counters, not a medical fitness score."""
    if readiness_score is not None and not 0 <= float(readiness_score) <= 100:
        raise ValueError("readiness_score must be between 0 and 100.")
    history = get_vitals_history(limit=1)
    score = (
        float(readiness_score)
        if readiness_score is not None
        else (_demo_readiness_score(history[-1]) if history else None)
    )
    today = date.today()
    init_db()
    with _db_connection() as connection:
        connection.row_factory = sqlite3.Row
        current = connection.execute(
            "SELECT * FROM gamification_stats WHERE id = 1"
        ).fetchone()
        previous_date = current["last_checkin_date"]
        if previous_date == today.isoformat():
            streak = int(current["streak_days"])
        elif previous_date == (today - timedelta(days=1)).isoformat():
            streak = int(current["streak_days"]) + 1
        else:
            streak = 1
        connection.execute(
            """
            UPDATE gamification_stats
            SET streak_days = ?, readiness_score = ?,
                completed_tasks = completed_tasks + 1,
                last_checkin_date = ?
            WHERE id = 1
            """,
            (streak, score, today.isoformat()),
        )
    return get_gamification_stats()


def simulate_countermeasure_projection(
    latest_row: Any, countermeasures: Sequence[str] | dict[str, bool] | None
) -> pd.DataFrame:
    """Return a synthetic, non-operational 7-day comparison for UI exploration."""
    row = _row_dict(latest_row)
    if countermeasures is None:
        selected: set[str] = set()
    elif isinstance(countermeasures, dict):
        selected = {name for name, enabled in countermeasures.items() if enabled}
    elif isinstance(countermeasures, (list, tuple, set)):
        selected = set(countermeasures)
    else:
        raise TypeError("countermeasures must be a list, set, tuple, mapping, or None.")
    unknown = selected - COUNTERMEASURE_NAMES
    if unknown:
        raise ValueError(f"Unknown countermeasures: {sorted(unknown)}")

    radiation = _number(
        row, "radiation_dose_rate_msv_day", "neutron_radiation_msv"
    )
    bone = _number(row, "bone_bmd_delta")
    heart_rate = _number(row, "heart_rate")
    systolic = _number(row, "bp_sys")
    diastolic = _number(row, "bp_dia")
    sleep = _number(row, "sleep_hours")
    mood = _number(row, "mood_score")
    radiation_base = min(1.0, max(0.0, radiation / 18.5)) if radiation is not None else None
    cardio_base = None
    if heart_rate is not None and systolic is not None and diastolic is not None:
        deviation = (
            abs(heart_rate - 70) * 0.7
            + abs(systolic - 120) * 0.2
            + abs(diastolic - 80) * 0.2
        )
        cardio_base = max(0.0, min(100.0, 100.0 - deviation))
    neuro_base = None
    if sleep is not None and mood is not None:
        neuro_base = max(
            0.0,
            min(100.0, (sleep / 8.0) * 60.0 + (mood / 10.0) * 40.0),
        )

    baseline_name = "No Action (Baseline Drift)"
    selected_name = "With Selected Countermeasures"
    rows = []
    for day in range(1, 8):
        base_values = {
            "radiation_risk_index": (
                min(1.0, radiation_base + 0.01 * day)
                if radiation_base is not None
                else None
            ),
            "bone_bmd_delta": bone - 0.04 * day if bone is not None else None,
            "cardio_stability_score": (
                max(0.0, cardio_base - 0.5 * day)
                if cardio_base is not None
                else None
            ),
            "neuro_readiness_score": (
                max(0.0, neuro_base - day)
                if neuro_base is not None
                else None
            ),
        }
        selected_values = dict(base_values)
        if (
            "Water-Wall Shelter (design concept)" in selected
            and selected_values["radiation_risk_index"] is not None
        ):
            selected_values["radiation_risk_index"] *= 0.8
        if (
            "ARED Resistance Protocol (+30 min)" in selected
            and selected_values["bone_bmd_delta"] is not None
        ):
            selected_values["bone_bmd_delta"] += 0.02 * day
        if selected_values["cardio_stability_score"] is not None:
            if "Thigh Cuff & Fluid Load" in selected:
                selected_values["cardio_stability_score"] += 5.0
            selected_values["cardio_stability_score"] = min(
                100.0, selected_values["cardio_stability_score"]
            )
        if selected_values["neuro_readiness_score"] is not None:
            if "Circadian Blue-Light Reset" in selected:
                selected_values["neuro_readiness_score"] += 8.0
            selected_values["neuro_readiness_score"] = min(
                100.0, selected_values["neuro_readiness_score"]
            )

        rows.append(
            {
                "day_ahead": day,
                "scenario": baseline_name,
                **base_values,
                "selected_countermeasures": "",
                "evidence_status": "synthetic_non_operational_projection",
                "starting_bone_bmd_delta": bone,
            }
        )
        rows.append(
            {
                "day_ahead": day,
                "scenario": selected_name,
                **selected_values,
                "selected_countermeasures": ", ".join(sorted(selected)),
                "evidence_status": "synthetic_non_operational_projection",
                "starting_bone_bmd_delta": bone,
            }
        )

    projection = pd.DataFrame(rows)
    projection.attrs["disclaimer"] = (
        "Synthetic illustration only. Scores, drifts, and countermeasure "
        "effects are not validated efficacy estimates, clinical predictions, "
        "radiation limits, or operational guidance."
    )
    projection.attrs["countermeasure_assumptions"] = {
        "Water-Wall Shelter (design concept)": "20% reduction in the demo radiation-risk index, not a measured shielding factor or verified habitat design.",
        "ARED Resistance Protocol (+30 min)": "Offsets half of the demo daily BMD drift, not a measured exercise effect.",
        "Thigh Cuff & Fluid Load": "Adds 5 demo cardiovascular-stability points, not a measured treatment effect.",
        "Circadian Blue-Light Reset": "Adds 8 demo neuro-readiness points, not a measured treatment effect.",
    }
    return projection
