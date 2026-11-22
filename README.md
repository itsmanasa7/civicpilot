# CivicPilot

**ChatGPT explains a document. CivicPilot computes eligibility against a versioned rule set, reconciles your documents, and fills the real form, with your consent.**

Built for **IDEA FORGE**, Track 1: Civic Pulse, Digital Governance & Public Information.
Scheme covered: **PM-KISAN** (English + Hindi).

> All data in this repo is **synthetic**. No real personal documents are used.

## The problem
Government schemes are hard to use. Notices are full of jargon, small document errors cause rejections, and portals are confusing. Citizens often don't know why they were rejected or what to fix.

## What it does
| Feature | Description |
|---|---|
| Scheme Q&A | Answers only from retrieved scheme clauses, with clause IDs. If not covered, it escalates instead of guessing. |
| Notice explainer | Photo of a notice becomes a plain-language explanation with citations (Gemini vision). |
| Eligibility engine | Deterministic YAML rules with unit tests. The LLM never decides eligibility. |
| What-if simulator | See how a change in your situation changes the verdict. |
| Document reconciliation | Cross-checks Aadhaar, land record, bank passbook and self-declaration, then reports mismatches with severity and where to fix them. |
| Status decoder | Maps a rejection or pending status to its cause and fix. |
| Form agent | Playwright fills the form, you review a diff, enter the OTP and give consent. Every step is audit-logged. |
| Voice | Speak in English or Hindi, get a spoken reply. |
| Rule-change simulation | Versioned corpus. Only affected users get notified. |
| Eval dashboard | 30-case benchmark for eligibility, citations, escalation and reconciliation. |

## Architecture

web/ Next.js 14 PWA (mobile-first)
api/ FastAPI + SQLite (FTS5)
rag/ retrieval + cited answers
rules/ YAML eligibility engine + simulator
reconcile/ cross-document matching
agent/ consent-gated Playwright form filler
voice/ speech-to-text / text-to-speech
eval/ benchmark suite
corpus/ versioned scheme documents
mirror/ local mock of the portal form (for reliable demos)

Design principle: the LLM only explains and collects inputs. Everything that decides an outcome is deterministic code.

## Setup
```bash
git clone https://github.com/<your-username>/civicpilot.git
cd civicpilot
cp .env.example .env        # add your GEMINI_API_KEY (aistudio.google.com/apikey)
make dev                    # web :3000, api :8000, portal mirror :4000
make reset                  # restore demo state
cd api && pytest -v         # run tests
```

## Demo
See [DEMO.md](DEMO.md) for the 5-minute walkthrough.

## Responsible use
- Synthetic data only.
- The form agent never submits without explicit user consent and an OTP step.
- The demo runs against a local mirror of the portal, not the live government site.
- Rules must be verified against official PM-KISAN guidelines before any real use. This is a prototype, not legal advice.

## Tech
Next.js, FastAPI, SQLite FTS5, Gemini API, Playwright.

## License
MIT
