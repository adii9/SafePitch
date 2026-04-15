# SafeDeck — Product Specification

> **Status:** Active development
> **Brand:** SafeDeck (unified — PitchSafe retired)
> **Last Updated:** 2026-04-15

---

## 1. What SafeDeck Does

SafeDeck is an **AI deal intelligence layer for VCs**. It sits between inbound pitch decks and a VC's deal workflow, automatically reading decks, extracting structured data, verifying founder claims, and pushing the results into the VC's CRM and spreadsheets.

**Core loop:**
1. Founder emails a pitch deck PDF to `{fund_slug}@safedeck.ai` (or manual upload)
2. SafeDeck parses the PDF (LlamaParse) → markdown
3. Four CrewAI agents extract, verify, and score the deck in parallel + sequential verification
4. Structured output is pushed to Google Sheets, DynamoDB, and — via n8n webhook — into HubSpot or any CRM
5. The VC sees a scored, verified deal profile in their dashboard

**Value proposition:** Upfront setup → compounding ROI. One VC configures their thesis, column mapping, and scoring weights once. Every subsequent deck auto-populates their deal pipeline with zero manual work.

---

## 2. Architecture Overview

```
Founder Email / Upload
         │
         ▼
┌─────────────────────────────────┐
│  Parser Lambda (eu-north-1)     │
│  • Download from Google Drive    │
│  • LlamaParse PDF → Markdown     │
│  • Invoke CrewAI Lambda async    │
└─────────────────────────────────┘
         │
  Base64-encoded
  Markdown payload
  (< 256 KB or S3)
         │
         ▼
┌─────────────────────────────────┐
│  CrewAI Lambda (eu-north-1)      │
│  • SafepitchFlow (crewAI Flows)  │
│  • Tenant config lookup          │
│    (SafeDeckUsers DynamoDB)      │
│  • Sequential Crew process       │
│  • Rating template apply          │
│  • Save audit → DynamoDB         │
│  • Sync state → S3 (flows.db)    │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  AWS DynamoDB                    │
│  • Audit results (per tenant)    │
│  • SafeDeckUsers (config)       │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  n8n / Webhook                   │
│  • Push to HubSpot              │
│  • Google Sheets append          │
│  • Slack notification            │
│  • Notion page create            │
└─────────────────────────────────┘
```

**Frontend (React/Vite):**
- Deployed at `https://d36t7grotgwbz5.cloudfront.net/`
- Pages: Landing, Pricing, Checkout, Onboarding (7 steps), Dashboard, Sample Audit
- Calls two Lambda functions directly:
  - `user-sync` (eu-north-1) — onboarding profile + criteria save
  - `safepitch-function` (eu-north-1) — deck upload trigger
  - `audits` (eu-north-1) — dashboard reads existing audits

---

## 3. Agents & Their Roles

SafeDeck uses **CrewAI** with 4 specialist agents + 1 final consolidator. All use `gemini/gemini-2.5-flash`.

### Agent 1: `kyc_specialist`
**Role:** KYC and Onboarding Specialist
**Tools:** SerperDevTool (web search)
**Extracts:**
- Company identity (name, website, location, incorporation)
- Founder/promoter details (name, email, LinkedIn)
- Senior team + prior experience + education
- Sector, industry cluster, product offering

**Key behavior:** Aborts with `{"error": "No company with this name found."}` if real-world existence cannot be verified. This is a critical gate.

---

### Agent 2: `financial_auditor`
**Role:** Senior Financial Investment Analyst
**Tools:** None (deck-only data)
**Extracts:**
- Revenue model, EBITDA, unit economics (CAC/LTV/Contribution Margin)
- Current round ask, expected valuation, EV/Revenue multiple
- Prior funding, prior investors, prior valuation
- Cap table, grants received
- Calculates: EV/Revenue from Ask + Revenue; valuation increase %

**Key behavior:** Strictly deck-sourced. No external lookups. Numbers must come from parsed markdown tables.

---

### Agent 3: `market_intelligence_analyst`
**Role:** Market Research and Tracxn Intelligence Specialist
**Tools:** SerperDevTool (for Tracxn browsing)
**Extracts:**
- TAM/SAM/SOM (deck-primary, Tracxn-validated only if deck is missing)
- Competitor list (from deck competitive matrix, NOT replaced by Tracxn)
- Industry composition, CAGR, market share estimates
- Total funding raised by company

**Deck-First Protocol:** Always use deck data as primary. Tracxn is for validation/enrichment only.

---

### Agent 4: `claim_verification_specialist`
**Role:** Pitch Deck Claim Verification Specialist
**Tools:** SerperDevTool (web search)
**Behavior:** Forensic fact-checker. Treats every number and namedrop as a hypothesis. Produces a structured `verification_report` with:
- `summary.truth_score` (0–100)
- `verified_claims[]`
- `unverified_claims[]`
- `contradicted_claims[]`
- `field_level_verification{}`

**Key insight from sample report:** "Ex-Google", "Ex-Microsoft" claims are easy to make and hard to verify. This agent exists specifically to catch founders who pad their bios.

---

### Task 5: `final_consolidation_task`
**Role:** Consolidator (uses `market_intelligence_analyst` agent)
**Inputs:** Outputs from all 4 prior tasks as context
**Behavior:** Merges all 50+ fields into a single JSON object, injecting `verification_status` into each field. Matches a per-tenant `excel_schema` (53 columns in default config).

---

## 4. Current Features

### Implemented
- [x] Google OAuth login (landing page)
- [x] 7-step onboarding flow:
  1. Auth
  2. Fund profile + thesis + sectors/stages
  3. Evaluation criteria (53-field schema, per-field Must Have / Nice to Have / Ignore)
  4. Google Sheet column mapping
  5. Data source (email filter or manual upload)
  6. Test deck upload
  7. Done
- [x] Fund-specific inbox (`{slug}@safedeck.ai`)
- [x] Gmail forwarding setup instructions in onboarding
- [x] PDF upload via dashboard
- [x] LlamaParse PDF → Markdown
- [x] 4-agent CrewAI extraction + verification pipeline
- [x] DynamoDB persistence of audit results
- [x] Dashboard showing all audited decks with revenue, sector, status
- [x] Deck detail modal (full audit JSON view)
- [x] Per-tenant evaluation criteria + rating template (weights)
- [x] Per-tenant Google Sheet URL + field mapping
- [x] Multi-tenant config via `SafeDeckUsers` DynamoDB table
- [x] S3-based CrewAI flows.db persistence (state survives Lambda cold starts)
- [x] API endpoints: `profile`, `criteria`, `sheet`, `mapping`, `drive`, `datasource`, `email`, `safepitch-function`, `audits`, `user-sync`, `safepay`

### Partially Implemented
- [~] n8n integration (listed on landing page, no Lambda/webhook handler built yet)
- [~] HubSpot push (listed in integrations, not wired to any Lambda)
- [~] Google Sheets live append (URL stored per tenant, but write-back not implemented)
- [~] Tracxn integration (mentioned in agent config, but no real API — uses SerperDevTool as proxy)

### Not Yet Built
- [ ] Continuous monitoring (founder update emails, status changes)
- [ ] Calendar + meeting note integration (unlike Billion AI)
- [ ] VC thesis training (unlike Pitchto.vc)
- [ ] LinkedIn founder status change tracking (unlike Datacrust)
- [ ] Outbound LinkedIn / email automation (unlike FinalLayer, Mindy)
- [ ] Affinity integration (listed in landing page)
- [ ] Notion integration (listed in landing page)
- [ ] Slack notifications (listed in landing page)
- [ ] Per-tenant webhook URL (n8n needs a POST target)
- [ ] Deal pipeline / CRM view (dashboard only shows list of decks, not a pipeline board)
- [ ] Founder follow-up email automation
- [ ] Competitive analysis auto-report (vs. Pitchto.vc)
- [ ] Real Tracxn API integration (instead of web scraping via SerperDevTool)

---

## 5. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite, React Router v6, Framer Motion, Lucide icons |
| Styling | CSS custom properties, CSS Grid/Flexbox, no Tailwind |
| Auth | Google OAuth via `@react-oauth/google` |
| Backend AI | CrewAI 1.8.1, Gemini 2.5 Flash (via `gemini/gemini-2.5-flash`) |
| PDF Parsing | LlamaParse (async, runs in Parser Lambda) |
| Search | SerperDevTool (CrewAI built-in) |
| Database | AWS DynamoDB (audits + SafeDeckUsers) |
| State | S3 (`flows.db` — CrewAI Flow persistence) |
| Compute | AWS Lambda (2 functions: Parser + CrewAI) |
| Email | Gmail filter → `{slug}@safedeck.ai` forwarding |
| Payments | Custom `safepay` Lambda (Stripe or similar) |
| CDN | AWS CloudFront |
| Infrastructure | Terraform-ready (Dockerfiles in `Deployment/` and `Parser_Deployment/`) |
| Language | TypeScript (frontend), Python 3.10+ (backend) |
| Package Manager | UV (backend), npm (frontend) |

---

## 6. Brand Name Decision

**Decision: Use "SafeDeck" exclusively.**

- Landing page hero: "SafeDeck | AI-Powered Pitch Deck Auditor for VCs"
- Header/nav: "SafeDeck"
- Dashboard: "SafeDeck | Dashboard"
- Onboarding footer: "SafeDeck"
- Email inbox convention: `{slug}@safedeck.ai`
- API endpoints / Lambda functions: reference `safepitch` internally (keep for now, but external-facing docs should use SafeDeck)
- Domain: safedeck.ai (assumed)

**Action items:**
- [ ] Retire "PitchSafe" from all copy — landing page `index.html` title tag says "SafeDeck", but `<title>` in `index.html` says "PitchSafe" (line 6 of index.html — `<title>PitchSafe | AI-Powered Pitch Deck Auditor for VCs</title>` — needs update)
- [ ] Rename GitHub repo / internal folder from `safepitch` to `safedeck` if it causes confusion
- [ ] Update `pyproject.toml` `name = "safepitch"` → `name = "safedeck"` for proper package naming

---

## 7. Roadmap

### Short Term — 1–2 Sprints (Prove the Core Value)

These are quick wins that validate the product's core promise: "upload a deck, get a verified profile."

#### 1.1 Fix brand name consistency
- Update `<title>` in `index.html` from "PitchSafe" to "SafeDeck"
- Rename repo folder from `safepitch` → `safedeck` (or alias)
- Update `pyproject.toml` name field
- **Why:** First impression matters. A VC sees "PitchSafe" on Google and "SafeDeck" in the app — trust erodes.

#### 1.2 Wire up Google Sheets write-back
- Add a Lambda function or n8n trigger that, on audit completion, appends a row to the tenant's configured Google Sheet URL
- Map the 53-field schema to the tenant's custom column mapping
- **Why:** VCs repeatedly asked about this. It's the #1 manual task they're paying to eliminate.

#### 1.3 Wire up Slack notifications
- On audit completion, POST to a tenant-specific Slack webhook URL with: company name, revenue, truth score, and a link to the dashboard
- **Why:** VCs want to know within seconds of a deck arriving. Push > pull.

#### 1.4 Real Tracxn API integration
- Replace SerperDevTool "Tracxn" lookups with the actual Tracxn API (or approved scraping partner)
- Add a Tracxn API key to tenant config
- **Why:** Data quality is the #1 VC pain point. SerperDevTool is not a private markets database.

#### 1.5 Fix the verification report integration
- The `verification_report.md` exists but isn't being returned as part of the Lambda response
- Ensure `claim_verification_task` output is included in the DynamoDB save and dashboard display
- Surface truth score prominently in the dashboard card
- **Why:** The verification layer is SafeDeck's key differentiator vs. simple OCR tools. It must be visible.

---

### Medium Term — Next Quarter (Core Differentiation)

These features address the specific pain points VCs voiced on the call.

#### 2.1 HubSpot CRM push
- Map audit output to HubSpot deal/contact fields
- Create or update HubSpot deal on audit completion
- Push founder contact + company + financial metrics to HubSpot
- **Why:** HubSpot is the base CRM for deal flow per the VC calls. SafeDeck must feed it, not require VCs to manually export.

#### 2.2 Founder update email monitoring
- Instead of only processing new deck emails, also monitor for replies/update emails from previously tracked founders
- Detect "update" emails and trigger a re-audit vs. previous baseline
- Flag what changed: new revenue, new round, new team members
- **Why:** "Always on" is in the product DNA. Currently it's "on-demand." VCs want continuous tracking.

#### 2.3 Competitive analysis auto-report
- On audit completion, generate a 1-page competitive brief: how does this company compare to existing portfolio? What's the whitespace?
- Use the deck's competitor list + Tracxn data to build this
- **Why:** Pitchto.vc trains on VC thesis to pre-screen. SafeDeck should synthesize the competitive landscape from the deck itself.

#### 2.4 Affinity integration
- Map founders and prior investors to Affinity list entries
- **Why:** Listed in current integrations section but not built.

#### 2.5 Per-tenant webhook + n8n support
- Allow VCs to configure a webhook URL in onboarding (Step 4 or Settings)
- POST the full audit JSON to their n8n instance on completion
- This unlocks Notion, Linear, Jira, or any custom workflow
- **Why:** n8n is listed in integrations. It enables everything else.

#### 2.6 Deal pipeline board view
- Replace the flat deck list in dashboard with a Kanban board: Pipeline / Under Review / Passed / Committed
- Allow VC to manually move deals between stages
- Show truth score and key metrics on each card
- **Why:** VCs think in pipelines, not deck lists.

#### 2.7 Founder claim red flags dashboard
- Surface a dedicated "Red Flags" panel on the deck detail view
- Show contradicted claims, unverified claims, founder "Ex-Company" flags
- Make it impossible to miss — this is the trust layer
- **Why:** Data quality is the #1 VC pain point. SafeDeck must be explicit about what it couldn't verify.

---

### Long Term — Platform / Network Effects

These build compounding moat.

#### 3.1 VC Network Effect — Anonymized Benchmarking
- With VC consent, pool anonymized market data across funds (TAM figures, competitor funding rounds, valuation multiples)
- Allow VCs to ask: "Where does this company's revenue multiple sit vs. our 2024 cohort?"
- **Why:** Each fund sees only their own deals. Network-wide data is enormously valuable and impossible for a single fund to build.

#### 3.2 Founder Signal Engine
- Track founder LinkedIn status changes (job changes, new companies, funding announcements) via Datacrust or similar
- Alert VCs when a founder in their pipeline raises a round elsewhere, switches sectors, or exits
- **Why:** VCs mentioned Datacrust specifically. This is a high-value alert that keeps SafeDeck sticky.

#### 3.3 "Teach Once, Repeat Forever" — Portfolio Monitoring
- Expand from deal sourcing to portfolio monitoring: quarterly financial updates, runway calculations, headcount changes
- Compare portfolio company metrics against deck claims (are they tracking to projections?)
- **Why:** This is the "compounding ROI" pitch. New deal intake is table stakes. Portfolio tracking is the retainer.

#### 3.4 AI Meeting Notes Integration
- Integrate with calendar (Google Calendar API) to pull meeting notes after founder calls
- Auto-attach notes to the deal profile
- Cross-reference claims in the meeting with claims in the deck
- **Why:** Billion AI has calendar + notetaker + CRM. SafeDeck needs to match this baseline to stay competitive.

#### 3.5 VC Thesis–Trained Screening (vs. Pitchto.vc)
- Allow funds to upload their investment thesis (PDF or text)
- Score inbound decks against stated thesis alignment
- Flag when a deck matches thesis but VC hasn't seen it yet
- **Why:** Pitchto.vc's core feature. SafeDeck should match it, then exceed it with verification + CRM push.

#### 3.6 SafeDeck Fund (Network Fund)
- Once network effect is strong enough: create a proprietary deal flow feed from SafeDeck subscriber funds
- VCs get access to deals from other funds' pipelines (with founder consent)
- This is the ultimate network effect flywheel
- **Why:** This is how Bloomberg became indispensable. One terminal → everyone needs the terminal.

---

## 8. Critical Gaps vs. VC Needs

| VC Pain Point | SafeDeck Status | Priority |
|---|---|---|
| Data quality / hallucinations | Partially addressed (verification agent exists, not surfaced) | 🔴 Critical |
| Privacy / compliance | Not addressed — all data in AWS/US | 🔴 Critical |
| Microsoft ecosystem | No Outlook/Excel integration | 🟡 Medium |
| "Teach once, repeat forever" | Onboarding config done, but no continuous monitoring | 🟡 Medium |
| CRM push (HubSpot) | Listed, not built | 🟡 Medium |
| Always-on deck monitoring | Email filter built, no re-audit on updates | 🟡 Medium |
| Competitive analysis | Deck-only, no cross-portfolio view | 🟡 Medium |
| Calendar / meeting notes | Not built | 🟡 Medium |
| LinkedIn founder tracking | Not built | 🟡 Low (nice to have) |
| LinkedIn outbound | Not built | 🟡 Low (nice to have) |

### Biggest Immediate Risk
**Data quality without visible verification = liability.** If a VC relies on SafeDeck's extracted revenue figure and it's wrong, they blame SafeDeck — not the founder. The verification layer is the product's most important feature and it's currently the least visible. It must be surfaced prominently.

### Pricing Fit Check
At ₹30K–₹1L/month (by deals tracked, not seats), VCs need to see clear ROI per deal:
- 1 deal/day × 20 working days = 20 deals/month
- At ₹30K/month that's ₹1,500/deal
- That needs to replace 30–60 min of analyst time per deal = ~₹500–1,000 in labor
- **Conclusion:** Price is only justified if SafeDeck also saves meeting notes, CRM entry, AND competitive research — not just deck extraction. The "deals tracked, not seats" model is correct but needs the full workflow to justify it.

---

*Document author: Dev Agent (Subagent)*
*For questions or updates, contact the main agent.*

## n8n Integration Layer

**Location:** `/Users/adiimathur/Downloads/safepitch-workflows/`

n8n is the orchestration layer for email ingestion and external integrations.

### Workflows:

**1. SafeDeck-Engine (`Aasn5YkzJgoypxED-SafeDeck_Engine.json`)**
- `Gmail Trigger` — watches for emails with pitch deck attachments
- `Upload file` (Google Drive) — stores incoming decks
- `Basic LLM Chain` + `Google Gemini Chat Model` — basic AI preprocessing
- `Merge` — combines data flows
- `Create folder` (Google Drive) — organizes processed decks
- `AWS Lambda` — triggers CrewAI deep processing pipeline
- Output → `SafeDeck_Writer`

**2. SafeDeck-Writer (`Awmrlt5zd1jPiUDU-SafeDeck_Writer.json`)**
- `Append or update row in sheet` (Google Sheets) — writes audit results
- `Webhook1` — incoming trigger for results

**3. My workflow (`2fL43T5d23MzRWyC-My_workflow.json`)**
- `Gmail Trigger` → `Upload file` → `AWS Lambda` → `Merge`

### Data Flow:
```
Pitch deck email
    ↓
n8n Gmail Trigger
    ↓
Google Drive (raw storage)
    ↓
Gemini LLM (basic analysis)
    ↓
CrewAI Lambda (deep analysis)
    ↓
Google Sheets (results via SafeDeck-Writer)
    ↓
SafeDeck Dashboard (frontend)
```

### Implications for Roadmap:
- n8n handles integrations that would otherwise need custom API endpoints
- Google Sheets write-back is already wired through n8n
- The Lambda is the core processing engine — improving it improves everything
- Email ingestion is handled by n8n, not the Lambda — good separation of concerns
