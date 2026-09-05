from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from database import detection_db

logger = logging.getLogger("detection")

# ---------------------------------------------------------------------------
# Pattern definitions for wireless attack detection
# ---------------------------------------------------------------------------

DEAUTH_FLOOD_THRESHOLD = 20  # deauth packets per minute to trigger alert
BEACON_ANOMALY_INTERVAL_S = 30  # check for beacon anomalies every N seconds


@dataclass
class DetectionEvent:
    event_type: str  # "rogue_ap" | "deauth_flood" | "beacon_anomaly" | "info"
    severity: str = "info"  # "info" | "low" | "medium" | "high" | "critical"
    source: str = ""
    details: str = ""
    raw_data: str = ""
    interface: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "severity": self.severity,
            "source": self.source,
            "details": self.details,
            "raw_data": self.raw_data[:1000],
            "interface": self.interface,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Detection Engine
# ---------------------------------------------------------------------------


class DetectionEngine:
    """Passive wireless monitoring and attack detection.

    Runs as a background asyncio task that:
    - Periodically scans for rogue access points
    - Monitors for deauthentication floods
    - Detects beacon anomalies
    - Stores all events in the detection database

    Can be started/stopped via API.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False
        self._interface: str = ""
        self._deauth_counter: dict[str, int] = {}
        self._known_bssids: set[str] = set()
        self._known_ssids: set[str] = set()

    # ---- Public API -----------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self, interface: str = "wlan0") -> str:
        """Start the background monitoring loop on *interface*."""
        if self._running:
            return "already_running"

        self._interface = interface
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Detection engine started on {interface}")
        return "started"

    async def stop(self) -> str:
        """Stop the background monitoring loop."""
        if not self._running:
            return "not_running"

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Detection engine stopped")
        return "stopped"

    async def scan_once(self, interface: str = "wlan0") -> list[dict]:
        """Run a one-shot scan and return events.

        Useful for API-driven scans without starting the background loop.
        """
        events: list[DetectionEvent] = []
        try:
            ap_scan = await self._scan_aps(interface)
            events.extend(ap_scan)
        except Exception:
            logger.exception("One-shot scan failed")
            events.append(DetectionEvent(
                event_type="scan_error",
                severity="info",
                source="detection_engine",
                details=f"Scan failed on {interface} (interface may not exist)",
            ))

        for ev in events:
            detection_db.store_event(
                event_type=ev.event_type,
                severity=ev.severity,
                source=ev.source,
                details=ev.details,
                raw_data=ev.raw_data,
                interface=ev.interface,
            )

        return [ev.to_dict() for ev in events]

    def get_events(self, event_type: str | None = None,
                   severity: str | None = None,
                   limit: int = 100, offset: int = 0) -> list[dict]:
        return detection_db.query(event_type, severity, limit, offset)

    # ---- Background loop ------------------------------------------------

    async def _monitor_loop(self) -> None:
        """Continuous monitoring loop."""
        scan_interval = 30  # seconds between full scans

        while self._running:
            try:
                events: list[DetectionEvent] = []

                # Full AP scan
                ap_events = await self._scan_aps(self._interface)
                events.extend(ap_events)

                # Deauth flood detection (passive via airodump-ng CSV)
                deauth_events = await self._check_deauth_flood(self._interface)
                events.extend(deauth_events)

                # Beacon anomaly detection
                beacon_events = await self._check_beacon_anomalies(self._interface)
                events.extend(beacon_events)

                # Persist all events
                for ev in events:
                    detection_db.store_event(
                        event_type=ev.event_type,
                        severity=ev.severity,
                        source=ev.source,
                        details=ev.details,
                        raw_data=ev.raw_data,
                        interface=ev.interface,
                    )
                    logger.info(f"Detection event: [{ev.severity}] {ev.event_type} — {ev.details[:100]}")

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Detection loop error")

            await asyncio.sleep(scan_interval)

    # ---- Detection methods ----------------------------------------------

    async def _scan_aps(self, interface: str) -> list[DetectionEvent]:
        """Scan for access points and detect rogue APs."""
        events: list[DetectionEvent] = []

        try:
            proc = await asyncio.create_subprocess_exec(
                "airodump-ng", interface, "--output-format", "csv",
                "-w", "/tmp/detection_scan", "--write-interval", "1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                await asyncio.wait_for(proc.wait(), timeout=15)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()

            # Read the CSV output
            csv_path = "/tmp/detection_scan-01.csv"
            try:
                with open(csv_path) as f:
                    content = f.read()
            except FileNotFoundError:
                return events

            # Parse airodump-ng CSV for APs and clients
            lines = content.splitlines()
            in_aps = True
            for line in lines:
                if line.startswith("BSSID,"):
                    in_aps = True
                    continue
                if line.startswith("Station MAC,"):
                    in_aps = False
                    continue
                if not line.strip() or "," not in line:
                    continue

                parts = [p.strip() for p in line.split(",")]

                if in_aps and len(parts) >= 6:
                    bssid = parts[0]
                    power = parts[3] if len(parts) > 3 else "0"
                    essid = parts[13] if len(parts) > 13 else ""
                    channel = parts[5] if len(parts) > 5 else ""
                    encryption = parts[7] if len(parts) > 7 else ""

                    # Track known networks
                    if bssid:
                        self._known_bssids.add(bssid)
                    if essid:
                        self._known_ssids.add(essid)

                    # Rogue AP detection: check for evil twin / same SSID different BSSID
                    if essid and essid in self._known_ssids:
                        # This is a known SSID — flag if not already known
                        if bssid and bssid not in self._known_bssids:
                            events.append(DetectionEvent(
                                event_type="rogue_ap",
                                severity="high",
                                source=bssid,
                                details=f"Possible rogue AP: {essid} ({bssid}) ch{channel} "
                                        f"enc={encryption}",
                                raw_data=line,
                                interface=interface,
                            ))

                    # Open/unencrypted AP detection
                    if encryption and encryption.lower() in ("opn", "none", ""):
                        events.append(DetectionEvent(
                            event_type="open_ap",
                            severity="medium",
                            source=bssid,
                            details=f"Open (unencrypted) AP: {essid} ({bssid}) ch{channel}",
                            raw_data=line,
                            interface=interface,
                        ))

                elif not in_aps and len(parts) >= 4:
                    # Client station — check for deauth patterns
                    pass

            # Clean up temp files
            for suffix in ["-01.csv", "-01.kismet.csv", "-01.log.csv"]:
                import os as _os
                try:
                    _os.remove(f"/tmp/detection_scan{suffix}")
                except OSError:
                    pass
            try:
                import os as _os
                _os.remove("/tmp/detection_scan-01.cap")
            except OSError:
                pass

        except FileNotFoundError:
            # airodump-ng not installed — try iwlist fallback
            events.extend(await self._scan_aps_fallback(interface))
        except Exception:
            logger.exception("AP scan failed")

        return events

    async def _scan_aps_fallback(self, interface: str) -> list[DetectionEvent]:
        """Fallback AP scan using iwlist (no airodump-ng needed)."""
        events: list[DetectionEvent] = []

        try:
            proc = await asyncio.create_subprocess_exec(
                "iwlist", interface, "scan",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return events

            output = stdout_bytes.decode("utf-8", errors="replace")

            # Parse iwlist output
            current_bssid = ""
            current_essid = ""
            current_channel = ""
            current_encryption = ""

            for line in output.splitlines():
                line = line.strip()
                m = re.match(r"Cell \d+ - Address: (\S+)", line)
                if m:
                    if current_bssid and current_bssid not in self._known_bssids:
                        # Previous cell processed — add it
                        if current_essid:
                            self._known_ssids.add(current_essid)
                        self._known_bssids.add(current_bssid)
                    current_bssid = m.group(1)
                    current_essid = ""
                    current_channel = ""
                    current_encryption = ""
                    continue

                m = re.search(r'ESSID:"([^"]*)"', line)
                if m:
                    current_essid = m.group(1)
                    if current_bssid:
                        self._known_ssids.add(current_essid)
                        self._known_bssids.add(current_bssid)
                    continue

                m = re.search(r"Channel[:\s]*(\d+)", line, re.IGNORECASE)
                if m:
                    current_channel = m.group(1)
                    continue

                if "Encryption key:off" in line or "Encryption:off" in line:
                    current_encryption = "OPN"
                    if current_bssid and current_essid:
                        events.append(DetectionEvent(
                            event_type="open_ap",
                            severity="medium",
                            source=current_bssid,
                            details=f"Open AP: {current_essid} ({current_bssid}) ch{current_channel}",
                            raw_data=line,
                            interface=interface,
                        ))

                if "WPA2" in line:
                    current_encryption = "WPA2"
                elif "WPA3" in line:
                    current_encryption = "WPA3"

        except FileNotFoundError:
            events.append(DetectionEvent(
                event_type="scan_error",
                severity="info",
                source="detection_engine",
                details=f"Neither airodump-ng nor iwlist available on {interface}",
            ))
        except Exception:
            logger.exception("Fallback AP scan failed")
            events.append(DetectionEvent(
                event_type="scan_error",
                severity="info",
                source="detection_engine",
                details=f"Fallback scan failed on {interface}",
            ))

        return events

    async def _check_deauth_flood(self, interface: str) -> list[DetectionEvent]:
        """Monitor for deauthentication flood attacks.

        Parses airodump-ng output for high rates of deauth packets.
        """
        events: list[DetectionEvent] = []

        try:
            proc = await asyncio.create_subprocess_exec(
                "airodump-ng", interface, "--output-format", "csv",
                "-w", "/tmp/deauth_check", "--write-interval", "1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                await asyncio.wait_for(proc.wait(), timeout=10)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()

            csv_path = "/tmp/deauth_check-01.csv"
            try:
                with open(csv_path) as f:
                    content = f.read()
            except FileNotFoundError:
                return events

            # Look for deauth indicators in the capture
            deauth_count = content.lower().count("deauth")
            if deauth_count > DEAUTH_FLOOD_THRESHOLD:
                events.append(DetectionEvent(
                    event_type="deauth_flood",
                    severity="critical" if deauth_count > 100 else "high",
                    source=interface,
                    details=f"Deauthentication flood detected: {deauth_count} deauth frames",
                    raw_data=f"deauth_count={deauth_count}",
                    interface=interface,
                ))

            # Cleanup
            import os as _os
            for suffix in ["-01.csv", "-01.kismet.csv", "-01.log.csv", "-01.cap"]:
                try:
                    _os.remove(f"/tmp/deauth_check{suffix}")
                except OSError:
                    pass

        except FileNotFoundError:
            pass  # airodump-ng not available
        except Exception:
            logger.exception("Deauth check failed")

        return events

    async def _check_beacon_anomalies(self, interface: str) -> list[DetectionEvent]:
        """Detect beacon frame anomalies — rogue APs spoofing legitimate SSIDs."""
        events: list[DetectionEvent] = []
        # This complements _scan_aps by flagging inconsistencies in
        # beacon intervals, channel hops, and signal patterns.
        #
        # Currently a placeholder — full beacon analysis requires
        # packet-level capture (scapy or tshark).
        return events

    def _detect_attack_pattern(self, events: list[DetectionEvent]) -> list[DetectionEvent]:
        """Correlate multiple events to detect coordinated attacks."""
        correlated: list[DetectionEvent] = []

        # Pattern: multiple open APs on different channels from same source
        open_aps = [e for e in events if e.event_type == "open_ap"]
        if len(open_aps) >= 3:
            sources = set(e.source for e in open_aps)
            if len(sources) >= 3:
                correlated.append(DetectionEvent(
                    event_type="multi_open_ap_anomaly",
                    severity="high",
                    source=",".join(list(sources)[:5]),
                    details=f"{len(open_aps)} open APs detected — possible rogue AP campaign",
                    interface=self._interface,
                ))

        return correlated


# Global singleton
detector = DetectionEngine()
