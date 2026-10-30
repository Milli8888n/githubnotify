"""
FastAPI Application for GitScrum AI
Provides REST API endpoints for repository scanning, Agile metrics calculation,
AI summary generation, webhook notifications, and serves the Web Dashboard.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

from github_scanner import GitHubScanner
from agile_engine import AgileEngine
from ai_summary import AIScrumMaster
from notifier import WebhookNotifier

# Fallback values from .env
DEFAULT_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip() or None
DEFAULT_REPO = os.getenv("DEFAULT_REPO", "").strip()
DEFAULT_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip() or None
DEFAULT_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip() or None
DEFAULT_SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "").strip() or None
DEFAULT_DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "").strip() or None
DEFAULT_TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or None
DEFAULT_TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip() or None

app = FastAPI(
    title="GitScrum AI",
    description="Automated GitHub Activity Scanner & Agile/Scrum Reporter",
    version="1.0.0",
)

# Enable CORS for local dev flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static folder exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

engine = AgileEngine()


# --- Models ---
class ScanSprintRequest(BaseModel):
    owner: str
    repo: str
    milestone_number: int
    token: Optional[str] = None


class AISummaryRequest(BaseModel):
    sprint_data: Dict[str, Any]
    provider: str = "heuristic"  # heuristic, gemini, openai
    api_key: Optional[str] = None
    custom_prompt: Optional[str] = None


class SendWebhookRequest(BaseModel):
    platform: str  # slack, discord, telegram
    webhook_url: Optional[str] = None
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    sprint_data: Dict[str, Any]
    custom_message: Optional[str] = None


# --- Endpoints ---
@app.get("/")
async def root():
    """Serve the Web Dashboard."""
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status": "online",
        "message": "GitScrum AI Backend is running. Please place index.html in the static directory.",
    }


@app.get("/api/config")
async def get_initial_config():
    """Return configured defaults from .env (without exposing private keys)."""
    return {
        "has_github_token": bool(DEFAULT_GITHUB_TOKEN),
        "default_repo": DEFAULT_REPO,
        "has_gemini_key": bool(DEFAULT_GEMINI_KEY),
        "has_openai_key": bool(DEFAULT_OPENAI_KEY),
        "has_slack_webhook": bool(DEFAULT_SLACK_WEBHOOK),
        "has_discord_webhook": bool(DEFAULT_DISCORD_WEBHOOK),
        "has_telegram": bool(DEFAULT_TELEGRAM_TOKEN and DEFAULT_TELEGRAM_CHAT_ID),
        "slack_webhook_url": DEFAULT_SLACK_WEBHOOK,
        "discord_webhook_url": DEFAULT_DISCORD_WEBHOOK,
        "telegram_chat_id": DEFAULT_TELEGRAM_CHAT_ID,
    }


@app.get("/api/rate-limit")
async def check_rate_limit(token: Optional[str] = None):
    """Check remaining GitHub API calls for the user/IP."""
    active_token = token or DEFAULT_GITHUB_TOKEN
    scanner = GitHubScanner(token=active_token)
    try:
        return await scanner.get_rate_limit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/milestones")
async def get_milestones(
    owner: str = Query(..., description="Repository owner"),
    repo: str = Query(..., description="Repository name"),
    token: Optional[str] = Query(None, description="Optional GitHub Personal Access Token"),
    state: str = Query("all", description="open, closed, all"),
):
    """List all milestones for the specified repository."""
    active_token = token or DEFAULT_GITHUB_TOKEN
    scanner = GitHubScanner(token=active_token)
    try:
        await scanner.verify_repo(owner, repo)
        milestones = await scanner.get_milestones(owner, repo, state=state)
        return {"owner": owner, "repo": repo, "milestones": milestones}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/api/scan-sprint")
async def scan_sprint(req: ScanSprintRequest):
    """Scan a milestone and run full Agile/Scrum metrics engine."""
    active_token = req.token or DEFAULT_GITHUB_TOKEN
    scanner = GitHubScanner(token=active_token)
    try:
        # 1. Fetch milestone metadata
        milestones = await scanner.get_milestones(req.owner, req.repo, state="all")
        target_milestone = next((m for m in milestones if m["number"] == req.milestone_number), None)
        if not target_milestone:
            raise HTTPException(status_code=404, detail=f"Milestone #{req.milestone_number} not found in {req.owner}/{req.repo}")

        # 2. Fetch issues, pull requests, reviews, and commits
        items_data = await scanner.get_milestone_items(req.owner, req.repo, req.milestone_number)

        # 3. Analyze through Agile Engine
        analysis = engine.analyze_sprint(
            milestone=target_milestone,
            pull_requests=items_data["pull_requests"],
            issues=items_data["issues"],
            commits=items_data["commits"],
        )

        return {
            "status": "success",
            "repository": f"{req.owner}/{req.repo}",
            "data": analysis,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan error: {str(e)}")


@app.post("/api/ai-summary")
async def generate_ai_summary(req: AISummaryRequest):
    """Generate AI Scrum Master summary (heuristic or via Gemini/OpenAI)."""
    try:
        active_key = req.api_key
        if not active_key:
            if req.provider == "gemini":
                active_key = DEFAULT_GEMINI_KEY
            elif req.provider == "openai":
                active_key = DEFAULT_OPENAI_KEY

        if req.provider in ["gemini", "openai"] and active_key:
            summary = await AIScrumMaster.generate_llm_summary(
                sprint_data=req.sprint_data,
                provider=req.provider,
                api_key=active_key,
                custom_instructions=req.custom_prompt,
            )
        else:
            summary = AIScrumMaster.generate_heuristic_summary(req.sprint_data)
        return {"status": "success", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation error: {str(e)}")


@app.post("/api/send-webhook")
async def send_webhook(req: SendWebhookRequest):
    """Send Agile report to Slack, Discord, or Telegram."""
    try:
        if req.platform == "slack":
            url = req.webhook_url or DEFAULT_SLACK_WEBHOOK
            if not url:
                raise HTTPException(status_code=400, detail="Slack webhook_url is required (nhập trên UI hoặc qua SLACK_WEBHOOK_URL trong .env).")
            res = await WebhookNotifier.send_slack_webhook(url, req.sprint_data, req.custom_message)
            return res

        elif req.platform == "discord":
            url = req.webhook_url or DEFAULT_DISCORD_WEBHOOK
            if not url:
                raise HTTPException(status_code=400, detail="Discord webhook_url is required (nhập trên UI hoặc qua DISCORD_WEBHOOK_URL trong .env).")
            res = await WebhookNotifier.send_discord_webhook(url, req.sprint_data, req.custom_message)
            return res

        elif req.platform == "telegram":
            token = req.telegram_token or DEFAULT_TELEGRAM_TOKEN
            chat_id = req.telegram_chat_id or DEFAULT_TELEGRAM_CHAT_ID
            if not token or not chat_id:
                raise HTTPException(status_code=400, detail="Telegram bot_token and chat_id are required (nhập trên UI hoặc qua file .env).")
            msg = req.custom_message or WebhookNotifier.format_standup_markdown(req.sprint_data)
            res = await WebhookNotifier.send_telegram_message(token, chat_id, msg)
            return res

        raise HTTPException(status_code=400, detail=f"Unsupported platform '{req.platform}'.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/demo")
async def get_demo_data():
    """Return realistic mock Sprint data for instant testing without token or rate limits."""
    now = datetime.now(timezone.utc)
    mock_milestone = {
        "number": 14,
        "title": "Sprint 14: Checkout & Payment Optimization",
        "state": "open",
        "created_at": (now - timedelta(days=9)).isoformat(),
        "due_on": (now + timedelta(days=5)).isoformat(),
        "html_url": "https://github.com/company/ecommerce/milestone/14",
    }

    mock_prs = [
        {
            "id": 101,
            "number": 204,
            "title": "feat: Stripe webhook signature validation [5sp]",
            "state": "closed",
            "merged": True,
            "author": "sarah-frontend",
            "author_avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80",
            "labels": ["sp:5", "backend", "security"],
            "created_at": (now - timedelta(hours=36)).isoformat(),
            "merged_at": (now - timedelta(hours=14)).isoformat(),
            "closed_at": (now - timedelta(hours=14)).isoformat(),
            "html_url": "https://github.com/company/ecommerce/pull/204",
            "reviews": [{"user": "david-backend", "state": "APPROVED", "submitted_at": (now - timedelta(hours=15)).isoformat()}],
        },
        {
            "id": 102,
            "number": 208,
            "title": "fix: Cart item counter badge sync on mobile safari [2sp]",
            "state": "closed",
            "merged": True,
            "author": "alex-dev",
            "author_avatar": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80",
            "labels": ["sp:2", "bug", "mobile"],
            "created_at": (now - timedelta(hours=22)).isoformat(),
            "merged_at": (now - timedelta(hours=6)).isoformat(),
            "closed_at": (now - timedelta(hours=6)).isoformat(),
            "html_url": "https://github.com/company/ecommerce/pull/208",
            "reviews": [{"user": "sarah-frontend", "state": "APPROVED", "submitted_at": (now - timedelta(hours=8)).isoformat()}],
        },
        {
            "id": 103,
            "number": 210,
            "title": "feat: Apple Pay / Google Pay express checkout button [8sp]",
            "state": "open",
            "merged": False,
            "author": "alex-dev",
            "author_avatar": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80",
            "labels": ["sp:8", "feature", "checkout"],
            "created_at": (now - timedelta(hours=54)).isoformat(),
            "updated_at": (now - timedelta(hours=52)).isoformat(),
            "html_url": "https://github.com/company/ecommerce/pull/210",
            "requested_reviewers": ["david-backend"],
            "reviews": [],
        },
        {
            "id": 104,
            "number": 212,
            "title": "refactor: Order tax recalculation service [3sp]",
            "state": "open",
            "merged": False,
            "author": "david-backend",
            "author_avatar": "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?w=100&auto=format&fit=crop&q=80",
            "labels": ["sp:3", "backend", "refactor"],
            "created_at": (now - timedelta(hours=30)).isoformat(),
            "updated_at": (now - timedelta(hours=10)).isoformat(),
            "html_url": "https://github.com/company/ecommerce/pull/212",
            "requested_reviewers": ["alex-dev"],
            "reviews": [{"user": "alex-dev", "state": "CHANGES_REQUESTED", "submitted_at": (now - timedelta(hours=10)).isoformat()}],
        },
    ]

    mock_issues = [
        {
            "id": 301,
            "number": 195,
            "title": "E2E Cypress testing for full checkout flow [5sp]",
            "state": "closed",
            "author": "emily-qa",
            "author_avatar": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=100&auto=format&fit=crop&q=80",
            "assignees": ["emily-qa"],
            "labels": ["sp:5", "qa", "e2e"],
            "created_at": (now - timedelta(days=5)).isoformat(),
            "closed_at": (now - timedelta(hours=18)).isoformat(),
            "html_url": "https://github.com/company/ecommerce/issues/195",
        },
        {
            "id": 302,
            "number": 199,
            "title": "Integrate address autocomplete API [3sp]",
            "state": "open",
            "author": "sarah-frontend",
            "author_avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80",
            "assignees": ["sarah-frontend"],
            "labels": ["sp:3", "frontend", "blocked"],
            "created_at": (now - timedelta(days=2)).isoformat(),
            "html_url": "https://github.com/company/ecommerce/issues/199",
        },
    ]

    mock_commits = [
        {"sha": "a7b3c29", "author": "sarah-frontend", "message": "feat: handle stripe webhook idempotency", "date": (now - timedelta(hours=16)).isoformat(), "html_url": "#"},
        {"sha": "f1e8d4a", "author": "alex-dev", "message": "fix: prevent double submit on place order button", "date": (now - timedelta(hours=8)).isoformat(), "html_url": "#"},
        {"sha": "c3b9e11", "author": "emily-qa", "message": "test: add cypress test cases for payment errors", "date": (now - timedelta(hours=20)).isoformat(), "html_url": "#"},
    ]

    analysis = engine.analyze_sprint(
        milestone=mock_milestone,
        pull_requests=mock_prs,
        issues=mock_issues,
        commits=mock_commits,
        now=now,
    )

    return {
        "status": "success",
        "repository": "company/ecommerce-core (Demo Dataset)",
        "data": analysis,
    }
