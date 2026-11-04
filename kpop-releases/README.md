# K-Pop Release Radar

Eine kleine Web-App (eine einzige HTML-Datei, keine Installation), die anstehende
und kürzlich erschienene K-Pop-Releases anzeigt – bis maximal 30 Tage zurück.

**Starten:** `index.html` im Browser öffnen (Doppelklick genügt).

## Funktionen
- **Demnächst**: angekündigte Comebacks (bis ca. 5 Monate im Voraus), inkl. deutscher Uhrzeit
- **Neu erschienen**: Releases der letzten 30 Tage, neueste zuerst
- „Meine Gruppen“ (inkl. Solo-Releases der Mitglieder) oder „Alle K-Pop“
- Filter nach Album / EP / Single und Suche nach Gruppe oder Titel
- Karte antippen → Tracklist (Titelsong mit ★)
- Gruppenliste wird geprüft: unbekannte/falsch geschriebene Namen werden mit Vorschlag markiert

## Datenquelle
[KPOP OFFICIAL](https://kpopofficial.com/kpop-comebacks/) – Comeback-Kalender, der nur
koreanische Musik enthält (über die öffentliche WordPress-API, ohne Key).

## Konzerte in Deutschland (Tab „Konzerte“)
- Alle angekündigten K-Pop-Konzerte in Deutschland ab heute, nach Monat gruppiert
- Große Tourneen kommen ohne Key von KPOP OFFICIAL
- Datum, Uhrzeit, Stadt, Halle, Status (abgesagt/verschoben), Vorverkaufsstart und Ticket-Link
- Optional zusätzlich Ticketmaster (findet auch kleinere Konzerte): Suche nach „K-Pop“ und nach jeder Gruppe aus „Meine Gruppen“

**Optional:** ein kostenloser Ticketmaster API-Key.
1. Auf https://developer-acct.ticketmaster.com/user/register registrieren
2. Unter „My Apps“ den **Consumer Key** kopieren
3. In der App im Tab „Konzerte“ unter „Ticketmaster API-Key“ einfügen

Hinweis: Konzerte, die nur über andere Anbieter (z. B. Eventim) verkauft werden,
können fehlen.

## Android-App (APK)
Der Ordner `android/` enthält eine Android-App, die die Web-App in einer WebView anzeigt.
Die APK wird automatisch von **GitHub Actions** gebaut (`.github/workflows/kpop-apk.yml`),
sobald sich etwas in `kpop-releases/` ändert (oder manuell über „Run workflow“).

Download danach unter **Releases → „K-Pop Release Radar (Android-APK)“ → KPop-Release-Radar.apk**.

Ohne eigene Secrets wird mit einem wechselnden Debug-Schlüssel signiert – ein Update
erfordert dann vorher das Deinstallieren der alten Version (Gruppen-Liste/API-Key neu eintragen).
Für feste Signatur die Repository-Secrets `KS_BASE64` (Keystore als Base64), `KS_PASSWORD`
und `KS_ALIAS` setzen.

Lokal bauen (Android SDK nötig): `cd kpop-releases/android && gradle assembleRelease`
