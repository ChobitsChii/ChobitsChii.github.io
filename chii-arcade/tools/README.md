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
