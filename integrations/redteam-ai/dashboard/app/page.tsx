"use client";

import { useState, useEffect, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ─── Types ────────────────────────────────────────────────────────────────── */
type Phase = { key: string; label: string; color: string; icon: string };

/* ─── Constants ────────────────────────────────────────────────────────────── */
const PHASES: Phase[] = [
  { key: "recon",        label: "Recon",        color: "#3B82F6", icon: "⬡" },
  { key: "web_app",      label: "Web App",      color: "#8B5CF6", icon: "◈" },
  { key: "vuln_scan",    label: "Vuln Scan",    color: "#F59E0B", icon: "⚠" },
  { key: "exploitation", label: "Exploit",      color: "#EF4444", icon: "⚡" },
  { key: "password",     label: "Password",     color: "#EC4899", icon: "⬤" },
  { key: "post_exploit", label: "Post-Exploit", color: "#14B8A6", icon: "≋" },
  { key: "wireless",     label: "Wireless",     color: "#F97316", icon: "◉" },
  { key: "forensics",    label: "Forensics",    color: "#6366F1", icon: "⊛" },
];

const QUICK_ACTIONS = [
  { label: "Full Pentest",  task: "full pentest",    color: "#00ff87", icon: "⬡", desc: "Complete pipeline" },
  { label: "Recon",         task: "recon",           color: "#3B82F6", icon: "◈", desc: "Subdomain enumeration" },
  { label: "Web App Audit", task: "web_app",         color: "#8B5CF6", icon: "◍", desc: "OWASP Top-10 checks" },
  { label: "Vuln Scan",     task: "vuln_scan",       color: "#F59E0B", icon: "⚠", desc: "CVE & misconfig scan" },
  { label: "Exploitation",  task: "exploitation",    color: "#EF4444", icon: "⚡", desc: "Active exploitation" },
  { label: "Password Atk",  task: "password",        color: "#EC4899", icon: "⬤", desc: "Credential attacks" },
];

/* ─── Helpers ────────────────────────────────────────────────────────────── */
function phaseIndex(key: string | null) {
  if (!key) return -1;
  return PHASES.findIndex((p) => p.key === key);
}

/* ─── Component ──────────────────────────────────────────────────────────── */
export default function Home() {
  const [target, setTarget]         = useState("");
  const [customTask, setCustomTask] = useState("");
  const [result, setResult]         = useState<string | null>(null);
  const [loading, setLoading]       = useState(false);
  const [activePhase, setActivePhase] = useState<string | null>(null);
  const [logLines, setLogLines]     = useState<string[]>([]);
  const [scanId, setScanId]         = useState<string | null>(null);
  const terminalRef = useRef<HTMLDivElement>(null);

  /* Auto-scroll terminal */
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logLines]);

  async function runAgent(taskText: string) {
    if (!target) return;
    setLoading(true);
    setResult(null);
    setActivePhase(null);
    const id = crypto.randomUUID().slice(0, 8).toUpperCase();
    setScanId(id);
    const ts = () => new Date().toISOString().slice(11, 19);
    setLogLines([
      `[${ts()}] SESSION ${id} — initialising`,
      `[${ts()}] TARGET   → ${target}`,
      `[${ts()}] TASK     → ${taskText}`,
      `[${ts()}] Routing intent through AI planner...`,
    ]);
    try {
      const res = await fetch(`${API}/agent?task=${encodeURIComponent(taskText + " " + target)}`);
      const data = await res.json();
      const finalPhase =
        data.phases_covered?.[data.phases_covered.length - 1] ?? data.phase ?? null;
      setActivePhase(finalPhase);
      setResult(JSON.stringify(data, null, 2));
      setLogLines((prev) => [
        ...prev,
        `[${ts()}] Response received from orchestrator`,
        `[${ts()}] Phase resolved → ${finalPhase ?? "orchestrator"}`,
        `[${ts()}] STATUS ✓ COMPLETE`,
      ]);
    } catch (e) {
      setResult(`Error: ${e}`);
      setLogLines((prev) => [...prev, `[${ts()}] ERROR — ${e}`]);
    } finally {
      setLoading(false);
    }
  }

  const activePIdx = phaseIndex(activePhase);

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "32px 24px", display: "flex", flexDirection: "column", gap: "32px" }}>

      {/* ── Hero Header ─────────────────────────────────────────────────── */}
      <div
        className="slide-up"
        style={{ textAlign: "center", padding: "48px 24px 40px", position: "relative", overflow: "hidden" }}
      >
        {/* Glowing background blobs */}
        <div style={{
          position: "absolute", top: "20%", left: "50%", transform: "translateX(-50%)",
          width: "600px", height: "200px",
          background: "radial-gradient(ellipse, rgba(0,255,135,0.06) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            padding: "4px 14px",
            borderRadius: "20px",
            background: "rgba(0,255,135,0.06)",
            border: "1px solid rgba(0,255,135,0.15)",
            fontSize: "11px",
            fontFamily: "monospace",
            color: "#00ff87",
            marginBottom: "20px",
            letterSpacing: "0.1em",
          }}
        >
          <span className="pulse-dot" style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: "#00ff87" }} />
          AUTONOMOUS SECURITY ASSESSMENT ENGINE
        </div>
        <h1
          style={{
            fontSize: "clamp(36px, 5vw, 58px)",
            fontWeight: 900,
            letterSpacing: "-1.5px",
            lineHeight: 1.05,
            marginBottom: "12px",
            background: "linear-gradient(135deg, #f0f4f8 30%, rgba(240,244,248,0.5))",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          KVS{" "}
          <span
            style={{
              background: "linear-gradient(135deg, #00ff87, #00c96a)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              textShadow: "none",
              filter: "drop-shadow(0 0 20px rgba(0,255,135,0.4))",
            }}
          >
            Red Team
          </span>{" "}
          AI
        </h1>
        <p style={{ color: "#7a8a9a", fontSize: "15px", maxWidth: "480px", margin: "0 auto" }}>
          50+ integrated security tools. AI-driven intent routing. Fully autonomous pipeline.
        </p>
      </div>

      {/* ── Target Input Section ─────────────────────────────────────────── */}
      <div
        className="glass gradient-border slide-up"
        style={{ borderRadius: "16px", padding: "28px", animationDelay: "0.05s" }}
      >
        <div style={{ marginBottom: "16px", display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ width: "3px", height: "20px", background: "#00ff87", borderRadius: "2px" }} />
          <span style={{ fontSize: "12px", fontWeight: 600, color: "#7a8a9a", textTransform: "uppercase", letterSpacing: "0.1em" }}>
            Target Configuration
          </span>
        </div>

        <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
          <div style={{ flex: "2 1 260px", position: "relative" }}>
            <span style={{
              position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)",
              fontSize: "12px", color: "#3d4f60", fontFamily: "monospace", pointerEvents: "none",
            }}>$</span>
            <input
              className="rt-input"
              style={{ paddingLeft: "28px" }}
              placeholder="target.com · 10.0.0.1 · 192.168.1.0/24"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && target && runAgent(customTask || `full pentest`)}
              id="target-input"
            />
          </div>
          <input
            className="rt-input"
            style={{ flex: "2 1 220px" }}
            placeholder="Custom task (optional)"
            value={customTask}
            onChange={(e) => setCustomTask(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && target && runAgent(customTask || `full pentest`)}
            id="task-input"
          />
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            className="btn-primary"
            onClick={() => runAgent(`full pentest`)}
            disabled={loading || !target}
            id="btn-full-pentest"
          >
            {loading ? (
              <>
                <span style={{ display: "inline-block", width: "12px", height: "12px", border: "2px solid #000", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.6s linear infinite" }} />
                Running...
              </>
            ) : (
              <> ⚡ Full Pentest </>
            )}
          </button>
          <button
            className="btn-secondary"
            onClick={() => runAgent(customTask || `recon`)}
            disabled={loading || !target}
            id="btn-run-task"
          >
            ▷ Run Task
          </button>
          {result && (
            <button
              className="btn-secondary"
              onClick={() => { setResult(null); setLogLines([]); setActivePhase(null); }}
              id="btn-clear"
            >
              ✕ Clear
            </button>
          )}
        </div>
      </div>

      {/* ── Assessment Pipeline ──────────────────────────────────────────── */}
      <div className="slide-up" style={{ animationDelay: "0.1s" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ width: "3px", height: "20px", background: "linear-gradient(180deg,#3B82F6,#8B5CF6)", borderRadius: "2px" }} />
            <span style={{ fontSize: "12px", fontWeight: 600, color: "#7a8a9a", textTransform: "uppercase", letterSpacing: "0.1em" }}>
              Assessment Pipeline
            </span>
          </div>
          {activePhase && (
            <span style={{ fontSize: "11px", fontFamily: "monospace", color: "#00ff87" }}>
              Active: {activePhase}
            </span>
          )}
        </div>

        <div
          className="glass"
          style={{ borderRadius: "12px", padding: "20px 24px" }}
        >
          <div
            className="phase-flow"
            style={{ display: "flex", alignItems: "center", overflowX: "auto", paddingBottom: "4px", gap: 0 }}
          >
            {PHASES.map((phase, i) => {
              const done   = activePIdx >= 0 && i <= activePIdx;
              const active = activePhase === phase.key;
              return (
                <div key={phase.key} style={{ display: "flex", alignItems: "center", flexShrink: 0 }}>
                  <button
                    title={phase.label}
                    id={`phase-btn-${phase.key}`}
                    onClick={() => runAgent(phase.key + " scan")}
                    disabled={loading || !target}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "8px",
                      padding: "10px 12px",
                      background: "none",
                      border: "none",
                      cursor: target ? "pointer" : "default",
                      opacity: done || active ? 1 : 0.35,
                      transition: "all 0.25s",
                      transform: active ? "scale(1.1)" : "scale(1)",
                    }}
                  >
                    <div
                      style={{
                        width: "44px",
                        height: "44px",
                        borderRadius: "50%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "16px",
                        fontWeight: 700,
                        border: `2px solid ${phase.color}`,
                        background: done || active ? phase.color : "transparent",
                        color: done || active ? "#000" : phase.color,
                        boxShadow: active ? `0 0 24px ${phase.color}60, 0 0 8px ${phase.color}40` : done ? `0 0 12px ${phase.color}30` : "none",
                        transition: "all 0.3s",
                      }}
                    >
                      {active && loading ? (
                        <span style={{ fontSize: "10px", animation: "spin 1s linear infinite", display: "inline-block" }}>↻</span>
                      ) : (
                        phase.icon
                      )}
                    </div>
                    <span
                      style={{
                        fontSize: "9.5px",
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                        color: active ? phase.color : done ? phase.color : "#7a8a9a",
                        fontFamily: "monospace",
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                      }}
                    >
                      {phase.label}
                    </span>
                  </button>
                  {i < PHASES.length - 1 && (
                    <div className="phase-connector" style={{ color: phase.color }} />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Quick Actions Grid ───────────────────────────────────────────── */}
      <div className="slide-up" style={{ animationDelay: "0.15s" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
          <div style={{ width: "3px", height: "20px", background: "linear-gradient(180deg,#F59E0B,#EF4444)", borderRadius: "2px" }} />
          <span style={{ fontSize: "12px", fontWeight: 600, color: "#7a8a9a", textTransform: "uppercase", letterSpacing: "0.1em" }}>
            Quick Actions
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "10px" }}>
          {QUICK_ACTIONS.map((q) => (
            <button
              key={q.task}
              id={`quick-${q.task}`}
              className="glass gradient-border"
              onClick={() => runAgent(q.task)}
              disabled={loading || !target}
              style={{
                textAlign: "left",
                padding: "16px",
                border: `1px solid ${q.color}18`,
                borderRadius: "12px",
                cursor: target ? "pointer" : "not-allowed",
                opacity: !target ? 0.4 : 1,
                transition: "all 0.2s",
                background: "none",
              }}
              onMouseEnter={(e) => {
                if (!target) return;
                (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
                (e.currentTarget as HTMLElement).style.borderColor = q.color + "40";
                (e.currentTarget as HTMLElement).style.boxShadow = `0 8px 24px ${q.color}15`;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
                (e.currentTarget as HTMLElement).style.borderColor = q.color + "18";
                (e.currentTarget as HTMLElement).style.boxShadow = "none";
              }}
            >
              <div style={{ fontSize: "20px", marginBottom: "8px", color: q.color }}>{q.icon}</div>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#f0f4f8", marginBottom: "3px" }}>{q.label}</div>
              <div style={{ fontSize: "11px", color: "#7a8a9a" }}>{q.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Terminal / Results ───────────────────────────────────────────── */}
      {(logLines.length > 0 || loading) && (
        <div className="terminal slide-up" style={{ animationDelay: "0.05s" }}>
          {/* Terminal header */}
          <div className="terminal-header">
            <div className="terminal-dot" style={{ background: "#ff5f57" }} />
            <div className="terminal-dot" style={{ background: "#ffbd2e" }} />
            <div className="terminal-dot" style={{ background: "#28c840" }} />
            <span style={{ fontSize: "11px", color: "#3d4f60", fontFamily: "monospace", marginLeft: "8px" }}>
              redteam-ai — session {scanId}
            </span>
            {loading && (
              <span style={{ marginLeft: "auto", fontSize: "10px", color: "#00ff87", fontFamily: "monospace" }}>
                ● LIVE
              </span>
            )}
          </div>

          {/* Log lines */}
          <div
            ref={terminalRef}
            style={{ padding: "16px", maxHeight: "220px", overflowY: "auto" }}
          >
            {logLines.map((line, i) => (
              <div
                key={i}
                style={{
                  marginBottom: "4px",
                  color: line.includes("ERROR") ? "#ff3b3b"
                       : line.includes("✓ COMPLETE") ? "#00ff87"
                       : line.includes("→") ? "#e0f0ff"
                       : "#9fcfb0",
                }}
              >
                {line}
              </div>
            ))}
            {loading && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#7a8a9a" }}>
                <span style={{ animation: "blink 1s step-end infinite" }}>█</span>
                awaiting response...
              </div>
            )}
          </div>

          {/* JSON Result */}
          {result && !loading && (
            <>
              <div style={{ borderTop: "1px solid rgba(0,255,135,0.08)", padding: "10px 16px", display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "10px", fontFamily: "monospace", color: "#00ff87" }}>JSON OUTPUT</span>
                <button
                  onClick={() => navigator.clipboard.writeText(result)}
                  style={{
                    marginLeft: "auto", fontSize: "10px", color: "#7a8a9a",
                    background: "none", border: "none", cursor: "pointer", fontFamily: "monospace",
                  }}
                >
                  copy
                </button>
              </div>
              <pre
                style={{
                  padding: "16px",
                  maxHeight: "400px",
                  overflowY: "auto",
                  overflowX: "auto",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  fontSize: "11.5px",
                  lineHeight: "1.7",
                  color: "#9fcfb0",
                  borderTop: "1px solid rgba(0,255,135,0.08)",
                  margin: 0,
                }}
              >
                {result}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}
