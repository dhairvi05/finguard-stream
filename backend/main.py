# """
# backend/main.py
# ---------------
# FastAPI REST layer for Ledgify.

# Endpoints
# ---------
# GET /api/ledger
#     Returns the latest 30 transactions from PostgreSQL, sorted newest-first.

# GET /api/alerts
#     Returns the latest 15 AI forensic compliance records from MongoDB,
#     sorted descending by audit date.

# GET /health
#     Simple liveness check – useful for container health probes.
# """

# import sys
# from datetime import datetime
# from pathlib import Path
# from typing import Any

# from fastapi import Depends, FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pymongo import MongoClient, DESCENDING
# from sqlalchemy.orm import Session

# # ---------------------------------------------------------------------------
# # Project root on path
# # ---------------------------------------------------------------------------
# PROJECT_ROOT = Path(__file__).resolve().parent.parent
# sys.path.insert(0, str(PROJECT_ROOT))

# from config.db_config import (  # noqa: E402
#     MONGO_URI,
#     TransactionLedger,
#     get_db,
#     init_db,
# )

# # ---------------------------------------------------------------------------
# # Application factory
# # ---------------------------------------------------------------------------

# app = FastAPI(
#     title="Ledgify API",
#     description=(
#         "High-throughput financial fraud monitoring pipeline. "
#         "Exposes real-time transaction ledger and AI-powered compliance alerts."
#     ),
#     version="1.0.0",
# )

# # Allow the Streamlit dashboard (running on a different port) to call the API
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ---------------------------------------------------------------------------
# # MongoDB client (module-level – shared across requests)
# # ---------------------------------------------------------------------------

# MONGO_DB_NAME = "compliance_audit_db"
# MONGO_COLLECTION = "ai_forensic_logs"

# _mongo_client: MongoClient | None = None


# def get_mongo_collection():
#     """Lazy-initialised MongoDB collection accessor."""
#     global _mongo_client
#     if _mongo_client is None:
#         _mongo_client = MongoClient(MONGO_URI)
#     return _mongo_client[MONGO_DB_NAME][MONGO_COLLECTION]


# # ---------------------------------------------------------------------------
# # Startup event: initialise PostgreSQL schema
# # ---------------------------------------------------------------------------

# @app.on_event("startup")
# def on_startup() -> None:
#     init_db()
#     print("[main.py] PostgreSQL schema ready.")


# # ---------------------------------------------------------------------------
# # Health check
# # ---------------------------------------------------------------------------

# @app.get("/health", tags=["System"])
# def health_check() -> dict:
#     return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# # ---------------------------------------------------------------------------
# # GET /api/ledger
# # ---------------------------------------------------------------------------

# @app.get("/api/ledger", tags=["Transactions"])
# def get_ledger(db: Session = Depends(get_db)) -> list[dict]:
#     """
#     Return the 30 most recently ingested transactions from PostgreSQL,
#     ordered newest-first.

#     Each record includes: id, transaction_id, user_id, amount, currency,
#     merchant_type, location, timestamp (ISO-8601), and status.
#     """
#     try:
#         rows = (
#             db.query(TransactionLedger)
#             .order_by(TransactionLedger.timestamp.desc())
#             .limit(30)
#             .all()
#         )
#         return [row.to_dict() for row in rows]
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# # ---------------------------------------------------------------------------
# # GET /api/alerts
# # ---------------------------------------------------------------------------

# def _serialise_mongo_doc(doc: dict) -> dict[str, Any]:
#     """
#     Convert a raw MongoDB document into a JSON-serialisable dict.

#     - Removes the BSON ObjectId (_id) from the response.
#     - Converts datetime fields to ISO-8601 strings.
#     """
#     doc.pop("_id", None)

#     for key, value in doc.items():
#         if isinstance(value, datetime):
#             doc[key] = value.isoformat()

#     return doc


# @app.get("/api/alerts", tags=["Compliance Alerts"])
# def get_alerts() -> list[dict[str, Any]]:
#     """
#     Return the 15 most recent AI forensic compliance records from MongoDB,
#     sorted descending by the 'audited_at' timestamp.

#     Each document includes the original transaction fields plus the
#     structured AI report fields: risk_rating, threat_typology,
#     narrative_rationale, enforcement_action, and the raw_ai_output text.
#     """
#     try:
#         collection = get_mongo_collection()
#         cursor = (
#             collection.find({})
#             .sort("audited_at", DESCENDING)
#             .limit(15)
#         )
#         return [_serialise_mongo_doc(doc) for doc in cursor]
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc

"""
backend/main.py
---------------
FastAPI REST layer for Ledgify.

Endpoints
---------
GET /health
    Simple liveness check.

GET /api/ledger
    Latest 30 transactions from PostgreSQL, sorted newest-first.

GET /api/alerts
    Latest 15 AI forensic compliance records from MongoDB, sorted
    descending by audit date.

GET /api/compliance/{transaction_id}
    Single AI forensic compliance document by transaction_id, used by
    the dashboard's Master-Detail forensic view.

GET /api/compliance/{transaction_id}/exists
    Lightweight existence check for a compliance document.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient, DESCENDING
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Project root on path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.db_config import (  # noqa: E402
    MONGO_URI,
    TransactionLedger,
    get_db,
    init_db,
)

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Ledgify API",
    description=(
        "High-throughput financial fraud monitoring pipeline. "
        "Exposes real-time transaction ledger and AI-powered compliance alerts."
    ),
    version="1.1.0",
)

# Allow the Streamlit dashboard (running on a different port) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# MongoDB client (module-level – shared across requests)
# ---------------------------------------------------------------------------

MONGO_DB_NAME = "compliance_audit_db"
MONGO_COLLECTION = "ai_forensic_logs"

_mongo_client: Optional[MongoClient] = None


def get_mongo_collection():
    """Lazy-initialised MongoDB collection accessor."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI)
    return _mongo_client[MONGO_DB_NAME][MONGO_COLLECTION]


# ---------------------------------------------------------------------------
# Startup event: initialise PostgreSQL schema
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup() -> None:
    init_db()
    print("[main.py] PostgreSQL schema ready.")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check() -> dict:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# GET /api/ledger
# ---------------------------------------------------------------------------

@app.get("/api/ledger", tags=["Transactions"])
def get_ledger(db: Session = Depends(get_db)) -> list[dict]:
    """
    Return the 30 most recently ingested transactions from PostgreSQL,
    ordered newest-first.

    Each record includes: id, transaction_id, user_id, amount, currency,
    merchant_type, location, timestamp (ISO-8601), and status.
    """
    try:
        rows = (
            db.query(TransactionLedger)
            .order_by(TransactionLedger.timestamp.desc())
            .limit(30)
            .all()
        )
        return [row.to_dict() for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /api/alerts
# ---------------------------------------------------------------------------

def _serialise_mongo_doc(doc: dict) -> dict[str, Any]:
    """
    Convert a raw MongoDB document into a JSON-serialisable dict.

    - Removes the BSON ObjectId (_id) from the response.
    - Converts datetime fields to ISO-8601 strings.
    """
    doc.pop("_id", None)

    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()

    return doc


@app.get("/api/alerts", tags=["Compliance Alerts"])
def get_alerts() -> list[dict[str, Any]]:
    """
    Return the 15 most recent AI forensic compliance records from MongoDB,
    sorted descending by the 'audited_at' timestamp.

    Each document includes the original transaction fields plus the
    structured AI report fields: risk_rating, threat_typology,
    narrative_rationale, enforcement_action, and the raw_ai_output text.
    """
    try:
        collection = get_mongo_collection()
        cursor = (
            collection.find({})
            .sort("audited_at", DESCENDING)
            .limit(15)
        )
        return [_serialise_mongo_doc(doc) for doc in cursor]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /api/compliance/{transaction_id}
# (New — required for the Master-Detail Forensic Analytics Workspace)
# ---------------------------------------------------------------------------

@app.get("/api/compliance/{transaction_id}", tags=["Compliance Alerts"])
def get_compliance_report(transaction_id: str) -> dict[str, Any]:
    """
    Return the single AI forensic compliance document for one
    transaction_id, from MongoDB collection
    compliance_audit_db.ai_forensic_logs.

    Raises 404 if no compliance document has been generated yet for this
    transaction (e.g. the Llama3 worker hasn't processed it).
    """
    try:
        collection = get_mongo_collection()
        doc = collection.find_one({"transaction_id": transaction_id})

        if doc is None:
            raise HTTPException(
                status_code=404,
                detail=f"No compliance audit document found for transaction_id={transaction_id}",
            )

        return _serialise_mongo_doc(doc)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /api/compliance/{transaction_id}/exists
# ---------------------------------------------------------------------------

@app.get("/api/compliance/{transaction_id}/exists", tags=["Compliance Alerts"])
def compliance_report_exists(transaction_id: str) -> dict[str, Any]:
    """
    Lightweight existence check, used by the dashboard to avoid a 404
    round-trip per row when deciding whether to show a 'pending' state
    for a FLAGGED transaction.
    """
    try:
        collection = get_mongo_collection()
        exists = collection.count_documents({"transaction_id": transaction_id}, limit=1) > 0
        return {"transaction_id": transaction_id, "exists": exists}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc