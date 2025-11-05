# Salon AI Supervisor - Human-in-the-Loop Agent System

AI phone agent with supervisor escalation, automatic knowledge base learning, and customer follow-up.

## Quick Start

### Prerequisites
- Python 3.11+
- uv (Python package manager)
- LiveKit Cloud account (free tier)

### Setup

1. **Install dependencies**
```bash
uv sync
```

2. **Configure environment**
```bash
cp .env.example .env
# Add your LiveKit credentials:
# LIVEKIT_API_KEY=your_key
# LIVEKIT_API_SECRET=your_secret
# LIVEKIT_URL=wss://your-project.livekit.cloud
```

3. **Run services**

Terminal 1 - FastAPI server:
```bash
uv run uvicorn src.main:app --reload
```

Terminal 2 - LiveKit agent:
```bash
uv run python -m src.services.agent start
```

### Access Points
- **Admin Panel**: http://127.0.0.1:8000/static/admin_panel.html
- **Call Simulator**: http://127.0.0.1:8000/static/phone_call_sim.html
- **API Docs**: http://127.0.0.1:8000/docs

## Architecture

### Core Flow
```
Customer Call → AI Agent → Knowledge Base Check
                    ↓ (no answer)
              Escalate to Supervisor
                    ↓
            Supervisor Responds via UI
                    ↓
        Follow-up to Customer + Update KB
```

### Project Structure
```
src/
├── services/          # Business logic
│   ├── agent.py       # LiveKit agent w/ escalation
│   ├── help_request.py
│   └── knowledge_base.py
├── routers/           # FastAPI endpoints
├── models/            # Pydantic schemas
├── core/              # Config, logging, DI
├── static/            # Admin UI (HTML)
└── database/          # SQL schemas (reference)
```

## Design Decisions

### 1. Database Schema
**Tables:**
- `help_requests` - Request lifecycle (pending → resolved/unresolved)
- `knowledge_base` - Learned Q&A with usage tracking
- `request_kb_mapping` - Links requests to KB entries

**Key Features:**
- Priority levels (normal/high/urgent)
- Supervisor attribution (`supervisor_id`)
- Follow-up tracking (`follow_up_attempts`, `follow_up_method`)
- Soft deletes (`is_active`)
- Quality metrics (`confidence_score`, feedback counters)

### 2. Scalability Path
**Current (Demo):**
- SQLite - simple, no setup
- Synchronous operations
- In-memory caching

**Production (1k+ requests/day):**
- PostgreSQL (Supabase/RDS)
- Redis for hot KB entries
- Message queue (SQS) for async follow-ups
- Vector DB (Pinecone/pgvector) for semantic search
- Connection pooling

### 3. Modularity
**Easy extensions:**
- Phase 2: Live supervisor transfer (add Twilio conference)
- Phase 3: Multi-channel (SMS, web chat)
- Phase 4: Analytics dashboard
- Services are decoupled via dependency injection

### 4. Knowledge Base Strategy
**V1 (Current):**
- Keyword matching with LIKE queries
- Usage-based ranking

**Future Improvements:**
- Semantic search with embeddings (OpenAI/Cohere)
- Cache top 20 KB hits in Redis (80/20 rule)
- Feedback loop adjusts `confidence_score`
- A/B test multiple answers

## Prompt Engineering

### Agent System Prompt
Located in `src/services/agent.py`:

**Structure:**
1. **Role definition** - Clear identity and boundaries
2. **Business context** - Salon hours, services, pricing
3. **Escalation rules** - Specific triggers (pricing, availability, custom)
4. **Response format** - Concise, friendly, professional
5. **Examples** - Few-shot for edge cases

**Key Techniques Used:**
- CoT reasoning for escalation
- Explicit boundaries (what NOT to do)
- Structured output for API calls
- Temperature = 0.7 (balance consistency + naturalness)

### Room for Improvement
1. **Dynamic context injection** - Pull KB answers into prompt
2. **Conversation memory** - Track multi-turn context
3. **Sentiment detection** - Escalate frustrated callers faster
4. **A/B test prompts** - Track resolution rates by variant

## Testing

### Manual Testing Flow
1. Start both services
2. Open call simulator
3. Test scenarios:
   - Known question: "What are your hours?" (KB hit)
   - Unknown: "Do you do keratin treatments?" (escalate)
   - Urgent: "I need an appointment today!" (high priority)
4. Resolve in admin panel
5. Repeat same question (should use KB now)

## Future Enhancements

1. **Vector search** - Semantic KB matching (>60% improvement expected)
2. **Twilio integration** - Real SMS follow-ups
3. **Analytics dashboard** - Supervisor performance, agent learning curve
4. **Multi-language** - i18n for prompts + KB
5. **Voice cloning** - Consistent brand voice (ElevenLabs)
6. **Sentiment analysis** - Proactive escalation for frustration
7. **Live handoff** - Transfer to human agent mid-call

## Notes

- Uses LiveKit for voice agent framework (per assessment requirement)
- Simulates SMS via console logs (production would use Twilio)
- SQLite chosen for demo simplicity (production = PostgreSQL)
- Admin UI is functional, not polished (internal tool focus)
- All services can run independently (testable)