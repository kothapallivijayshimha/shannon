"use client";

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ─── Types ─────────────────────────────────────────────────────────────── */
type ToolInfo = {
  name: string;
  phase: string;
  description: string;
  timeout: number;
  priority: number;
};

/* ─── Constants ─────────────────────────────────────────────────────────── */
const PHASE_META: Record<string, { label: string; color: string; icon: string }> = {
  recon:        { label: "Reconnaissance",    color: "#3B82F6", icon: "⬡" },
  web_app:      { label: "Web App",           color: "#8B5CF6", icon: "◈" },
  vuln_scan:    { label: "Vuln Scan",         color: "#F59E0B", icon: "⚠" },
  exploitation: { label: "Exploitation",      color: "#EF4444", icon: "⚡" },
  password:     { label: "Password Attacks",  color: "#EC4899", icon: "⬤" },
  post_exploit: { label: "Post-Exploitation", color: "#14B8A6", icon: "≋" },
  wireless:     { label: "Wireless",          color: "#F97316", icon: "◉" },
  forensics:    { label: "Forensics",         color: "#6366F1", icon: "⊛" },
};

const PHASE_ORDER = Object.keys(PHASE_META);

/* ─── Skeleton Card ─────────────────────────────────────────────────────── */
function SkeletonCard() {
  return (
    <div
      className="glass"
      style={{ borderRadius: "12px", padding: "18px", display: "flex", flexDirection: "column", gap: "10px" }}
    >
      <div className="shimmer" style={{ height: "14px", width: "60%", borderRadius: "4px" }} />
      <div className="shimmer" style={{ height: "10px", width: "90%", borderRadius: "4px" }} />
      <div className="shimmer" style={{ height: "10px", width: "70%", borderRadius: "4px" }} />
      <div className="shimmer" style={{ height: "20px", width: "40%", borderRadius: "6px", marginTop: "4px" }} />
    </div>
  );
}

/* ─── Tool Card ─────────────────────────────────────────────────────────── */
function ToolCard({ tool }: { tool: ToolInfo }) {
  const meta = PHASE_META[tool.phase] || { label: tool.phase, color: "#6B7280", icon: "◈" };
  const pStars = Math.max(1, Math.min(5, tool.priority));

  return (
    <div
      className="glass"
      style={{
        borderRadius: "12px",
        padding: "18px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        cursor: "default",
        transition: "all 0.2s",
        position: "relative",
        overflow: "hidden",
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.borderColor = meta.color + "30";
        el.style.transform = "translateY(-2px)";
        el.style.boxShadow = `0 8px 32px ${meta.color}10`;
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.borderColor = "rgba(255,255,255,0.06)";
        el.style.transform = "translateY(0)";
        el.style.boxShadow = "none";
      }}
    >
      {/* Corner accent */}
      <div
        style={{
          position: "absolute", top: 0, right: 0,
          width: "48px", height: "48px",
          background: `radial-gradient(circle at top right, ${meta.color}12, transparent)`,
          pointerEvents: "none",
        }}
      />

      {/* Header row */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px" }}>
        <span
          style={{
            fontFamily: "monospace",
            fontSize: "13px",
            fontWeight: 700,
            color: "#f0f4f8",
            lineHeight: 1.3,
          }}
        >
          {tool.name}
        </span>
        <span
          style={{
            fontSize: "9px",
            fontFamily: "monospace",
            color: "#3d4f60",
            whiteSpace: "nowrap",
            background: "rgba(255,255,255,0.04)",
            padding: "2px 6px",
            borderRadius: "4px",
          }}
        >
          {tool.timeout}s
        </span>
      </div>

      {/* Description */}
      <p
        style={{
          fontSize: "11.5px",
          color: "#7a8a9a",
          lineHeight: 1.6,
          margin: 0,
          flex: 1,
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {tool.description}
      </p>

      {/* Footer */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
        <span
          style={{
            fontSize: "10px",
            padding: "2px 8px",
            borderRadius: "6px",
            fontWeight: 600,
            fontFamily: "monospace",
            letterSpacing: "0.05em",
            color: meta.color,
            background: meta.color + "12",
            border: `1px solid ${meta.color}25`,
            display: "flex",
            alignItems: "center",
            gap: "4px",
          }}
        >
          {meta.icon} {meta.label}
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: "2px" }}>
          {Array.from({ length: 5 }).map((_, k) => (
            <div
              key={k}
              style={{
                width: "5px",
                height: "5px",
                borderRadius: "50%",
                background: k < pStars ? meta.color : "rgba(255,255,255,0.08)",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Page ──────────────────────────────────────────────────────────────── */
export default function ToolsPage() {
  const [tools, setTools]       = useState<ToolInfo[]>([]);
  const [filter, setFilter]     = useState("all");
  const [search, setSearch]     = useState("");
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/tools`)
      .then((r) => r.json())
      .then((d) => setTools(d.tools || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const phases = [...new Set(tools.map((t) => t.phase))].sort(
    (a, b) => PHASE_ORDER.indexOf(a) - PHASE_ORDER.indexOf(b)
  );

  const filtered = tools.filter((t) => {
    if (filter !== "all" && t.phase !== filter) return false;
    if (
      search &&
      !t.name.toLowerCase().includes(search.toLowerCase()) &&
      !t.description.toLowerCase().includes(search.toLowerCase())
    )
      return false;
    return true;
  });

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "32px 24px", display: "flex", flexDirection: "column", gap: "28px" }}>

      {/* Header */}
      <div className="slide-up" style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <div style={{ width: "3px", height: "20px", background: "linear-gradient(180deg,#8B5CF6,#3B82F6)", borderRadius: "2px" }} />
            <span style={{ fontSize: "12px", fontWeight: 600, color: "#7a8a9a", textTransform: "uppercase", letterSpacing: "0.1em" }}>
              Tool Registry
            </span>
          </div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, letterSpacing: "-0.5px", margin: 0, color: "#f0f4f8" }}>
            Security Arsenal
          </h1>
          <p style={{ fontSize: "13px", color: "#7a8a9a", margin: "4px 0 0" }}>
            {loading ? "Loading..." : `${tools.length} tools across ${phases.length} attack phases`}
          </p>
        </div>

        {/* Search */}
        <div style={{ position: "relative" }}>
          <span style={{
            position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)",
            fontSize: "13px", color: "#3d4f60", pointerEvents: "none",
          }}>⌕</span>
          <input
            className="rt-input"
            style={{ width: "240px", paddingLeft: "32px" }}
            placeholder="Search tools..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            id="tools-search"
          />
        </div>
      </div>

      {/* Stats row */}
      {!loading && tools.length > 0 && (
        <div
          className="slide-up"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
            gap: "10px",
            animationDelay: "0.05s",
          }}
        >
          {[
            { label: "Total Tools", value: tools.length, color: "#00ff87" },
            { label: "Phases",      value: phases.length, color: "#3B82F6" },
            { label: "Active",      value: filtered.length, color: "#8B5CF6" },
            { label: "Avg Timeout", value: `${Math.round(tools.reduce((a, t) => a + t.timeout, 0) / tools.length)}s`, color: "#F59E0B" },
          ].map((s) => (
            <div key={s.label} className="stat-card" style={{ borderColor: s.color + "15" }}>
              <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Phase Filter Pills */}
      <div
        className="slide-up"
        style={{ display: "flex", gap: "8px", flexWrap: "wrap", animationDelay: "0.1s" }}
      >
        <button
          id="filter-all"
          onClick={() => setFilter("all")}
          style={{
            padding: "6px 14px",
            borderRadius: "8px",
            fontSize: "12px",
            fontWeight: 600,
            fontFamily: "monospace",
            border: "1px solid",
            cursor: "pointer",
            transition: "all 0.15s",
            background: filter === "all" ? "rgba(255,255,255,0.08)" : "transparent",
            borderColor: filter === "all" ? "rgba(255,255,255,0.15)" : "rgba(255,255,255,0.06)",
            color: filter === "all" ? "#f0f4f8" : "#7a8a9a",
          }}
        >
          All ({tools.length})
        </button>
        {phases.map((p) => {
          const meta = PHASE_META[p] || { label: p, color: "#6B7280", icon: "◈" };
          const count = tools.filter((t) => t.phase === p).length;
          const active = filter === p;
          return (
            <button
              key={p}
              id={`filter-${p}`}
              onClick={() => setFilter(p)}
              style={{
                padding: "6px 14px",
                borderRadius: "8px",
                fontSize: "12px",
                fontWeight: 600,
                fontFamily: "monospace",
                border: `1px solid ${active ? meta.color + "40" : meta.color + "15"}`,
                cursor: "pointer",
                transition: "all 0.15s",
                background: active ? meta.color + "15" : "transparent",
                color: active ? meta.color : "#7a8a9a",
                display: "flex",
                alignItems: "center",
                gap: "5px",
              }}
            >
              <span>{meta.icon}</span>
              {meta.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Tools grid */}
      <div
        className="slide-up"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: "12px",
          animationDelay: "0.15s",
        }}
      >
        {loading
          ? Array.from({ length: 12 }).map((_, i) => <SkeletonCard key={i} />)
          : filtered.map((tool) => <ToolCard key={tool.name} tool={tool} />)
        }
      </div>

      {!loading && filtered.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: "80px 0",
            color: "#3d4f60",
          }}
        >
          <div style={{ fontSize: "32px", marginBottom: "12px" }}>◈</div>
          <p style={{ fontSize: "15px", marginBottom: "4px", color: "#7a8a9a" }}>No tools match your filter</p>
          <p style={{ fontSize: "12px" }}>Try adjusting the phase filter or search query</p>
        </div>
      )}
    </div>
  );
}
