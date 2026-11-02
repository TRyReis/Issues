#!/usr/bin/env python3
"""
PC-Wake Server
==============

Kleiner Relay-Server, der dauerhaft im Heimnetz läuft (z.B. Raspberry Pi, NAS,
alter Laptop). Er

  * sendet Wake-on-LAN "Magic Packets" an deinen PC,
  * prüft, ob der PC online ist,
  * führt geplante Autostarts zu festen Uhrzeiten aus,
  * liefert die Handy-App (PWA) aus.

Nur Python-Standardbibliothek, keine Abhängigkeiten. Python >= 3.9.

Start:  python3 pcwake_server.py            (nutzt config.json im selben Ordner)
        python3 pcwake_server.py --config /pfad/zur/config.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hmac
import json
import logging
import mimetypes
import os
import platform
import re
import secrets
import socket
import subprocess
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "config.json"
DEFAULT_APP_DIR = BASE_DIR.parent / "app"

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

log = logging.getLogger("pcwake")


# --------------------------------------------------------------------------- #
# Wake-on-LAN
# --------------------------------------------------------------------------- #
def build_magic_packet(mac: str) -> bytes:
    if not MAC_RE.match(mac):
        raise ValueError(f"Ungültige MAC-Adresse: {mac}")
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    return b"\xff" * 6 + mac_bytes * 16


def send_magic_packet(mac: str, broadcast: str = "255.255.255.255", port: int = 9) -> None:
    packet = build_magic_packet(mac)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Mehrfach senden – UDP kann verloren gehen; Port 9 und 7 sind üblich.
        for _ in range(3):
            sock.sendto(packet, (broadcast, port))
            if port != 7:
                sock.sendto(packet, (broadcast, 7))
            time.sleep(0.05)


# --------------------------------------------------------------------------- #
# Online-Check
# --------------------------------------------------------------------------- #
def is_online(ip: str | None, tcp_ports: list[int] | None = None) -> bool | None:
    """True/False, oder None wenn keine IP konfiguriert ist."""
    if not ip:
        return None
    # 1) ICMP-Ping (Windows blockiert Ping oft in der Firewall -> danach TCP)
    flag = "-n" if platform.system().lower() == "windows" else "-c"
    wait = ["-w", "1000"] if platform.system().lower() == "windows" else ["-W", "1"]
    try:
        res = subprocess.run(
            ["ping", flag, "1", *wait, ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        if res.returncode == 0:
            return True
    except (OSError, subprocess.TimeoutExpired):
        pass
    # 2) TCP-Connect auf typische Windows-Ports (RDP, SMB)
    for port in tcp_ports or [3389, 445, 22]:
        try:
            with socket.create_connection((ip, port), timeout=0.8):
                return True
        except ConnectionRefusedError:
            return True  # Host antwortet -> ist an
        except OSError:
            continue
    return False


# --------------------------------------------------------------------------- #
# Konfiguration & Zeitpläne
# --------------------------------------------------------------------------- #
class Store:
    """Thread-sichere Verwaltung von config.json und schedules.json."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.lock = threading.RLock()
        self.config = self._load_config()
        sched_file = self.config.get("schedules_file", "schedules.json")
        self.schedules_path = (config_path.parent / sched_file).resolve()
        self.schedules: list[dict] = self._load_json(self.schedules_path, [])

    @staticmethod
    def _load_json(path: Path, default):
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            example = self.config_path.parent / "config.example.json"
            raise SystemExit(
                f"Konfiguration nicht gefunden: {self.config_path}\n"
                f"Kopiere {example.name} nach {self.config_path.name} und passe sie an."
            )
        cfg = self._load_json(self.config_path, {})
        token = cfg.get("token", "")
        if not token or token == "HIER-EIN-LANGES-GEHEIMES-TOKEN-EINTRAGEN":
            new_token = secrets.token_urlsafe(24)
            cfg["token"] = new_token
            self.config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
            print("\n" + "=" * 64)
            print(" Neues Zugangs-Token erzeugt und in config.json gespeichert:")
            print(f"   {new_token}")
            print(" Dieses Token gibst du einmalig in der Handy-App ein.")
            print("=" * 64 + "\n")
        for dev in cfg.get("devices", []):
            build_magic_packet(dev["mac"])  # validiert MAC
            dev.setdefault("id", re.sub(r"[^a-z0-9]+", "-", dev["name"].lower()).strip("-"))
            dev.setdefault("broadcast", "255.255.255.255")
            dev.setdefault("port", 9)
        if not cfg.get("devices"):
            raise SystemExit("In config.json ist kein Gerät unter 'devices' eingetragen.")
        return cfg

    def save_schedules(self) -> None:
        with self.lock:
            tmp = self.schedules_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.schedules, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.schedules_path)

    def device(self, device_id: str) -> dict | None:
        return next((d for d in self.config["devices"] if d["id"] == device_id), None)

    def tz(self):
        name = self.config.get("timezone")
        if name and ZoneInfo:
            return ZoneInfo(name)
        return None  # lokale Systemzeit

    def now(self) -> dt.datetime:
        tz = self.tz()
        return dt.datetime.now(tz) if tz else dt.datetime.now()


def validate_schedule(data: dict, store: Store) -> dict:
    device_id = str(data.get("device", ""))
    if not store.device(device_id):
        raise ValueError("Unbekanntes Gerät")
    t = str(data.get("time", ""))
    if not TIME_RE.match(t):
        raise ValueError("Uhrzeit muss im Format HH:MM sein")
    days = data.get("days", [])
    if not isinstance(days, list) or not days or not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
        raise ValueError("Mindestens ein Wochentag (0=Mo … 6=So) erforderlich")
    label = str(data.get("label", ""))[:60]
    return {
        "device": device_id,
        "time": t,
        "days": sorted(set(days)),
        "enabled": bool(data.get("enabled", True)),
        "label": label,
    }


# --------------------------------------------------------------------------- #
# Scheduler
# --------------------------------------------------------------------------- #
class Scheduler(threading.Thread):
    def __init__(self, store: Store):
        super().__init__(daemon=True, name="scheduler")
        self.store = store
        self._fired: set[str] = set()

    def run(self) -> None:
        log.info("Scheduler gestartet")
        while True:
            try:
                self.tick()
            except Exception:  # noqa: BLE001
                log.exception("Fehler im Scheduler")
            time.sleep(15)

    def tick(self) -> None:
        now = self.store.now()
        hhmm = now.strftime("%H:%M")
        minute_key = now.strftime("%Y-%m-%d %H:%M")
        # alte Einträge aufräumen
        self._fired = {k for k in self._fired if k.endswith(minute_key)}
        with self.store.lock:
            schedules = list(self.store.schedules)
        for s in schedules:
            if not s.get("enabled") or s["time"] != hhmm or now.weekday() not in s["days"]:
                continue
            key = f"{s['id']}|{minute_key}"
            if key in self._fired:
                continue
            self._fired.add(key)
            dev = self.store.device(s["device"])
            if not dev:
                continue
            log.info("Autostart '%s' -> %s (%s)", s.get("label") or s["id"], dev["name"], hhmm)
            try:
                send_magic_packet(dev["mac"], dev["broadcast"], dev["port"])
                with self.store.lock:
                    for item in self.store.schedules:
                        if item["id"] == s["id"]:
                            item["last_run"] = now.isoformat(timespec="seconds")
                    self.store.save_schedules()
            except OSError:
                log.exception("Magic Packet konnte nicht gesendet werden")


def next_run(schedule: dict, now: dt.datetime) -> str | None:
    if not schedule.get("enabled"):
        return None
    h, m = map(int, schedule["time"].split(":"))
    for offset in range(0, 8):
        day = now + dt.timedelta(days=offset)
        cand = day.replace(hour=h, minute=m, second=0, microsecond=0)
        if cand.weekday() in schedule["days"] and cand > now:
            return cand.isoformat(timespec="minutes")
    return None


# --------------------------------------------------------------------------- #
# HTTP-API
# --------------------------------------------------------------------------- #
class FailedLogins:
    """Einfacher Schutz gegen Token-Raten: max. 10 Fehlversuche / 10 min je IP."""

    def __init__(self):
        self.lock = threading.Lock()
        self.data: dict[str, list[float]] = {}

    def blocked(self, ip: str) -> bool:
        with self.lock:
            now = time.time()
            hits = [t for t in self.data.get(ip, []) if now - t < 600]
            self.data[ip] = hits
            return len(hits) >= 10

    def add(self, ip: str) -> None:
        with self.lock:
            self.data.setdefault(ip, []).append(time.time())


def make_handler(store: Store, app_dir: Path, failed: FailedLogins):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PCWake/1.0"

        # ---------- Hilfsfunktionen ----------
        def log_message(self, fmt, *args):  # noqa: N802
            log.debug("%s - %s", self.client_address[0], fmt % args)

        def client_ip(self) -> str:
            if store.config.get("trust_proxy"):
                fwd = self.headers.get("X-Forwarded-For")
                if fwd:
                    return fwd.split(",")[0].strip()
            return self.client_address[0]

        def send_json(self, status: int, payload) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 10_000:
                raise ValueError("Anfrage zu groß")
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw or b"{}")
            if not isinstance(data, dict):
                raise ValueError("JSON-Objekt erwartet")
            return data

        def authorized(self) -> bool:
            ip = self.client_ip()
            if failed.blocked(ip):
                self.send_json(429, {"error": "Zu viele Fehlversuche – bitte später erneut versuchen"})
                return False
            header = self.headers.get("Authorization", "")
            token = header[7:] if header.startswith("Bearer ") else ""
            if token and hmac.compare_digest(token.encode(), store.config["token"].encode()):
                return True
            failed.add(ip)
            log.warning("Ungültiges Token von %s", ip)
            self.send_json(401, {"error": "Ungültiges Token"})
            return False

        # ---------- Routing ----------
        def do_GET(self):  # noqa: N802
            path = urlparse(self.path).path
            if path.startswith("/api/"):
                if not self.authorized():
                    return
                if path == "/api/devices":
                    return self.api_devices()
                if path == "/api/schedules":
                    return self.api_list_schedules()
                return self.send_json(404, {"error": "Nicht gefunden"})
            return self.serve_static(path)

        def do_POST(self):  # noqa: N802
            path = urlparse(self.path).path
            if not path.startswith("/api/") or not self.authorized():
                if not path.startswith("/api/"):
                    self.send_json(404, {"error": "Nicht gefunden"})
                return
            try:
                data = self.read_json()
                m = re.fullmatch(r"/api/devices/([\w-]+)/wake", path)
                if m:
                    return self.api_wake(m.group(1))
                if path == "/api/schedules":
                    return self.api_create_schedule(data)
                m = re.fullmatch(r"/api/schedules/([\w-]+)", path)
                if m:
                    return self.api_update_schedule(m.group(1), data)
                return self.send_json(404, {"error": "Nicht gefunden"})
            except (ValueError, json.JSONDecodeError) as e:
                return self.send_json(400, {"error": str(e)})

        def do_DELETE(self):  # noqa: N802
            path = urlparse(self.path).path
            if not self.authorized():
                return
            m = re.fullmatch(r"/api/schedules/([\w-]+)", path)
            if not m:
                return self.send_json(404, {"error": "Nicht gefunden"})
            with store.lock:
                before = len(store.schedules)
                store.schedules = [s for s in store.schedules if s["id"] != m.group(1)]
                if len(store.schedules) == before:
                    return self.send_json(404, {"error": "Zeitplan nicht gefunden"})
                store.save_schedules()
            self.send_json(200, {"ok": True})

        # ---------- API ----------
        def api_devices(self):
            devices = store.config["devices"]
            results: dict[str, bool | None] = {}

            def check(d):
                results[d["id"]] = is_online(d.get("ip"), d.get("check_ports"))

            threads = [threading.Thread(target=check, args=(d,)) for d in devices]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.send_json(200, {
                "server_time": store.now().isoformat(timespec="seconds"),
                "devices": [
                    {"id": d["id"], "name": d["name"], "mac": d["mac"], "online": results.get(d["id"])}
                    for d in devices
                ],
            })

        def api_wake(self, device_id: str):
            dev = store.device(device_id)
            if not dev:
                return self.send_json(404, {"error": "Gerät nicht gefunden"})
            try:
                send_magic_packet(dev["mac"], dev["broadcast"], dev["port"])
            except OSError as e:
                log.exception("Senden fehlgeschlagen")
                return self.send_json(500, {"error": f"Senden fehlgeschlagen: {e}"})
            log.info("Manueller Start: %s (von %s)", dev["name"], self.client_ip())
            self.send_json(200, {"ok": True, "message": f"Magic Packet an {dev['name']} gesendet"})

        def api_list_schedules(self):
            now = store.now()
            with store.lock:
                items = [dict(s, next_run=next_run(s, now)) for s in store.schedules]
            self.send_json(200, {"schedules": items})

        def api_create_schedule(self, data: dict):
            sched = validate_schedule(data, store)
            sched["id"] = uuid.uuid4().hex[:10]
            with store.lock:
                store.schedules.append(sched)
                store.save_schedules()
            self.send_json(201, {"schedule": sched})

        def api_update_schedule(self, sched_id: str, data: dict):
            with store.lock:
                existing = next((s for s in store.schedules if s["id"] == sched_id), None)
                if not existing:
                    return self.send_json(404, {"error": "Zeitplan nicht gefunden"})
                merged = validate_schedule({**existing, **data}, store)
                existing.update(merged)
                store.save_schedules()
                result = dict(existing)
            self.send_json(200, {"schedule": result})

        # ---------- Statische Dateien (Handy-App) ----------
        def serve_static(self, path: str):
            if path in ("", "/"):
                path = "/index.html"
            target = (app_dir / path.lstrip("/")).resolve()
            if app_dir not in target.parents or not target.is_file():
                return self.send_json(404, {"error": "Nicht gefunden"})
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if target.suffix == ".webmanifest":
                ctype = "application/manifest+json"
            body = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="PC-Wake Server")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--app-dir", type=Path, default=DEFAULT_APP_DIR)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    store = Store(args.config.resolve())
    app_dir = args.app_dir.resolve()
    Scheduler(store).start()

    host = store.config.get("listen", "0.0.0.0")
    port = int(store.config.get("port", 8080))
    httpd = ThreadingHTTPServer((host, port), make_handler(store, app_dir, FailedLogins()))
    log.info("PC-Wake läuft auf http://%s:%d  (App-Ordner: %s)", host, port, app_dir)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("Beendet")


if __name__ == "__main__":
    main()
