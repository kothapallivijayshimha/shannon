# Phase 1 Research and Requirements Baseline

## Scope

This baseline extends Shannon's existing white-box web application and API
pentesting workflow toward security testing for AI-enabled, edge, IoT, and
cloud-native systems. It does not authorize testing systems without explicit
ownership or written rules of engagement.

## Current Platform Constraints

- Shannon uses TypeScript, Temporal workflows, Docker workers, and audited
  agent execution.
- Existing exploitation is evidence-driven: a finding requires a reproducible
  proof of concept.
- The integrated RedTeam AI service is a separate FastAPI/Celery/Redis/Next.js
  application and should communicate through versioned contracts rather than
  importing Shannon internals.
- Model providers include Anthropic-compatible endpoints, AWS Bedrock, Google
  Vertex, and local Ollama deployments.

## Initial Use Cases

### AI application security

- Direct and indirect prompt injection.
- RAG document poisoning and retrieval manipulation.
- Tool-call parameter tampering, unsafe chaining, and privilege escalation.
- System prompt, secret, and sensitive-data disclosure.
- Model capability and endpoint enumeration.

### Edge, IoT, and cloud-native security

- Validate exposed management interfaces and weak device authentication.
- Correlate service, container, and gateway telemetry with confirmed findings.
- Test authorization boundaries between tenants, workloads, and devices.
- Exercise approved containment playbooks in an isolated testbed.

### 5G and future-network readiness

Treat 5G/6G protocols and network functions as integration boundaries. The
first milestone is protocol-agnostic telemetry and policy contracts; protocol
specific scanners should be added only with a reproducible lab environment.

### Cryptographic migration

Inventory algorithms, key lifetimes, and protocol dependencies. Report
quantum-readiness gaps using deterministic policy and approved NIST post-quantum
algorithm metadata. An LLM may explain migration options but must not select
cryptographic primitives autonomously.

## Threat Model

| Actor or failure | Example | Required control |
| --- | --- | --- |
| Malicious target input | Prompt injection or poisoned retrieved content | Isolated context, tool allowlists, evidence validation |
| Compromised tool | A scanner returns malicious output | Container isolation, output size limits, provenance |
| Model failure | Hallucinated vulnerability or unsafe action | Deterministic validators, human approval, no-evidence-no-report |
| Telemetry attacker | Spoofed or replayed device events | Authenticated ingestion, timestamps, source identity |
| Insider or tenant escape | Cross-workspace data access | Per-run credentials, workspace isolation, audit logs |
| Model/data poisoning | Crafted training or feedback examples | Trusted datasets, provenance, drift and review gates |
| Privacy breach | Raw device or user data leaves an edge node | Redaction, data classification, local processing, retention limits |

## Data Classification

- **Public:** tool metadata, generic vulnerability taxonomy, anonymized metrics.
- **Internal:** model prompts, agent traces, configuration, architecture data.
- **Confidential:** source code, telemetry, target identifiers, findings, PoCs.
- **Restricted:** credentials, session tokens, personal data, private keys.

Restricted data must not be included in prompts or telemetry exports unless a
documented, approved redaction exception exists. Secrets are passed through
runtime configuration and must never be written to reports or audit messages.

## Success Metrics

Phase 1 establishes targets; Phase 2 and later must add measurement
instrumentation and test fixtures.

| Metric | Target | Measurement |
| --- | --- | --- |
| Known-pattern detection latency | Less than 2 seconds | Ingest timestamp to alert timestamp |
| Approved containment latency | Less than 30 seconds | Policy approval to completed action |
| False-positive rate | At most 5 percent | Labeled validation corpus |
| True-positive rate | At least 90 percent | Controlled red-team testbed |
| High-severity explanation coverage | 100 percent | Finding schema validation |
| Explanation length | At least 150 characters | Deterministic report validator |
| Model drift | Less than 2 percent monthly | Fixed evaluation set |
| Critical framework defects | Zero open critical issues | Security review and dependency scans |

## Research Decisions

1. Keep Temporal as the durable control plane and use an event-bus adapter for
   external telemetry.
2. Start with JSON Schema and TypeScript types; add Protobuf when a second
   independently deployed consumer requires it.
3. Support NATS or Kafka behind an interface, but provide an in-memory adapter
   for deterministic tests.
4. Use local Ollama inference for edge development and provider-neutral
   capability checks for hosted models.
5. Defer autonomous containment until policy, approval, rollback, and audit
   contracts are implemented and tested.

## Phase 1 Exit Criteria

- Requirements are versioned and reviewed.
- Threat model and data classifications are documented.
- Metrics have owners, targets, and measurement definitions.
- Rules of engagement and human approval boundaries are explicit.
- Phase 2 contracts can be designed without introducing provider-specific
  assumptions.

