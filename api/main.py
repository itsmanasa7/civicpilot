from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load .env file from project root or api folder
for candidate_env in [
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent / ".env",
]:
    if candidate_env.exists():
        load_dotenv(candidate_env, override=False)

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, create_engine

from rag.service import RAGService, AskRequest, AskResponse
from rag.notice import NoticeExplainer, ExplainNoticeResponse
from rules import (
    evaluate_profile,
    whatif_analysis,
    EligibilityRequest,
    EligibilityResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from interview import InterviewRequest, InterviewResponse, get_interview_engine
from reconcile import DocumentReconciler, get_reconciler, ReconcileResponse, ManualCorrectionRequest
from status_decoder import (
    DecodeStatusRequest,
    DecodeStatusResponse,
    get_status_decoder,
)
from agent import (
    StartFillRequest,
    StartFillResponse,
    ApproveDiffRequest,
    ApproveDiffResponse,
    SubmitConsentRequest,
    SubmitConsentResponse,
    get_registration_agent,
)
from voice import get_voice_service
from demo_users import get_demo_users, get_demo_user_by_id
from rules.simulator import get_rule_simulator
from eval import get_benchmark_runner, BENCHMARK_CASES

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./civicpilot.db")
engine = create_engine(DATABASE_URL, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

rag_service = RAGService()
notice_explainer = NoticeExplainer(rag_service=rag_service)
interview_engine = get_interview_engine()
reconciler = get_reconciler()
status_decoder = get_status_decoder()
registration_agent = get_registration_agent()
voice_service = get_voice_service()
rule_simulator = get_rule_simulator()
benchmark_runner = get_benchmark_runner()

# In-memory store for latest benchmark run
_latest_benchmark_cache = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # Auto-index corpus if database has no chunks
    if rag_service.db.count() == 0:
        rag_service.index_corpus()
    yield
    # Cleanup any active browser sessions
    await registration_agent.cleanup_all()

app = FastAPI(title="CivicPilot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "civicpilot-api"}

@app.get("/")
def root():
    return {"message": "CivicPilot API", "docs": "/docs"}

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    return rag_service.ask(req.question, lang=req.lang)

@app.post("/explain-notice", response_model=ExplainNoticeResponse)
async def explain_notice(
    file: UploadFile = File(...),
    lang: str = Form("en"),
):
    content = await file.read()
    filename = file.filename or "notice.jpg"
    content_type = file.content_type or "image/jpeg"
    return notice_explainer.explain(content, filename=filename, mime_type=content_type, lang=lang)

@app.post("/eligibility", response_model=EligibilityResponse)
def check_eligibility(req: EligibilityRequest):
    """Evaluates citizen profile against PM-KISAN rules using deterministic YAML engine (no LLM)."""
    return evaluate_profile(req.profile)

@app.post("/whatif", response_model=WhatIfResponse)
def check_whatif(req: WhatIfRequest):
    """Runs hypothetical what-if simulation comparing original profile against updated profile."""
    return whatif_analysis(req.profile, req.changes)

@app.post("/interview", response_model=InterviewResponse)
def interview_turn(req: InterviewRequest):
    """Interactive conversational intake interviewer that extracts profile fields one at a time.
    The LLM never determines or states eligibility itself. When complete, calls rule engine.
    """
    res = interview_engine.process_turn(
        user_message=req.message or "",
        profile=req.profile,
        current_field=req.current_field,
        lang=req.lang,
    )
    return res

@app.post("/reconcile", response_model=ReconcileResponse)
async def reconcile_documents(
    files: Optional[List[UploadFile]] = File(default=None),
):
    """Extracts fields from documents and produces a fuzzy-matched discrepancy report."""
    parsed_docs = {}

    if files and len(files) > 0:
        for f in files:
            content = await f.read()
            doc_key = Path(f.filename).stem if f.filename else "doc"
            parsed = reconciler.parse_document_text_or_json(content, f.filename or "doc.txt")
            parsed_docs[doc_key] = parsed
    else:
        # Load synthetic sample documents from demo-data
        demo_dir = Path("c:/civicpilot/demo-data")
        if not demo_dir.exists():
            demo_dir = Path(__file__).resolve().parent.parent / "demo-data"

        for json_path in demo_dir.glob("*.json"):
            parsed_docs[json_path.stem] = json.loads(json_path.read_text(encoding="utf-8"))

    return reconciler.reconcile(parsed_docs)

@app.post("/reconcile/correct", response_model=ReconcileResponse)
def reconcile_with_corrections(req: ManualCorrectionRequest):
    """Re-runs reconciliation with citizen/operator manual corrections applied."""
    return reconciler.reconcile(req.extracted_fields_by_doc, req.corrections)

@app.post("/decode-status", response_model=DecodeStatusResponse)
async def decode_status_endpoint(request: Request):
    """Decodes pasted or photographed portal status messages using known-causes YAML + RAG fallback."""
    content_type = request.headers.get("content-type", "")
    status_text = ""
    lang = "en"

    if "application/json" in content_type:
        body = await request.json()
        status_text = body.get("status_text", "")
        lang = body.get("lang", "en")
    elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        status_text = str(form.get("status_text") or "")
        lang = str(form.get("lang") or "en")
        upload_file = form.get("file")
        if upload_file and hasattr(upload_file, "read"):
            file_bytes = await upload_file.read()
            if file_bytes and len(file_bytes) > 0:
                fn = getattr(upload_file, "filename", "status.jpg")
                mt = getattr(upload_file, "content_type", "image/jpeg")
                ocr_text, conf, is_blurry = notice_explainer.extract_text(file_bytes, filename=fn, mime_type=mt)
                if ocr_text:
                    status_text = f"{status_text}\n{ocr_text}".strip() if status_text else ocr_text
    else:
        raw = await request.body()
        try:
            parsed = json.loads(raw.decode("utf-8"))
            status_text = parsed.get("status_text", "")
            lang = parsed.get("lang", "en")
        except Exception:
            status_text = raw.decode("utf-8")
            lang = "en"

    if not status_text.strip():
        raise HTTPException(status_code=400, detail="Missing status_text or uploaded status image.")

    return status_decoder.decode(status_text=status_text, lang=lang)

# ----------------- VOICE ENDPOINTS ----------------- #

@app.post("/voice/transcribe")
async def voice_transcribe(
    file: UploadFile = File(...),
    lang: str = Form("en"),
):
    """Transcribes citizen speech audio (English or Hindi) using Gemini Multimodal Audio."""
    audio_bytes = await file.read()
    mime = file.content_type or "audio/webm"
    res = voice_service.transcribe(audio_bytes=audio_bytes, mime_type=mime, lang=lang)
    return res

@app.post("/voice/turn")
async def voice_turn(
    file: UploadFile = File(...),
    lang: str = Form("en"),
    mode: str = Form("interview"),
    profile_json: Optional[str] = Form(default=None),
    current_field: Optional[str] = Form(default=None),
):
    """One-shot spoken audio turn: Transcribes voice, runs through interview/RAG, and returns response."""
    audio_bytes = await file.read()
    mime = file.content_type or "audio/webm"
    transcription = voice_service.transcribe(audio_bytes=audio_bytes, mime_type=mime, lang=lang)
    spoken_text = transcription.get("text", "").strip()

    if mode == "ask":
        rag_res = rag_service.ask(spoken_text or "PM-KISAN eligibility guidelines", lang=lang)
        return {
            "transcription": transcription,
            "spoken_input": spoken_text,
            "reply_text": rag_res.answer,
            "citations": rag_res.citations,
            "confidence": rag_res.confidence,
            "needs_escalation": rag_res.needs_escalation,
            "lang": lang,
        }
    else:
        # Default interview flow
        prof_dict = json.loads(profile_json) if profile_json else {}
        interview_res = interview_engine.process_turn(
            user_message=spoken_text,
            profile=prof_dict,
            current_field=current_field,
            lang=lang,
        )
        reply = (
            interview_res.get("assistant_message")
            if isinstance(interview_res, dict)
            else getattr(interview_res, "assistant_message", "")
        )
        return {
            "transcription": transcription,
            "spoken_input": spoken_text,
            "interview": interview_res,
            "reply_text": reply,
            "lang": lang,
        }

# ----------------- PLAYWRIGHT AGENT ENDPOINTS ----------------- #

@app.post("/agent/start-fill", response_model=StartFillResponse)
async def agent_start_fill(req: StartFillRequest):
    """Launches Playwright, navigates to mirror form, fills profile fields, and produces diff."""
    try:
        return await registration_agent.start_fill(
            profile_data=req.profile,
            portal_url=req.portal_url or "http://localhost:4000",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/approve-diff", response_model=ApproveDiffResponse)
async def agent_approve_diff(req: ApproveDiffRequest):
    """User approves the verified field diffs. Agent transitions to OTP step and pauses."""
    try:
        return await registration_agent.approve_diff(req.session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/agent/submit-with-consent", response_model=SubmitConsentResponse)
async def agent_submit_with_consent(req: SubmitConsentRequest):
    """Enforces explicit consent check. Enters user OTP, submits form, and writes immutable JSON audit log."""
    if not req.explicit_consent:
        raise HTTPException(
            status_code=400,
            detail="SUBMISSION_BLOCKED: Explicit user consent is mandatory. Submission aborted.",
        )
    try:
        return await registration_agent.submit_with_consent(
            session_id=req.session_id,
            otp=req.otp,
            explicit_consent=req.explicit_consent,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent/audit-log/{session_id}")
def get_audit_log(session_id: str):
    """Fetches the written JSON audit log for a given session."""
    from agent.browser_agent import AUDIT_LOGS_DIR
    log_file = AUDIT_LOGS_DIR / f"{session_id}.json"
    if not log_file.exists():
        raise HTTPException(status_code=404, detail=f"Audit log for session '{session_id}' not found.")
    return json.loads(log_file.read_text(encoding="utf-8"))

# ----------------- DEMO USERS, SIMULATOR & NUDGES ----------------- #

@app.get("/demo-users")
def list_demo_users():
    """Returns the list of seeded demo users with their profiles and baseline statuses."""
    return get_demo_users()

@app.get("/demo-users/{user_id}")
def get_single_demo_user(user_id: str):
    u = get_demo_user_by_id(user_id)
    if not u:
        raise HTTPException(status_code=404, detail=f"Demo user '{user_id}' not found.")
    return u

@app.post("/simulate-rule-change")
def simulate_rule_change(
    new_version: str = "2026.2",
    description: str = "Strict Cutoff Date Enforcement: Disqualify land mutated after 01-Feb-2019",
):
    """Versions the scheme corpus, evaluates all demo users, and notifies ONLY affected users."""
    res = rule_simulator.simulate_rule_amendment(
        new_version=new_version,
        amendment_description=description,
    )
    return res

@app.post("/cron/dispatch-nudges")
def cron_dispatch_nudges():
    """Simulates periodic background cron job sending proactive nudges for deadlines and missing docs."""
    nudges = rule_simulator.run_cron_nudge_dispatch()
    return {"status": "ok", "dispatched_count": len(nudges), "nudges": nudges}

@app.get("/nudges")
def get_dispatched_nudges():
    """Returns all dispatched proactive citizen nudges."""
    return rule_simulator.dispatched_nudges

# ----------------- BENCHMARK EVALUATION (/eval) ----------------- #

@app.get("/eval/cases")
def list_eval_cases():
    """Lists the 30 benchmark test cases across Eligibility, Citations, Escalation, and Reconciliation."""
    return {"total_cases": len(BENCHMARK_CASES), "cases": BENCHMARK_CASES}

@app.post("/eval/run")
def run_evaluation_benchmark():
    """Executes the full 30-case evaluation benchmark and calculates accuracy, coverage, and recall."""
    global _latest_benchmark_cache
    metrics = benchmark_runner.run_all()
    _latest_benchmark_cache = metrics
    return metrics

@app.get("/eval/latest")
def get_latest_evaluation():
    """Returns the latest benchmark evaluation results (or runs on demand if not cached)."""
    global _latest_benchmark_cache
    if _latest_benchmark_cache is None:
        _latest_benchmark_cache = benchmark_runner.run_all()
    return _latest_benchmark_cache

@app.post("/index")
def index_corpus():
    count = rag_service.index_corpus()
    return {"status": "ok", "indexed_chunks": count}
