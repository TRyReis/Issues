# K-Pop Release Radar

Eine kleine Web-App (eine einzige HTML-Datei, keine Installation), die anstehende
und kürzlich erschienene K-Pop-Releases anzeigt – bis maximal 30 Tage zurück.

**Starten:** `index.html` im Browser öffnen (Doppelklick genügt).

## Funktionen
- **Heute**: alle Releases von heute (und morgen) nach deutscher Uhrzeit, mit Countdown
- **Demnächst** (eigener Tab): angekündigte Comebacks (bis ca. 5 Monate im Voraus), nach Tagen, inkl. deutscher Uhrzeit
- **Neu** (eigener Tab): Releases der letzten 30 Tage, neueste zuerst, nach Tagen
- Duplikate zwischen den Quellen werden zusammengeführt (Albumname ↔ Titelsong, Unit-Namen, ±1 Tag)
- Alle K-Pop-Artists inkl. Solo-Releases; Releases von „Meine Gruppen“ (und ihren Mitgliedern) mit ★ markiert
- Filter (optional, Standard: alles): Nur meine Gruppen · Nur Comebacks & Debüts · Gruppen/Solo · Album/EP/Single/OST · Zeitraum ±7/±14 Tage ·
  Japan-Releases und Pre-Releases ein-/ausblenden · Suche nach Artist oder Titel
- Design: Auto (wie System) / Hell / Dunkel
- Künstler, die man nicht sehen will, lassen sich in der Diskographie ausblenden (rückgängig unter „Ausgeblendete Künstler“)
- Karte antippen → Tracklist (Titelsong mit ★)
- Künstlernamen antippen → **komplette Diskographie** nach Jahren (inkl. angekündigter Releases
  und Solo-Releases der Mitglieder)
- Gruppenliste wird geprüft: unbekannte/falsch geschriebene Namen werden mit Vorschlag markiert

## Datenquellen (alle ohne Key)
- [KPOP OFFICIAL](https://kpopofficial.com/kpop-comebacks/) – Comeback-Kalender, nur koreanische Musik,
  inkl. angekündigter Releases (Hauptquelle, mit Cover, Uhrzeit, Tracklist)
- [kprofiles](https://kprofiles.com) – Monatslisten aller koreanischen Releases. Weil dort auch Trot, Ballade,
  Indie, Rock und Hip-Hop stehen, wird jeder Eintrag geprüft. Übernommen wird nur, wer Mitglied einer bekannten
  K-Pop-Gruppe ist, im K-Pop-Kalender Releases hat, in „Meine Gruppen“ steht oder laut MusicBrainz als k-pop
  eingestuft ist. Ohne 🇰🇷 nur bekannte K-Pop-Gruppen (&TEAM, NiziU). Keine reinen MV-Releases
- [Deezer](https://www.deezer.com) – vollständiger Katalog für die Diskographie und für Gruppen aus
  „Meine Gruppen“, die im Kalender fehlen (z. B. from20, cosmosy)
- [MusicBrainz](https://musicbrainz.org) – zusätzlich für Gruppen, die im Kalender fehlen
  (nur Künstler aus Südkorea bzw. mit K-Pop-Tag)

## Konzerte in Deutschland (Tab „Konzerte“)
- Alle angekündigten K-Pop-Konzerte in Deutschland ab heute, nach Monat gruppiert
- Optionale Filter (werden gespeichert): Stadt (Auswahlliste), „Nur meine Gruppen“, „Nur Konzerte“ (ohne Fan-Events/Festivals),
  Tribute-Shows ausblenden (Standard: alles)
- Nur K-Pop-Künstler (gleiche Prüfung wie bei den Releases); doppelte Termine aus mehreren Quellen werden zusammengeführt
- Ohne Key: K-Pop-Tourkalender von Radio:Active / KPOP IN GERMANY (alle Deutschland-Termine inkl. kleinerer
  Konzerte und Ticket-Link), KPOP OFFICIAL und Wikipedia
- Ticketstatus (Vorverkaufsbeginn, abgesagt, verschoben) nur aus Ticketmaster (live, offiziell). Der Ticketstatus
  des Tourkalenders wird nicht angezeigt, weil er dort nicht aktualisiert wird. Ohne direkten Ticket-Link gibt es
  „🔎 Tickets suchen“ (Suche nach Künstler, Stadt und Datum) (Tourseiten großer K-Pop-Tourneen, z. B. aespa,
  TWICE, BTS, LE SSERAFIM; abgesagte Termine werden markiert, Tribute-Shows gekennzeichnet und optional ausblendbar)
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
