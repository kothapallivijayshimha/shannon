"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const NAV_ITEMS = [
  { href: "/",       label: "Assess",  icon: "⬡" },
  { href: "/tools",  label: "Tools",   icon: "◈" },
  { href: "/phases", label: "History", icon: "≋" },
];

export default function Navbar() {
  const pathname = usePathname();
  const [time, setTime] = useState("");
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString("en-US", {
          hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
        })
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const check = () =>
      fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/`)
        .then(() => setApiOnline(true))
        .catch(() => setApiOnline(false));
    check();
    const id = setInterval(check, 10_000);
    return () => clearInterval(id);
  }, []);

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        background: "rgba(2,5,8,0.85)",
        backdropFilter: "blur(20px) saturate(180%)",
        WebkitBackdropFilter: "blur(20px) saturate(180%)",
      }}
    >
      <div
        style={{
          maxWidth: "1280px",
          margin: "0 auto",
          padding: "0 24px",
          height: "56px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "24px",
        }}
      >
        {/* Logo */}
        <Link href="/" style={{ textDecoration: "none", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {/* Animated hex logo */}
            <div
              style={{
                width: "32px",
                height: "32px",
                background: "linear-gradient(135deg, #00ff87, #00c96a)",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "14px",
                fontWeight: 900,
                color: "#000",
                boxShadow: "0 0 20px rgba(0,255,135,0.3)",
                fontFamily: "monospace",
              }}
            >
              RT
            </div>
            <div>
              <div
                style={{
                  fontSize: "15px",
                  fontWeight: 700,
                  color: "#f0f4f8",
                  lineHeight: 1,
                  letterSpacing: "-0.3px",
                }}
              >
                KVS <span style={{ color: "#00ff87" }}>RedTeam</span>
              </div>
              <div
                style={{
                  fontSize: "9px",
                  color: "#3d4f60",
                  fontFamily: "monospace",
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                }}
              >
                AI v4.0
              </div>
            </div>
          </div>
        </Link>

        {/* Nav Links */}
        <nav style={{ display: "flex", gap: "4px" }}>
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "6px 14px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: 500,
                  textDecoration: "none",
                  transition: "all 0.15s",
                  color: active ? "#f0f4f8" : "#3d4f60",
                  background: active ? "rgba(255,255,255,0.06)" : "transparent",
                  border: `1px solid ${active ? "rgba(255,255,255,0.08)" : "transparent"}`,
                }}
              >
                <span style={{ fontSize: "11px", opacity: 0.7 }}>{item.icon}</span>
                {item.label}
                {active && (
                  <span
                    style={{
                      display: "inline-block",
                      width: "4px",
                      height: "4px",
                      borderRadius: "50%",
                      background: "#00ff87",
                      boxShadow: "0 0 6px #00ff87",
                    }}
                  />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right side: status + clock */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px", flexShrink: 0 }}>
          {/* API Status */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "11px",
              fontFamily: "monospace",
              color: apiOnline === null ? "#3d4f60" : apiOnline ? "#00ff87" : "#ff3b3b",
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: apiOnline === null ? "#3d4f60" : apiOnline ? "#00ff87" : "#ff3b3b",
                boxShadow: apiOnline ? "0 0 8px #00ff87" : "none",
                animation: apiOnline ? "pulse-dot 2s infinite" : "none",
              }}
            />
            {apiOnline === null ? "checking" : apiOnline ? "API ONLINE" : "API OFFLINE"}
          </div>

          {/* Clock */}
          {time && (
            <div
              style={{
                fontSize: "11px",
                fontFamily: "monospace",
                color: "#3d4f60",
                letterSpacing: "0.05em",
                borderLeft: "1px solid rgba(255,255,255,0.06)",
                paddingLeft: "16px",
              }}
            >
              {time}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
