# Chii Arcade – Spiele veröffentlichen

Diese Seite dokumentiert das **öffentliche** Veröffentlichungswerkzeug `tools/publish_game.py`. Es kann in jedes Spieleprojekt kopiert werden. Die eigentliche Android-App bleibt im privaten Repository `chii-arcade`.

## So arbeitet der Store

```text
Privates Spielprojekt -> signierte APK
        |
        v
Publisher prüft aapt, apksigner und SHA-256
        |
        +--> Öffentliches GitHub-Release (aktuell ChobitsChii/games)
        |
        +--> GitHub Pages: chii-arcade/catalog-v1.json (mit APK-URL)
                          |
                          v
                Chii Arcade Android App
                 - lokaler/offline Katalog
                 - Sicherheitsprüfung
                 - Android Installer
```

**Wichtig:** Die Spiele-Repositories dürfen privat bleiben. Im öffentlichen Release erscheinen ausschließlich die hochgeladenen APK-Dateien (und die automatisch erzeugten öffentlichen Quellcode-Archive des gewählten Release-Repositories, aktuell `games`). Nie private Game-Repositories als anonyme APK-Quelle im öffentlichen Katalog verlinken.

## Wiederverwendbare Einrichtung pro Spiel

1. `tools/publish_game.py` einmalig in das eigene Spieleprojekt kopieren, zum Beispiel als `tools/chii_arcade_publish.py`.
2. Datei `chii-arcade.json` im Spieleprojekt anlegen:

```json
{
  "id": "kaskellia",
  "title": "Kaskellia",
  "category": "Puzzle",
  "teaser": "Farbenfrohe Kugelrätsel",
  "description": "Spielebeschreibung",
  "symbol": "🌸",
  "android": {
    "packageName": "de.chobitschii.kaskellia",
    "signingCertificateSha256": "f180a9c294153bdc6fb700794bf980736ff1785331058beb933e474b8c8fcb5c"
  }
}
```

3. Fertige **Release-APK** mit dauerhaftem Signierschlüssel erzeugen und Versionscode gegenüber dem letzten Release erhöhen.
4. `gh auth login` (einmalig); Android SDK-Build-Tools `apksigner` und `aapt` installieren, `ANDROID_HOME` setzen.
5. Probe und Veröffentlichung:

```bash
python3 tools/chii_arcade_publish.py --config chii-arcade.json --apk /pfad/zur/spiel.apk --dry-run
python3 tools/chii_arcade_publish.py --config chii-arcade.json --apk /pfad/zur/spiel.apk
```

Beim ersten Start kontrolliert das Script Paket-ID und SHA-256 des öffentlichen Signierzertifikats, liest Versionsname/-code aus der APK, erstellt ein öffentliches Release und aktualisiert danach atomar den Katalog über die GitHub-API. Die APK selbst wird **nicht** in Pages eingecheckt.

Das Script verweigert Downgrades, identische Versionscodes mit veränderten APK-Inhalten, falsche Signaturen und unbestätigte Asset-Digests. Bei Fehlern bleibt ein bereits veröffentlichter Katalog unverändert. Bei erfolgreicher Wiederholung mit identischer APK darf der Vorgang erneut ausgeführt werden.

## Anleitung für KI-Coding-Assistenten

Wenn du als KI ein Spiel für Chii Arcade veröffentlichst:

- Lies zuerst die Signatur-/Exportregeln des jeweiligen Spielprojekts. **Niemals** einen neuen Signierschlüssel erzeugen, wenn bereits ein Release-Schlüssel existiert.
- Erhöhe für jedes tatsächliche Update den Android-`versionCode`; `versionName` nachvollziehbar anpassen.
- Prüfe das signierte APK mit `apksigner verify --print-certs` und kontrolliere die Paketkennung mit `aapt dump badging`.
- Pflege `chii-arcade.json` mit Titel, Kategorie, Beschreibung und dem dauerhaft dokumentierten öffentlichen Zertifikatsfingerabdruck. **Keine** Secrets, privaten Tokens oder Schlüssel in JSON schreiben.
- Verwende `--dry-run`, danach erst die tatsächliche Veröffentlichung bei explizitem Veröffentlichungsauftrag.
- Der Publisher legt ein neues öffentliches GitHub-Release an und aktualisiert den Pages-Katalog; niemals Release-Dateien direkt ins Pages-Repository hochladen.
- Prüfe anschließend die öffentliche Release-URL und den JSON-Katalog. GitHub Pages kann einige Minuten zum Deploy benötigen.
- Bei Fehlern kein Umschreiben der Versionsgeschichte, kein blindes `--clobber` und kein Downgrade.
- **Aktueller Android-Client:** Für Kaskellia ist der Zertifikatsfingerabdruck bereits fest hinterlegt. Weitere Spiele können katalogisiert werden, aber deren Installation benötigt vorerst eine explizite Freigabe im Client. Ein signiertes, dynamisches Vertrauensmodell ist geplant.
- Sobald ein eigener HTTPS-Server eingesetzt wird, ändern sich **nur** der Publisher als Veröffentlichungsziel und die im Katalog hinterlegten, geprüften APK-URLs – Signatur-, Versions- und Hashprüfungen bleiben Pflicht.

## Privatsphäre und Verteilung

Keine Nutzerkonten, keine Werbung, keine Analytics. APK-Installationen erfolgen ausschließlich über die Android-Systemoberfläche. Die Installation unbekannter APK-Quellen muss der Nutzer selbst erlauben. Android kann weitere Prüfungen durch Play Protect vornehmen.

Die öffentliche GitHub-Release-Ablage ist aktuell `ChobitsChii/games`. Langfristig empfiehlt sich ein gesondertes öffentliches `chii-arcade-releases`-Repository. Vor Umstellung muss die Android-App den neuen Download-Host bzw. Repositorypfad ausdrücklich zulassen.


## Cover und Screenshots separat veröffentlichen (ohne APK-Update)

Ab Medien-Erweiterung M04 sind im öffentlichen Katalog zwei **optionale** Felder vorgesehen:
`coverImage` (ein absolutes, vertrauenswürdiges WebP-URL) und `screenshots` (0–8 absolute WebP-URLs). Die Android-App lädt diese auf Abruf in ihren Offline-Bildcache, zeigt 16:9-Cover auf der Übersichts- und Detailseite und ermöglicht eine Vollbild-Galerie mit Wisch- und Pfeilnavigation. Fehlende Bilder sind kein Fehler; vorhandene Platzhalter bleiben.

**Private Spielprojekt-Konfiguration**: Damit das öffentliche Script Bilder ohne Ratespiel publizieren kann, stehen in der jeweiligen `chii-arcade.json` stattdessen **relative lokale WebP-Dateipfade**, z. B.:

```json
{
  "id": "kaskellia",
  "coverImage": "store-media/cover.webp",
  "screenshots": [
    "store-media/01-weltkarte.webp",
    "store-media/02-spielfeld.webp",
    "store-media/03-powerups.webp"
  ]
}
```

Andere bereits vorhandene Konfigurationsfelder (Titel, Android-Signatur usw.) **beibehalten**, hier nur die neuen Felder ergänzen. Cover: **16:9**, bevorzugt 1280×720 WebP; Screenshots: **echte, unbearbeitete Spielsituationen im Original-Seitenverhältnis** (Hochformat und Querformat erlaubt). Nur UI-freie Promoillustrationen als Cover nutzen; Screenshots nicht per KI erfinden oder verfälschen. Maximal 8 Screenshots, jedes WebP maximal 4 MB und zusammen maximal 22 MB. Dateinamen sollten keine Sonderzeichen oder Leerzeichen enthalten.

**Medien-Dry-Run:** aus dem Spielprojekt:

```bash
python3 /pfad/zu/ChobitsChii.github.io/chii-arcade/tools/publish_media.py --config chii-arcade.json --dry-run
```

**Nur nach ausdrücklicher Freigabe** ohne `--dry-run` ausführen. Das Programm benötigt `gh auth login` mit Schreibzugriff auf `ChobitsChii/ChobitsChii.github.io`. Es überprüft Dateien und Pfade, lädt die WebP-Dateien zuerst nach `chii-arcade/assets/<game-id>/` hoch (mit SHA-256-Hash im Dateinamen) und trägt danach die **absoluten** Cover-/Screenshot-URLs in `chii-arcade/catalog-v1.json` ein. Ein bestehendes, öffentlich spielbares Spiel muss bereits im Katalog vorhanden sein. **Keine APK wird gebaut oder hochgeladen, der Versionscode bleibt unverändert.** Alte veröffentlichte URLs bleiben für Caches stabil; neue Medienbytes erhalten einen neuen Dateinamen.

**Wichtig für spätere APK-Releases:** Der aktuelle `tools/publish_game.py` bewahrt `coverImage` und `screenshots` bestehender Katalogeinträge bei einem Spielupdate. Alle privaten Kopien des Publishers (z. B. Kaskellia und Tintaloria) sollten dieselbe Änderung erhalten, **bevor** sie ein zukünftiges APK-Update veröffentlichen, sonst überschreiben ältere Kopien die Medienfelder wieder. Für die Bildbereitstellung reicht `publish_media.py`, das vor einer Veröffentlichung jeweils vom öffentlichen Repository bezogen werden kann.

Bei Problemen niemals private Bilder unbeabsichtigt hochladen, den Katalog blind editieren, unveröffentlichte Spiele eintragen oder ein neues APK-Release erzwingen. App-Version vorerst aktualisieren, bevor Screenshots veröffentlicht werden: ältere Store-Versionen ignorieren die neuen optionalen Felder.

