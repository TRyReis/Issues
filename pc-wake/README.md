# PC-Wake – PC per Handy von überall starten

Handy-App, mit der du deinen PC **von überall** einschaltest, auch über mobile Daten.
Dazu kommen **Autostart-Zeitpläne** (z.B. „Mo–Fr um 07:30“).

```
 Handy (App)  ──Internet / mobile Daten──▶  Mini-Server im Heimnetz  ──Magic Packet──▶  PC
                 (sicher über Tailscale)     (Raspberry Pi, NAS …)       (Wake-on-LAN)
```

## Warum ein kleiner Server im Heimnetz?

Ein ausgeschalteter PC kann nur über ein **Wake-on-LAN-„Magic Packet“** geweckt werden.
Dieses Paket muss **aus dem eigenen Heimnetz** kommen, denn Router leiten solche Broadcasts
aus dem Internet normalerweise nicht weiter. Deshalb läuft ein winziger Server (`server/`)
auf einem Gerät, das immer an ist, z.B. einem **Raspberry Pi** (ein Zero 2 W reicht),
einem NAS oder einem alten Laptop. Er

- empfängt den „Einschalten“-Befehl vom Handy und sendet das Magic Packet,
- zeigt an, ob der PC online ist,
- **führt die Autostarts aus**. Dafür muss das Handy nicht an sein und auch keinen Empfang haben,
- liefert die Handy-App aus.

Die App ist eine **Web-App (PWA)**: Sie wird über „Zum Startbildschirm hinzufügen“ installiert
und läuft dann wie eine normale App im Vollbild, auf **Android und iPhone**. Einen App-Store
brauchst du nicht.

---

## 1. PC vorbereiten (Wake-on-LAN aktivieren)

Der PC muss **per LAN-Kabel** am Router hängen. WLAN-Wake funktioniert nur selten zuverlässig.

1. **BIOS/UEFI** (beim Start `Entf`/`F2`): je nach Hersteller *Wake on LAN*, *Power On By PCI-E*
   oder *Resume by LAN* **aktivieren**. *ErP / EuP Ready* **deaktivieren**.
2. **Windows → Geräte-Manager → Netzwerkadapter → (dein LAN-Adapter) → Eigenschaften**
   - Reiter *Energieverwaltung*: ✅ „Gerät kann den Computer aus dem Ruhezustand aktivieren“
     und ✅ „Nur Magic Packets …“
   - Reiter *Erweitert*: „Wake on Magic Packet“ = **Aktiviert**
3. **Schnellstart deaktivieren**: Systemsteuerung → Energieoptionen → „Auswählen, was beim
   Drücken des Netzschalters geschehen soll“ → „Schnellstart aktivieren“ **abhaken**.
4. **MAC-Adresse und IP notieren**: in der Eingabeaufforderung `ipconfig /all` ausführen,
   dann die Werte „Physische Adresse“ (z.B. `AA-BB-CC-DD-EE-FF`) und „IPv4-Adresse“ abschreiben.
5. Am besten im Router (z.B. FRITZ!Box) einstellen: **„Diesem Gerät immer die gleiche IPv4-Adresse
   zuweisen“**.

## 2. Server auf dem Raspberry Pi einrichten

```bash
# Dateien auf den Pi kopieren (z.B. nach /home/pi/pc-wake), dann:
cd ~/pc-wake/server
cp config.example.json config.json
nano config.json
```

`config.json` anpassen:

| Feld        | Bedeutung                                                               |
|-------------|-------------------------------------------------------------------------|
| `mac`       | MAC-Adresse des PCs                                                     |
| `ip`        | IP des PCs (für die Online-Anzeige)                                     |
| `broadcast` | Broadcast-Adresse deines Netzes, meist IP mit `.255` am Ende, z.B. `192.168.178.255` |
| `timezone`  | Zeitzone für die Autostarts, z.B. `Europe/Berlin`                       |
| `token`     | einfach so lassen: beim ersten Start wird automatisch ein sicheres Token erzeugt |

Mehrere PCs? Dann einfach weitere Einträge in `devices` ergänzen.

Testlauf:

```bash
python3 pcwake_server.py
```

Das angezeigte **Token** notieren. Danach im Heimnetz `http://<IP-des-Pi>:8080` im Handy-Browser
öffnen, Token eingeben und testen.

Als Dienst einrichten, damit der Server beim Booten automatisch startet:

```bash
sudo cp pcwake.service /etc/systemd/system/   # Pfade/Benutzer darin ggf. anpassen
sudo systemctl daemon-reload
sudo systemctl enable --now pcwake
```

## 3. Von überall erreichbar machen (mobile Daten)

### Empfohlen: Tailscale (kostenlos, sicher, ohne Portfreigabe)

Tailscale baut ein privates VPN zwischen Handy und Pi auf. Es funktioniert auch bei
DS-Lite/CGNAT-Anschlüssen (viele Kabel- und Glasfaseranschlüsse), bei denen eine Portfreigabe
gar nicht möglich ist.

1. Auf dem Pi:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   # HTTPS-Adresse mit gültigem Zertifikat bereitstellen (nur im eigenen Tailnet sichtbar):
   sudo tailscale serve --bg 8080
   ```
   Den angezeigten Link notieren, z.B. `https://raspberrypi.tail1234.ts.net`.
2. Auf dem Handy die **Tailscale-App** installieren und mit demselben Konto anmelden.
3. Den Link im Handy-Browser öffnen. Ab jetzt geht das auch über mobile Daten.

### Alternative: Portfreigabe im Router

Nur zu empfehlen, wenn du dich damit auskennst. Den Server dann **unbedingt hinter HTTPS** betreiben
(z.B. mit Caddy als Reverse-Proxy und einer DynDNS-Adresse). Ohne HTTPS würde das Token
unverschlüsselt übertragen. Hinter einem Reverse-Proxy in der `config.json` zusätzlich
`"trust_proxy": true` und `"listen": "127.0.0.1"` setzen.

## 4. App aufs Handy installieren

Die Server-Adresse im Browser öffnen (am besten den Tailscale-HTTPS-Link):

- **Android (Chrome):** Menü ⋮ → **„App installieren“** bzw. „Zum Startbildschirm hinzufügen“
- **iPhone (Safari):** Teilen-Symbol → **„Zum Home-Bildschirm“**

Token einmalig eingeben, fertig.

## Bedienung

- **Geräte:** großen ⏻-Knopf antippen, um den PC zu starten. Der Punkt zeigt den Status
  (grün = online, gelb blinkend = startet gerade).
- **Autostart:** „+ Neuer Autostart“ wählen, dann Uhrzeit und Wochentage festlegen
  (Schnellwahl Mo–Fr, Wochenende, Täglich). Mit dem Schalter lassen sich Zeitpläne pausieren,
  ein Tipp auf einen Eintrag öffnet ihn zum Bearbeiten oder Löschen.
  Die Zeitpläne laufen **auf dem Server**, das Handy kann also aus sein.

## Fehlersuche

| Problem | Lösung |
|---|---|
| PC startet nicht | Wake-on-LAN im BIOS und beim Netzwerkadapter prüfen; Schnellstart aus; LAN-Kabel statt WLAN; `broadcast` testweise auf `255.255.255.255` setzen |
| Startet nur aus Ruhezustand, nicht aus „Herunterfahren“ | „ErP/EuP“ im BIOS deaktivieren; bei manchen Mainboards zusätzlich „Deep Sleep“ aus |
| Status zeigt immer „Aus“, obwohl der PC an ist | Windows blockiert Ping. Entweder in der Windows-Firewall „Datei- und Druckerfreigabe (Echoanforderung – ICMPv4 eingehend)“ erlauben oder in `config.json` beim Gerät `"check_ports": [3389]` mit einem offenen Port eintragen |
| „Ungültiges Token“ | Token aus `server/config.json` neu eingeben (⚙ → abmelden) |
| Autostart zur falschen Uhrzeit | `timezone` in `config.json` prüfen; in der App wird die Serverzeit angezeigt |

## Sicherheit

- Jeder API-Aufruf braucht das Token. Nach 10 Fehlversuchen wird die IP für 10 Minuten gesperrt.
- Das Token wird nur lokal auf dem Handy gespeichert.
- Am sichersten ist der Zugriff über Tailscale, dann ist der Server gar nicht öffentlich im Internet.
- `config.json` und `schedules.json` sind per `.gitignore` von Git ausgeschlossen.

## Dateien

```
pc-wake/
├── server/
│   ├── pcwake_server.py      # Server: Wake-on-LAN, Online-Check, Zeitplaner, API
│   ├── config.example.json   # Vorlage für config.json
│   └── pcwake.service        # systemd-Dienst für den Autostart des Servers
└── app/                      # Handy-App (PWA)
    ├── index.html, app.js, style.css
    ├── manifest.webmanifest, sw.js
    └── icon.svg, icon-192.png, icon-512.png
```
