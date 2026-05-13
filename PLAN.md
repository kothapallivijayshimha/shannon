# Shannon — AI Security Testing Platform

## What Shannon Already Is

Shannon is an **autonomous AI pentester** built by Keygraph. It's not a simple script — it's a full platform with:

- **13 AI agents** across 5 phases (Pre-Recon → Recon → Vuln Analysis → Exploitation → Report)
- **Claude Agent SDK** integration with 3 model tiers (Haiku/Sonnet/Opus)
- **Temporal workflow orchestration** (durable, crash-recoverable, checkpoint-aware)
- **5 OWASP coverage areas**: Injection, XSS, SSRF, Auth, Authz
- **Docker-based deployment** with ephemeral worker containers
- **96% benchmark score** (XBOW security benchmark)
- **Real exploitation** — "no exploit, no report" philosophy

## What We're Building: LLM Security Testing on Top of Shannon

Shannon tests **web apps**. We extend it to test **AI systems** — the fastest-growing security gap in the market.

## The 10/10 Plan

### Phase 1: Foundation (Week 1)
- [x] Clean up local copy (git init, remove stale files)
- [x] Create GitHub repo, push
- [ ] Add `.env.example` with all config fields documented
- [ ] Write a comprehensive README for our fork

### Phase 2: LLM Agent System (Week 1-2)
New agents targeting the OWASP Top 10 for LLMs:

| Agent | What It Does | Model Tier |
|-------|-------------|------------|
| **prompt-injection-agent** | Tests prompt injection — direct, indirect, jailbreaking, role-playing attacks | Opus |
| **rag-poison-agent** | Tests RAG pipelines — poisoned context, document injection, retrieval manipulation | Sonnet |
| **tool-abuse-agent** | Tests tool/function calling — parameter manipulation, tool chaining, privilege escalation via tools | Sonnet |
| **data-exfil-agent** | Tests data leakage — unintended output exposure, training data extraction, system prompt leakage | Sonnet |
| **model-enum-agent** | Enumerates model capabilities — discovers exposed functions, system prompts, backend models | Haiku |

### Phase 3: Infrastructure (Week 2)
- Add Docker Compose for local dev (no Temporal dependency needed for single-agent runs)
- Create a lightweight "agent mode" — run individual LLM security agents without the full 5-phase pipeline
- Add support for common LLM targets (OpenAI, Claude, local models via Ollama/LiteLLM)

### Phase 4: Delivery (Week 2-3)
- Add structured output schemas for LLM vulnerabilities
- LLM-specific report templates
- Demo against a vulnerable LLM target (like a custom GPT or AI chatbot)
- Tests for the LLM agent system

## Why This Is High Yield

1. **AI adoption is outpacing AI security** — every company shipping AI features needs this yesterday
2. **No serious competitor** — nobody has a ready-to-use LLM red-teaming tool with real exploitation
3. **Built on proven infra** — Shannon's Temporal + Claude SDK stack is production-grade
4. **$50/scan cost point** — trivial compared to hiring human AI red-teamers ($5k-$20k/engagement)
5. **First mover advantage** — the OWASP Top 10 for LLMs is still stabilizing, the tooling space is wide open

## The End Goal
A CLI tool where you run:
```bash
npx shannon-ai scan --target https://my-ai-app.com --llm-endpoint https://api.openai.com
```
And get back a pentest report with confirmed, reproducible AI vulnerabilities — prompt injections that work, RAG poisonings that exfiltrate data, tool abuses that escalate privileges.
