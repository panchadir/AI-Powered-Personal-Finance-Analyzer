# AI-Powered Personal Finance Analyzer — Mermaid Diagrams

Eight diagrams covering every major system dimension: architecture, user journey, data pipelines, the financial engine, the AI copilot, the database schema, the API surface, and the 3-day build plan.

---

## 1. System Architecture Overview

Layered monolith with ports-and-adapters at both external edges (statement parsers and LLM calls). The Engine/Narrate boundary is the core invariant: no financial number originates in the narrate layer.

```mermaid
graph TB
    subgraph UI["UI Layer — Reflex Pages + rx.State"]
        P1[auth.py<br/>Register / Login]
        P2[upload.py<br/>Statement Upload]
        P3[transactions.py<br/>Transaction Table]
        P4[dashboard.py<br/>Dashboard & Briefing]
        P5[insights.py<br/>AI Insights]
        P6[copilot.py<br/>AI Copilot Chat]
    end

    subgraph SVC["Service Layer — services/ (framework-agnostic Python)"]
        subgraph ING["Ingestion — services/ingestion/"]
            ING1[StatementParser Protocol]
            ING2[CSV / PDF Parsers]
            ING3[Normalizer]
            ING4[Deduplicator]
        end

        subgraph CAT["Categorize — services/categorize/"]
            CAT1[Tier-1: Rules Engine]
            CAT2[Tier-2: LLM structured output]
            CAT3[Tier-3: Teach Me / user correction]
            CAT4[schema.py — Category Enum SSoT]
        end

        subgraph ENG["Engine — services/engine/ ⚠ no LLM imports"]
            ENG1[safe_to_spend.py]
            ENG2[confidence_score.py]
            ENG3[commitments.py]
        end

        subgraph NAR["Narrate — services/narrate/ ⚠ no math"]
            NAR1[evidence_pack builder]
            NAR2[Claude narrator]
            NAR3[Copilot tool runner]
        end
    end

    subgraph DATA["Data Layer — SQLite via rx.Model / sqlmodel"]
        DB[(SQLite DB)]
        DB --> T1[users]
        DB --> T2[uploaded_files]
        DB --> T3[transactions]
        DB --> T4[merchant_rules]
        DB --> T5[commitments]
        DB --> T6[score_events]
        DB --> T7[insights]
        DB --> T8[chat_messages]
    end

    subgraph EXT["External — Claude API"]
        LLM1[claude-haiku-4-5<br/>Categorization]
        LLM2[claude-opus-4-8<br/>Narration + Copilot]
    end

    P1 & P2 & P3 & P4 & P5 & P6 --> SVC
    ING --> CAT --> ENG
    ENG --> NAR
    SVC --> DATA
    CAT2 --> LLM1
    NAR2 & NAR3 --> LLM2

    classDef hardBoundary stroke:#e74c3c,stroke-width:3px,stroke-dasharray:6
    class ENG,NAR hardBoundary
```

---

## 2. User Journey — Golden Path (MVP)

The committed end-to-end flow: upload → understand → act. Every step maps to an Epic.

```mermaid
flowchart LR
    subgraph E1["Epic 1 — Foundation & Auth"]
        S1([Register])
        S2([Login])
    end

    subgraph E2["Epic 2 — Statement Ingestion"]
        S3([Upload Statement\nPDF / CSV])
        S4([Parse Progress\nWebSocket / polling])
        S5([Transactions Table\ncategory · confidence · badge])
    end

    subgraph E3["Epic 3 — Categorization"]
        S6([Auto-Categorize\nRule → LLM → User])
        S7([Teach Me\nCorrect a category])
    end

    subgraph E4_E5["Epics 4 & 5 — Engine + Dashboard"]
        S8([Dashboard\nSafe-to-Spend · Confidence Score · Briefing])
        S9([Commitments\nadd / edit / delete → STS updates live])
    end

    subgraph E6["Epic 6 — AI Copilot"]
        S10([Copilot Chat\nQ&A · streaming · trace chips])
    end

    subgraph E7_E8["Epics 7 & 8 — Insights"]
        S11([AI Insights\n≥3 pattern detectors fire on demo data])
    end

    S1 --> S2 --> S3 --> S4 --> S5
    S5 --> S6 --> S7
    S5 --> S8 --> S9
    S8 --> S10
    S8 --> S11

    style E1 fill:#e8f4f8,stroke:#2980b9
    style E2 fill:#eafaea,stroke:#27ae60
    style E3 fill:#fef9e7,stroke:#f39c12
    style E4_E5 fill:#fdf2f8,stroke:#8e44ad
    style E6 fill:#fdedec,stroke:#e74c3c
    style E7_E8 fill:#f0f3f4,stroke:#566573
```

---

## 3. Statement Ingestion Pipeline

Ports-and-adapters pattern. Every parser normalizes to the canonical Transaction schema before any downstream processing touches it.

```mermaid
flowchart TD
    U([User uploads\nPDF or CSV]) --> R{File type?}

    R -->|CSV| P1[statementsparser\nIndian bank-specific]
    R -->|Text PDF| P2[pdfplumber\nprimary text-layer]
    R -->|Table PDF| P3[camelot\ntable fallback]
    R -->|Unrecognized text PDF| P4[Claude LLM\ntext extraction]
    R -->|Scanned / image PDF| FAIL[Honest refusal\n'We can't read scanned PDFs yet']

    P1 & P2 & P3 & P4 --> N[Normalizer\n→ canonical Transaction shape\nAD-6]

    N --> DEDUP{Duplicate?}
    DEDUP -->|"hash(user_id, date, amount,\ndescription_raw, balance_after)"| DROP[Drop duplicate]
    DEDUP -->|New| PERSIST[(transactions table)]

    PERSIST --> CAT_GATE{Category\nassigned?}
    CAT_GATE -->|No| TIER1[Tier-1: Rules Engine\n~40–60 India merchant rules\ncategory_source = 'rule']
    TIER1 -->|No match| TIER2[Tier-2: claude-haiku-4-5\nstructured output, Pydantic Literal\ncategory_source = 'llm']
    TIER2 -->|User corrects| TIER3[Tier-3: Teach Me\nwrites merchant_rules row\ncategory_source = 'user']
    TIER1 & TIER2 & TIER3 --> DONE([Transaction ready\nfor Engine])
    CAT_GATE -->|Yes| DONE

    style FAIL fill:#fdedec,stroke:#e74c3c
    style DROP fill:#f9f9f9,stroke:#aaa
    style TIER1 fill:#eafaea,stroke:#27ae60
    style TIER2 fill:#fef9e7,stroke:#f39c12
    style TIER3 fill:#e8f4f8,stroke:#2980b9
```

---

## 4. Financial Engine — Safe-to-Spend & Confidence Score

The engine is the only source of truth for every financial number. It is fully deterministic (no LLM), fully unit-tested, and produces an evidence pack that the narrate layer receives as a struct.

```mermaid
flowchart TD
    subgraph INPUTS["Inputs — SQLite reads, user_id scoped"]
        I1[transactions\ncurrent balance, debits, credits]
        I2[commitments\nname, amount, due_day, criticality]
        I3[score_events\nprior score history]
    end

    subgraph ENG["services/engine/ — zero LLM, all Decimal math"]
        subgraph STS["safe_to_spend.py — AD-8"]
            STS1["balance_after_credits\n(latest transaction balance)"]
            STS2["reserved_total\n= Σ committed obligations\nin proximity window"]
            STS3["buffer\n(configurable safety margin)"]
            STS4["spendable_pool\n= balance − reserved − buffer"]
            STS5["days_to_income\n(≥1, guarded against 0 and ∞)"]
            STS6["safe_to_spend\n= max(0, floor(spendable_pool ÷ days_to_income, 10))"]

            STS1 --> STS4
            STS2 --> STS4
            STS3 --> STS4
            STS4 --> STS6
            STS5 --> STS6
        end

        subgraph CS["confidence_score.py"]
            CS1["Data quality signals\n(completeness, recency, age)"]
            CS2["Commitment coverage\n(known vs predicted)"]
            CS3["Income regularity\n(salary consistency)"]
            CS4["Score 0–100\n+ Low / Med / High band"]
            CS5["score_events row\n(trigger_event, explanation,\nsuggested_action — AD-9)"]

            CS1 & CS2 & CS3 --> CS4
            CS4 --> CS5
        end

        PROX["Proximity Windows\nCritical = 7d, Important = 5d, Flexible = 3d"]
        PROX --> STS2
    end

    subgraph EP["Evidence Pack (struct — no LLM)"]
        EP1[reserved_total]
        EP2[spendable_pool]
        EP3[days_to_income]
        EP4[safe_to_spend_today]
        EP5[safe_to_spend_after_income]
        EP6[prediction_confidence]
        EP7[drivers array]
        EP8[data_quality_flags array]
        EP9[safety_ok bool]
    end

    INPUTS --> ENG
    STS6 --> EP1 & EP2 & EP3 & EP4 & EP5 & EP6 & EP7 & EP8 & EP9
    CS4 --> EP6

    EP -->|struct only — no numbers computed here| NAR["services/narrate/\nClaude opus-4-8 → plain-language briefing"]
    EP --> UI["Dashboard hero card\nSTS · CS · Briefing"]

    classDef noLLM fill:#eafaea,stroke:#27ae60
    class ENG noLLM
    classDef llmOnly fill:#fef9e7,stroke:#f39c12
    class NAR llmOnly
```

---

## 5. AI Copilot — Request / Response Flow

The Copilot is strictly read-only. Four hardcoded honesty rules are non-configurable in the system prompt. The SSE `done` event fires from a `finally` block — the browser EventSource never hangs.

```mermaid
sequenceDiagram
    actor User
    participant Client as Browser / Reflex UI
    participant API as POST /copilot/chat
    participant LLM as claude-opus-4-8<br/>(Copilot)
    participant Tools as Read-only Tools
    participant DB as SQLite (user_id scoped)

    User->>Client: Types question, hits Send
    Client->>API: POST {user_id, message, history}
    API->>API: Prepend system prompt\n(4 hardcoded honesty rules,\ntool definitions — cached AD-10)
    API->>LLM: messages + tools (SSE stream opened)

    loop Tool use loop
        LLM-->>API: tool_use block
        API->>Tools: dispatch tool
        note right of Tools: get_safe_to_spend<br/>get_confidence_score<br/>query_transactions<br/>get_spending_by_category<br/>get_upcoming_commitments
        Tools->>DB: SELECT … WHERE user_id = ?
        DB-->>Tools: rows
        Tools-->>API: tool_result
        API->>LLM: tool_result block
    end

    LLM-->>API: streaming text tokens
    API-->>Client: SSE {type:"token", text:"…"} ×N
    API-->>Client: SSE {type:"trace", sources:[…]}
    API-->>Client: SSE {type:"done"} ← always from finally block (AD-11)

    Client->>Client: Render tokens word-by-word\n+ trace chips ("Based on: Safe-to-Spend engine")
    API->>DB: INSERT chat_messages (role=assistant, trace_sources)
```

---

## 6. Database Entity Relationship Diagram

All 8 tables. Every table except `users` carries a `user_id` foreign key — no cross-user data leakage (AD-4).

```mermaid
erDiagram
    users {
        int id PK
        string email
        string password_hash
        datetime created_at
    }

    uploaded_files {
        int id PK
        int user_id FK
        string filename
        datetime upload_at
        string parse_status
    }

    transactions {
        int id PK
        int user_id FK
        int source_file_id FK
        date date
        string description_raw
        string merchant_normalized
        decimal amount
        string direction
        decimal balance_after
        string category
        string category_source
        float category_confidence
    }

    merchant_rules {
        int id PK
        int user_id FK
        string pattern
        string category
        string source
    }

    commitments {
        int id PK
        int user_id FK
        string name
        decimal amount
        int due_day
        string criticality
    }

    score_events {
        int id PK
        int user_id FK
        int score
        int delta
        string trigger_event
        string explanation
        string suggested_action
        datetime timestamp
    }

    insights {
        int id PK
        int user_id FK
        string pattern_name
        string observation
        json evidence
        string explanation
        json action_suggestions
        float confidence
        int data_months
        bool seen
        bool dismissed
    }

    chat_messages {
        int id PK
        int user_id FK
        string role
        text content
        json trace_sources
        datetime timestamp
    }

    users ||--o{ uploaded_files : "uploads"
    users ||--o{ transactions : "owns"
    users ||--o{ merchant_rules : "teaches"
    users ||--o{ commitments : "tracks"
    users ||--o{ score_events : "accrues"
    users ||--o{ insights : "receives"
    users ||--o{ chat_messages : "chats"
    uploaded_files ||--o{ transactions : "produces"
```

---

## 7. API Surface Map

13 canonical endpoints organized by domain. Every write endpoint that touches commitments returns `safe_to_spend_updated` to avoid a redundant fetch.

```mermaid
graph LR
    subgraph AUTH["Auth — /auth"]
        A1["POST /auth/register\nRegister + auto-login\nhttpOnly cookie set"]
        A2["POST /auth/login\nhttpOnly cookie set"]
        A3["POST /auth/logout\nClear session"]
    end

    subgraph STMT["Statements — /statements"]
        B1["POST /statements/upload\nUpload PDF or CSV"]
        B2["GET|WS /statements/{id}/status\nParse progress\n(WebSocket preferred, polling fallback)"]
        B3["GET /statements/{id}/transactions\nTransaction list\ncategory · confidence · badge"]
    end

    subgraph TXN["Transactions — /transactions"]
        C1["PATCH /transactions/{id}/categorise\nTeach Me correction\nwrites merchant_rules row"]
    end

    subgraph DASH["Dashboard — /dashboard"]
        D1["GET /dashboard\nSTS · Confidence Score · Briefing\nCommitments · spending_by_category"]
    end

    subgraph INS["Insights — /insights"]
        E1["GET /insights\nActive insight cards"]
        E2["POST /insights/{id}/dismiss\nDismiss insight"]
    end

    subgraph COMM["Commitments — /commitments"]
        F1["GET /commitments\nList all"]
        F2["POST /commitments\nAdd new\n→ returns safe_to_spend_updated"]
        F3["PATCH /commitments/{id}\nEdit\n→ returns safe_to_spend_updated"]
        F4["DELETE /commitments/{id}\nDelete\n→ returns safe_to_spend_updated"]
    end

    subgraph COP["Copilot — /copilot"]
        G1["POST /copilot/chat\nSSE stream\ntoken · trace · done"]
    end

    CLIENT([Browser / Reflex UI]) --> AUTH & STMT & TXN & DASH & INS & COMM & COP

    style F2 fill:#fdf2f8,stroke:#8e44ad
    style F3 fill:#fdf2f8,stroke:#8e44ad
    style F4 fill:#fdf2f8,stroke:#8e44ad
    style G1 fill:#fdedec,stroke:#e74c3c
```

---

## 8. 3-Day MVP Build Timeline — Epics & Stories

Epics are ordered by dependency. P0 stories are non-negotiable. Never-cut items are marked ★.

```mermaid
gantt
    title 3-Day MVP Build — AI-Powered Personal Finance Analyzer
    dateFormat  D
    axisFormat  Day %d

    section Day 1 — Foundation
    E1 Foundation & Auth (P0)        :crit, e1, 1, 1d
    E2 Statement Ingestion (P0)      :crit, e2, after e1, 1d
    E3 Categorization (P0)           :e3, after e2, 0.5d

    section Day 2 — Engine & UX
    E4 Financial Engine STS+CS (P0)★ :crit, e4, 2, 0.5d
    E5 Dashboard & Briefing (P0/P1)  :e5, after e4, 0.5d
    E7 Commitments Management (P1)   :e7, after e5, 0.5d
    E3 Categorization continued      :e3b, after e4, 0.5d

    section Day 3 — AI & Hardening
    E6 AI Copilot (P0/P1 must-ship)★ :crit, e6, 3, 0.75d
    E8 Proactive Insights (P1)★      :e8, 3, 0.75d
    E9 Hardening & Demo-Readiness    :e9, after e6, 0.5d
```

---

## 9. Proactive Insights — Detection Pipeline

Five deterministic pandas detectors. Each emits an evidence pack; the narrate layer adds language. SEBI IA boundary enforced at every output.

```mermaid
flowchart TD
    TXN[(transactions table\nuser_id scoped)] --> PANDAS[pandas DataFrame\nloaded in service layer]

    PANDAS --> D1[PostPaydaySpike\ndetector]
    PANDAS --> D2[DeathBySmallPurchases\ndetector]
    PANDAS --> D3[ZombieSubscriptions\ndetector]
    PANDAS --> D4[WeekendVsWeekdayPace\ndetector]
    PANDAS --> D5[UpcomingCommitmentCollision\ndetector]

    D1 & D2 & D3 & D4 & D5 --> EP["Evidence Pack per insight\npattern_name · observation\nevidence [{date, merchant, amount}]\nexplanation · action_suggestions\nconfidence · data_months"]

    EP --> NAR["services/narrate/\nclaude-opus-4-8\nO → E → E → A shape"]

    NAR --> INS[(insights table\nuser_id scoped)]

    INS --> UI["Insight cards\n(seen / dismissed lifecycle)"]

    UI --> SEBI["⚠ SEBI IA boundary\n'you might consider' — never 'you should'\n'information, never advice'"]

    style SEBI fill:#fdedec,stroke:#e74c3c,stroke-width:2px
    style D1 fill:#eafaea,stroke:#27ae60
    style D2 fill:#eafaea,stroke:#27ae60
    style D3 fill:#eafaea,stroke:#27ae60
    style D4 fill:#eafaea,stroke:#27ae60
    style D5 fill:#eafaea,stroke:#27ae60
```

---

## 10. Architecture Decision Map — Hard Boundaries

Visual summary of the 14 ADs and the two cross-cutting seams that span multiple layers.

```mermaid
graph TD
    subgraph SEAMS["Cross-Layer Seams"]
        S1["AD-4 × all layers\nuser_id on EVERY query\nNo 'reference data' exemption"]
        S2["AD-5 × AD-11\nhttpOnly cookie auth\nalso gates SSE stream\n(no URL/query-param token)"]
        S3["AD-13 × UI + charts\nformatINR + formatDate\nEVERYWHERE incl. Plotly axes"]
    end

    subgraph UI_AD["UI / State (rx.State)"]
        AD3["AD-3\nState mutates via engine only\nNo inline financial math in rx.State"]
        AD8_UI["AD-8 display\nSTS shown rounded DOWN\nto nearest ₹10"]
    end

    subgraph ING_AD["Ingestion"]
        AD6["AD-6\nCanonical Transaction schema\nas ingestion contract"]
        AD12["AD-12\nParser failure = honest refusal\nNo swallowed exceptions"]
    end

    subgraph CAT_AD["Categorization"]
        AD7["AD-7\nCategory enum hard-constraint\nPydantic Literal\nNo invented categories\nPrompt injection guard"]
    end

    subgraph ENG_AD["Engine (no LLM)"]
        AD1E["AD-1 half\nEngine never imports narrate"]
        AD8["AD-8\nSTS formula + floor + rounding\nmax(0, …) · floor(÷10)"]
        AD9["AD-9\nScore events as write path\nEvery score change = DB row\ntrigger_event column"]
    end

    subgraph NAR_AD["Narrate (LLM only)"]
        AD1N["AD-1 half\nNarrate never imports engine\nNo financial numbers computed here"]
        AD2["AD-2\nservices/ never imports reflex\nFramework-agnostic"]
    end

    subgraph COP_AD["Copilot"]
        AD10["AD-10\nRead-only tools only\n4 hardcoded honesty rules\nnon-configurable"]
        AD11["AD-11\nSSE: token · trace · done\ndone in finally block always"]
    end

    subgraph DATA_AD["Data / DB"]
        AD4["AD-4\nuser_id on every query\nIDOR prevention"]
        AD5["AD-5\nAuth token in httpOnly cookie\nnever localStorage / header"]
    end

    subgraph PHASE2["Phase-2 Boundary"]
        AD14["AD-14\npytest services/ with no Reflex\nservices/ independently importable"]
    end

    SEAMS --> UI_AD & ING_AD & CAT_AD & ENG_AD & NAR_AD & COP_AD & DATA_AD

    classDef hardBound fill:#fdedec,stroke:#e74c3c,stroke-width:2px
    class AD1E,AD1N,AD4,AD5,AD7,AD10 hardBound
```
