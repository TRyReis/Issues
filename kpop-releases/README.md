# K-Pop Release Radar

Eine kleine Web-App (eine einzige HTML-Datei, keine Installation), die anstehende
und kürzlich erschienene K-Pop-Releases anzeigt – bis maximal 30 Tage zurück.

**Starten:** `index.html` im Browser öffnen (Doppelklick genügt).

## Funktionen
- **Demnächst**: angekündigte Releases (bis ca. 4 Monate im Voraus)
- **Neu erschienen**: Releases der letzten 30 Tage, neueste zuerst
- Filter nach Album / EP / Single und Suche nach Gruppe oder Titel
- Karte antippen → Tracklist (Lieder) des Releases
- „Meine Gruppen“: eigene Liste von Gruppen pflegen (wird im Browser gespeichert)

## Datenquelle
[MusicBrainz](https://musicbrainz.org) (frei, ohne API-Key) und das
[Cover Art Archive](https://coverartarchive.org). Geladen werden alle Releases mit
dem Tag „k-pop“ sowie alle Releases der Gruppen aus „Meine Gruppen“.
Hinweis: Angekündigte Releases erscheinen nur, wenn sie bereits von der
Community in MusicBrainz eingetragen wurden.
