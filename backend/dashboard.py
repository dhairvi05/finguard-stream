from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
API_BASE_URL = "http://localhost:8000"  # FastAPI gateway root
LEDGER_ENDPOINT = f"{API_BASE_URL}/api/ledger"
COMPLIANCE_ENDPOINT = f"{API_BASE_URL}/api/compliance"

st.set_page_config(
    page_title="Ledgify | Forensic Analytics Workspace",
    layout="wide",
)

# ------------------------------------------------------------
# Session state initialization (prevents glitching / cleared
# selection on rerun/refresh)
# ------------------------------------------------------------
if "selected_transaction_id" not in st.session_state:
    st.session_state.selected_transaction_id = None

if "selected_transaction_status" not in st.session_state:
    st.session_state.selected_transaction_status = None

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.utcnow()

if "_fetch_error" not in st.session_state:
    st.session_state["_fetch_error"] = None


# ------------------------------------------------------------
# Data fetch helpers
# ------------------------------------------------------------
def _fetch_ledger_from_api() -> pd.DataFrame:
    """
    Pull the latest transactions from PostgreSQL via GET /api/ledger.
    Returns columns: id, transaction_id, user_id, amount, currency,
    merchant_type, location, timestamp, status.
    """
    try:
        resp = requests.get(LEDGER_ENDPOINT, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data)
        st.session_state["_fetch_error"] = None
        return df
    except requests.exceptions.RequestException as exc:
        st.session_state["_fetch_error"] = str(exc)
        return pd.DataFrame()


def fetch_ledger() -> pd.DataFrame:
    """
    Return a STABLE snapshot of the ledger from st.session_state.

    Deliberately NOT re-fetched on every rerun/interaction: live ingestion
    means new rows arrive constantly, and Streamlit's dataframe selection
    is positional (row index). If the underlying data reordered between
    the click and the rerun, the selection highlight would silently land
    on a different transaction than the one the analyst actually clicked
    (e.g. a FLAGGED row appearing to "become" SETTLED). Freezing the
    snapshot avoids this. The analyst explicitly pulls fresh data via the
    'Refresh now' button.
    """
    if "ledger_df" not in st.session_state or st.session_state.ledger_df is None:
        st.session_state.ledger_df = _fetch_ledger_from_api()
    return st.session_state.ledger_df


def fetch_compliance_report(transaction_id: str):
    """
    Pull a single AI forensic compliance document by transaction_id
    via GET /api/compliance/{transaction_id}.

    Returns (report_dict, None) on success,
            (None, "not_found") if no document exists yet,
            (None, error_message) on any other failure.
    """
    try:
        resp = requests.get(f"{COMPLIANCE_ENDPOINT}/{transaction_id}", timeout=10)
        if resp.status_code == 404:
            return None, "not_found"
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as exc:
        return None, str(exc)


# ------------------------------------------------------------
# UI: Header
# ------------------------------------------------------------
st.title("Ledgify — Forensic Analytics Workspace")
st.caption(
    "Split-screen master-detail view: select a transaction on the left to inspect its "
    "AI-generated compliance forensic report on the right."
)

top_l, top_r = st.columns([3, 1])
with top_l:
    if st.session_state.get("_fetch_error"):
        st.warning(f"Could not reach transaction API: {st.session_state['_fetch_error']}")
with top_r:
    if st.button("🔄 Refresh now", use_container_width=True):
        st.session_state.ledger_df = _fetch_ledger_from_api()
        st.session_state.selected_transaction_id = None
        st.session_state.selected_transaction_status = None
        st.session_state.last_refresh = datetime.utcnow()
        st.rerun()

st.divider()

# ------------------------------------------------------------
# Layout: Master (left) / Detail (right)
# ------------------------------------------------------------
left_col, right_col = st.columns([1.4, 1])

# ================= LEFT: MASTER LEDGER VIEW ==================
with left_col:
    st.subheader("Master Ledger — Recent Transactions")

    df = fetch_ledger()

    if df.empty:
        st.info("No transaction data available yet. Waiting for the ingestion worker...")
    else:
        display_cols = [
            c for c in
            ["transaction_id", "user_id", "timestamp", "amount", "currency",
             "merchant_type", "location", "status"]
            if c in df.columns
        ]
        view_df = df[display_cols].copy()

        # ------------------------------------------------------------
        # NOTE ON DESIGN: st.dataframe's on_select interactivity does
        # NOT work when a pandas Styler (used for row background color)
        # is passed in — Streamlit only supports selection on a plain
        # DataFrame. Rather than lose either full-row color or reliable
        # click-to-select, we render each row as its own container with
        # a stable `key`, and scope CSS to that key's auto-generated
        # `st-key-<key>` class (an officially supported Streamlit
        # mechanism) to color the row. A "View" button inside each
        # container drives selection directly — no dataframe involved.
        # ------------------------------------------------------------

        def _safe_key(raw: str) -> str:
            """Sanitize a transaction_id into a CSS-class-safe key fragment."""
            return "".join(ch if ch.isalnum() else "_" for ch in str(raw))

        flagged_keys = []
        settled_keys = []
        for _, r in view_df.iterrows():
            k = _safe_key(r.get("transaction_id", ""))
            status_val = str(r.get("status", "")).upper()
            if status_val == "FLAGGED":
                flagged_keys.append(k)
            elif status_val == "SETTLED":
                settled_keys.append(k)

        css_rules = []
        if flagged_keys:
            selector = ", ".join(f".st-key-txrow_{k}" for k in flagged_keys)
            css_rules.append(
                f"{selector} {{ background-color: rgba(255, 76, 76, 0.14) !important; "
                f"border: 1px solid rgba(255, 76, 76, 0.45) !important; }}"
            )
        if settled_keys:
            selector = ", ".join(f".st-key-txrow_{k}" for k in settled_keys)
            css_rules.append(
                f"{selector} {{ background-color: rgba(46, 204, 113, 0.12) !important; "
                f"border: 1px solid rgba(46, 204, 113, 0.35) !important; }}"
            )
        if css_rules:
            st.markdown(f"<style>{' '.join(css_rules)}</style>", unsafe_allow_html=True)

        with st.container(height=560):
            for _, row in view_df.iterrows():
                tx_id = row.get("transaction_id", "")
                status_val = str(row.get("status", "")).upper()
                row_key = f"txrow_{_safe_key(tx_id)}"

                with st.container(key=row_key, border=True):
                    c1, c2, c3, c4, c5 = st.columns([2.4, 1.1, 1.1, 1.6, 1])

                    with c1:
                        st.markdown(f"**`{str(tx_id)[:18]}…`**")
                        st.caption(f"{row.get('user_id', '')} · {row.get('timestamp', '')}")
                    with c2:
                        st.markdown(f"{row.get('amount', '')} {row.get('currency', '')}")
                    with c3:
                        st.markdown(f"{row.get('merchant_type', '')}")
                        st.caption(f"{row.get('location', '')}")
                    with c4:
                        if status_val == "FLAGGED":
                            st.markdown("🚩 **FLAGGED**")
                        elif status_val == "SETTLED":
                            st.markdown("✅ **SETTLED**")
                        else:
                            st.markdown(status_val)
                    with c5:
                        if st.button("View", key=f"btn_{row_key}", use_container_width=True):
                            st.session_state.selected_transaction_id = tx_id
                            st.session_state.selected_transaction_status = status_val
                            st.rerun()

        flagged_count = len(flagged_keys)
        settled_count = len(settled_keys)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Loaded", len(view_df))
        m2.metric("🚩 Flagged", flagged_count)
        m3.metric("✅ Settled", settled_count)

        st.caption(
            "Click 'View' on a row to select it — the analysis panel on the right updates automatically."
        )

# ================= RIGHT: AI FORENSIC DETAILS VIEW ==================
with right_col:
    st.subheader("AI Forensic Detail — Llama3 Compliance Engine")

    selected_id = st.session_state.selected_transaction_id
    selected_status = st.session_state.selected_transaction_status

    if not selected_id:
        st.info("Select a transaction from the ledger to view its forensic detail here.")
    else:
        st.markdown(f"**Selected Transaction ID:** `{selected_id}`")

        status_normalized = (selected_status or "").strip().upper()

        if status_normalized == "SETTLED":
            st.success("Transaction verified as SETTLED. No compliance anomalies detected by Llama3 Core.")

        elif status_normalized == "FLAGGED":
            with st.spinner("Fetching AI compliance audit from MongoDB..."):
                report, err = fetch_compliance_report(selected_id)

            if err == "not_found":
                st.warning(
                    "This transaction is FLAGGED, but the Llama3 compliance worker has not "
                    "finished generating its audit report yet. Try refreshing shortly."
                )
            elif err:
                st.error(f"Failed to reach compliance API: {err}")
            elif report:
                risk_level = (report.get("risk_rating") or "UNKNOWN").strip().upper()

                if "CRITICAL" in risk_level:
                    st.error("RISK RATING: CRITICAL")
                elif "HIGH" in risk_level:
                    st.error("RISK RATING: HIGH")
                elif "MEDIUM" in risk_level:
                    st.warning("RISK RATING: MEDIUM")
                elif "LOW" in risk_level:
                    st.info("RISK RATING: LOW")
                else:
                    st.markdown(f"**Risk Rating:** {risk_level}")

                meta_l, meta_r = st.columns(2)
                with meta_l:
                    st.caption(f"Model: `{report.get('ai_model', 'llama3')}`")
                with meta_r:
                    audited_at = report.get("audited_at")
                    st.caption(f"Audited: `{audited_at if audited_at else 'unknown'}`")

                info_l, info_r = st.columns(2)
                with info_l:
                    st.caption(f"User: `{report.get('user_id', 'N/A')}`")
                with info_r:
                    amt = report.get("amount")
                    cur = report.get("currency", "")
                    st.caption(f"Amount: `{amt} {cur}`" if amt is not None else "Amount: `N/A`")

                st.markdown("---")

                threat_typology = report.get("threat_typology")
                if threat_typology:
                    st.markdown("#### Financial Threat Typology")
                    st.markdown(threat_typology)
                    st.markdown("")

                enforcement_action = report.get("enforcement_action")
                if enforcement_action:
                    st.markdown("#### Enforcement Action")
                    st.markdown(enforcement_action)
                    st.markdown("")

                narrative_rationale = report.get("narrative_rationale")
                if narrative_rationale:
                    st.markdown("#### Narrative Rationale")
                    with st.container(border=True):
                        st.markdown(narrative_rationale)

                if not (threat_typology or enforcement_action or narrative_rationale):
                    st.warning("Report retrieved, but expected fields were empty. Raw AI output below:")
                    st.code(report.get("raw_ai_output", ""), language="markdown")

                with st.expander("View raw AI report (debug)"):
                    st.code(report.get("raw_ai_output", ""), language="markdown")
        else:
            st.info(
                f"Selected transaction has status `{selected_status or 'UNKNOWN'}`. "
                "Only FLAGGED transactions have a Llama3 compliance report; SETTLED "
                "transactions are shown as clean."
            )

st.divider()
st.caption(
    f"Last data refresh check: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')} UTC · "
    "Auto-refreshing cache every 5s · Click '🔄 Refresh now' to force an immediate pull."
)