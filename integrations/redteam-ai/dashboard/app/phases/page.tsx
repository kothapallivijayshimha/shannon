"use client";

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ─── Types ─────────────────────────────────────────────────────────────── */
type PhaseEntry = {
  id: number;
  domain: string;
  phase: string;
  status: string;
  result: string;
  created_at: string;
};

/* ─── Constants ─────────────────────────────────────────────────────────── */
const PHASE_META: Record<string, { label: string; color: string; icon: string }> = {
  recon:        { label: "Recon",        color: "#3B82F6", icon: "⬡" },
  web_app:      { label: "Web App",      color: "#8B5CF6", icon: "◈" },
  vuln_scan:    { label: "Vuln Scan",    color: "#F59E0B", icon: "⚠" },
  exploitation: { label: "Exploit",      color: "#EF4444", icon: "⚡" },
  password:     { label: "Password",     color: "#EC4899", icon: "⬤" },
  post_exploit: { label: "Post-Exploit", color: "#14B8A6", icon: "≋" },
  wireless:     { label: "Wireless",     color: "#F97316", icon: "◉" },
  forensics:    { label: "Forensics",    color: "#6366F1", icon: "⊛" },
  orchestrator: { label: "Orchestrator", color: "#6B7280", icon: "⬡" },
};

const STATUS_META: Record<string, { label: string; badgeClass: string; dot: string }> = {
  completed: { label: "Done",    badgeClass: "badge badge-completed", dot: "#00ff87" },
  failed:    { label: "Failed",  badgeClass: "badge badge-failed",    dot: "#ff3b3b" },
  timeout:   { label: "Timeout", badgeClass: "badge badge-timeout",   dot: "#f59e0b" },
  skipped:   { label: "Skipped", badgeClass: "badge badge-skipped",   dot: "#6b7280" },
  queued:    { label: "Queued",  badgeClass: "badge badge-queued",    dot: "#3b82f6" },
};

/* ─── Phase Row ─────────────────────────────────────────────────────────── */
function PhaseRow({ entry, isOpen, onToggle }: { entry: PhaseEntry; isOpen: boolean; onToggle: () => void }) {
  const pMeta = PHASE_META[entry.phase] || { label: entry.phase, color: "#6B7280", icon: "◈" };
  const sMeta = STATUS_META[entry.status] || { label: entry.status, badgeClass: "badge badge-skipped", dot: "#6B7280" };

  const formattedJson = (() => {
    try { return JSON.stringify(JSON.parse(entry.result), null, 2); }
    catch { return entry.result || "No data"; }
  })();

  return (
    <div>
      <button
        onClick={onToggle}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          gap: "14px",
          padding: "12px 20px",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
          transition: "background 0.15s",
          color: "inherit",
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.02)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "none"; }}
      >
        {/* Phase dot */}
        <div
          style={{
            width: "28px",
            height: "28px",
            borderRadius: "50%",
            border: `1.5px solid ${pMeta.color}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "12px",
            color: pMeta.color,
            flexShrink: 0,
          }}
        >
          {pMeta.icon}
        </div>

        {/* Phase name */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "13px", fontWeight: 600, fontFamily: "monospace", color: "#f0f4f8" }}>
            {pMeta.label}
          </div>
          <div style={{ fontSize: "10px", color: "#3d4f60", fontFamily: "monospace" }}>
            {entry.created_at?.replace("T", " ").slice(0, 19) ?? "—"}
          </div>
        </div>

        {/* Status badge */}
        <span className={sMeta.badgeClass}>{sMeta.label}</span>

        {/* Chevron */}
        <span
          style={{
            fontSize: "12px",
            color: "#3d4f60",
            transition: "transform 0.2s",
            transform: isOpen ? "rotate(90deg)" : "rotate(0deg)",
          }}
        >
          ›
        </span>
      </button>

      {/* Expanded JSON */}
      {isOpen && (
        <div
          className="fade-in"
          style={{
            borderTop: "1px solid rgba(255,255,255,0.04)",
            background: "#020a0e",
            position: "relative",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 16px",
              borderBottom: "1px solid rgba(0,255,135,0.06)",
            }}
          >
            <span style={{ fontSize: "9px", fontFamily: "monospace", color: "#3d4f60", textTransform: "uppercase", letterSpacing: "0.1em" }}>
              JSON Result
            </span>
            <button
              onClick={() => navigator.clipboard.writeText(formattedJson)}
              style={{ marginLeft: "auto", fontSize: "10px", color: "#7a8a9a", background: "none", border: "none", cursor: "pointer", fontFamily: "monospace" }}
            >
              copy
            </button>
          </div>
          <pre
            style={{
              padding: "16px",
              maxHeight: "320px",
              overflowY: "auto",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              fontSize: "11px",
              lineHeight: 1.7,
              color: "#9fcfb0",
              fontFamily: "monospace",
              margin: 0,
            }}
          >
            {formattedJson}
          </pre>
        </div>
      )}
    </div>
  );
}

/* ─── Target Card ───────────────────────────────────────────────────────── */
function TargetCard({ domain, entries }: { domain: string; entries: PhaseEntry[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const done = entries.filter((e) => e.status === "completed").length;
  const pct  = Math.round((done / entries.length) * 100);

  return (
    <div
      className="glass"
      style={{ borderRadius: "14px", overflow: "hidden", transition: "border-color 0.2s" }}
    >
      {/* Target header */}
      <div
        style={{
          padding: "16px 20px",
          background: "linear-gradient(90deg, rgba(0,255,135,0.04), transparent)",
          borderBottom: "1px solid rgba(255,255,255,0.05)",
          display: "flex",
          alignItems: "center",
          gap: "14px",
        }}
      >
        {/* Animated dot */}
        <span
          className="pulse-dot"
          style={{
            display: "inline-block",
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: done === entries.length ? "#00ff87" : "#3B82F6",
            boxShadow: done === entries.length ? "0 0 10px rgba(0,255,135,0.5)" : "0 0 10px rgba(59,130,246,0.5)",
            flexShrink: 0,
          }}
        />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: "monospace", fontWeight: 700, fontSize: "14px", color: "#f0f4f8" }}>
            {domain}
          </div>
          <div style={{ fontSize: "11px", color: "#7a8a9a", marginTop: "2px" }}>
            {done}/{entries.length} phases complete
          </div>
        </div>

        {/* Progress pill */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "80px",
              height: "4px",
              background: "rgba(255,255,255,0.06)",
              borderRadius: "2px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${pct}%`,
                background: done === entries.length
                  ? "linear-gradient(90deg,#00c96a,#00ff87)"
                  : "linear-gradient(90deg,#3B82F6,#8B5CF6)",
                borderRadius: "2px",
                transition: "width 0.5s ease",
              }}
            />
          </div>
          <span
            style={{
              fontSize: "11px",
              fontFamily: "monospace",
              color: done === entries.length ? "#00ff87" : "#7a8a9a",
              minWidth: "32px",
            }}
          >
            {pct}%
          </span>
        </div>
      </div>

      {/* Phase entries */}
      <div style={{ divideColor: "rgba(255,255,255,0.04)" }}>
        {entries.map((entry, idx) => (
          <div key={entry.id} style={{ borderBottom: idx < entries.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none" }}>
            <PhaseRow
              entry={entry}
              isOpen={expanded === entry.id}
              onToggle={() => setExpanded(expanded === entry.id ? null : entry.id)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Page ──────────────────────────────────────────────────────────────── */
export default function PhasesPage() {
  const [phases, setPhases]   = useState<PhaseEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter]   = useState<"all" | "completed" | "failed">("all");

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/phases`)
      .then((r) => r.json())
      .then((d) => setPhases(d.phases || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const grouped: Record<string, PhaseEntry[]> = {};
  for (const p of phases) {
    if (!grouped[p.domain]) grouped[p.domain] = [];
    grouped[p.domain].push(p);
  }

  const filteredDomains = Object.entries(grouped).filter(([, entries]) => {
    if (filter === "completed") return entries.every((e) => e.status === "completed");
    if (filter === "failed")    return entries.some((e) => e.status === "failed");
    return true;
  });

  const totalScans     = Object.keys(grouped).length;
  const completedScans = Object.values(grouped).filter((entries) => entries.every((e) => e.status === "completed")).length;

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "32px 24px", display: "flex", flexDirection: "column", gap: "28px" }}>

      {/* Header */}
      <div className="slide-up" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <div style={{ width: "3px", height: "20px", background: "linear-gradient(180deg,#14B8A6,#6366F1)", borderRadius: "2px" }} />
            <span style={{ fontSize: "12px", fontWeight: 600, color: "#7a8a9a", textTransform: "uppercase", letterSpacing: "0.1em" }}>
              History
            </span>
          </div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, letterSpacing: "-0.5px", margin: 0, color: "#f0f4f8" }}>
            Assessment History
          </h1>
          <p style={{ fontSize: "13px", color: "#7a8a9a", margin: "4px 0 0" }}>
            Pipeline execution records grouped by target
          </p>
        </div>

        {/* Filter pills */}
        {phases.length > 0 && (
          <div style={{ display: "flex", gap: "8px" }}>
            {(["all", "completed", "failed"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={{
                  padding: "6px 14px",
                  borderRadius: "8px",
                  fontSize: "12px",
                  fontWeight: 600,
                  fontFamily: "monospace",
                  border: "1px solid",
                  cursor: "pointer",
                  transition: "all 0.15s",
                  textTransform: "capitalize",
                  background: filter === f ? "rgba(255,255,255,0.06)" : "transparent",
                  borderColor: filter === f ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.06)",
                  color: filter === f ? "#f0f4f8"
                       : f === "failed" ? "#ff3b3b"
                       : f === "completed" ? "#00ff87"
                       : "#7a8a9a",
                }}
              >
                {f}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Stats */}
      {!loading && phases.length > 0 && (
        <div
          className="slide-up"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
            gap: "10px",
            animationDelay: "0.05s",
          }}
        >
          {[
            { label: "Total Targets", value: totalScans, color: "#00ff87" },
            { label: "Completed",     value: completedScans, color: "#14B8A6" },
            { label: "Total Phases",  value: phases.length, color: "#3B82F6" },
            {
              label: "Success Rate",
              value: phases.length
                ? `${Math.round((phases.filter((p) => p.status === "completed").length / phases.length) * 100)}%`
                : "—",
              color: "#8B5CF6",
            },
          ].map((s) => (
            <div key={s.label} className="stat-card" style={{ borderColor: s.color + "15" }}>
              <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && phases.length === 0 && (
        <div
          className="glass slide-up"
          style={{
            borderRadius: "16px",
            padding: "80px 40px",
            textAlign: "center",
            animationDelay: "0.1s",
          }}
        >
          <div style={{ fontSize: "48px", marginBottom: "16px", opacity: 0.3 }}>≋</div>
          <p style={{ fontSize: "16px", fontWeight: 600, color: "#7a8a9a", marginBottom: "8px" }}>
            No assessments yet
          </p>
          <p style={{ fontSize: "13px", color: "#3d4f60" }}>
            Run a full pipeline from the Assess page to see history here.
          </p>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="glass shimmer" style={{ borderRadius: "14px", height: "100px" }} />
          ))}
        </div>
      )}

      {/* Target cards */}
      {!loading && (
        <div
          className="slide-up"
          style={{ display: "flex", flexDirection: "column", gap: "14px", animationDelay: "0.1s" }}
        >
          {filteredDomains.map(([domain, entries]) => (
            <TargetCard key={domain} domain={domain} entries={entries} />
          ))}
        </div>
      )}
    </div>
  );
}
