# Wärmepumpe (Resümat) für Home Assistant

Home-Assistant-Integration für Wärmepumpen mit Resümat-Regler. Sie spricht **direkt per TCP mit dem Resümat-Adapter** (Standard-Port 6001) – ein zusätzlicher Service ist nicht nötig.

Das Protokoll ist eine Python-Portierung von [wpadapter](https://github.com/paxumol/wpadapter), die Parameterliste stammt aus dessen `MenuAdressen.csv`.

## Installation

**Manuell:** Ordner `custom_components/resumat` nach `/config/custom_components/resumat` kopieren und Home Assistant neu starten.

**HACS (privates Repo):** HACS kann private Repositories nur mit einem GitHub-Token installieren, das Zugriff auf dieses Repo hat. Ohne Token die manuelle Installation verwenden.

## Einrichtung

Einstellungen → Geräte & Dienste → Integration hinzufügen → „Wärmepumpe (Resümat)“ → IP des Adapters (z. B. `192.168.178.35`) und Port `6001`.

Der Adapter verträgt vermutlich nur eine Verbindung gleichzeitig – keine anderen Programme (z. B. wp-resumat-ms) parallel darauf zugreifen lassen.

## Entitäten

**Lesend**
- Temperaturen, Drücke, Betriebsstunden usw. als Sensoren mit Einheit
- 0/1-Werte als Binärsensoren, dazu „Heizbetrieb“, „Kühlbetrieb“, „Warmwasserbetrieb“
- Statusregister (Bitfelder) sind standardmäßig deaktiviert und können bei Bedarf aktiviert werden
- Das Kennwort (Menü 06.00) wird nicht als Entität angelegt

**Schreibend**

| Menü | Name | Entität | Bereich |
|---|---|---|---|
| 02.10 | Externe Anhebung | Zahl | −5 … +10 °C |
| 04.04 | Warmwasser Soll | Zahl | 30 … 60 °C |
| 04.05 | Beckenwasser Temperatur Soll | Zahl | 15 … 40 °C |
| 04.06 / 04.07 | Warmwasser- / Beckenwasser-Hysterese | Zahl | 1 … 10 K |
| 02.00 | Handabschaltung | Schalter | an = abgeschaltet |
| 04.00 | Abschaltung (Warmwasser) | Schalter | an = abgeschaltet |
| 02.13 / 02.14 | Sollwertänderung Ein / Aus | Uhrzeit | |
| 04.01 / 04.02 | Warmwasser Zeit ein / aus | Uhrzeit | |

Nach jedem Schreiben wird der Wert zurückgelesen; wurde er nicht übernommen, meldet Home Assistant einen Fehler. Die Bereiche stehen in `number.py` (`LIMITS`). Ob die Steuerung negative Werte bei „Externe Anhebung“ akzeptiert, ist noch nicht geprüft – zuerst mit −1 testen und den Rücklauf-Sollwert (01.03) beobachten.

Die Uhrzeit der Wärmepumpe (05.00) wird nur angezeigt, nicht gesetzt.

Das Abfrageintervall ist in den Optionen der Integration änderbar (Standard 60 s).

## Protokoll

| | Bytes |
|---|---|
| Anfrage | `10 02` · `01 15 <start:2> <len:2>` · `10 03` · CRC16 |
| Antwort | `FF 10 02` · `00 17 <daten>` · `10 03` · CRC16 · `FF` |

`0x10` im Nutzdatenteil wird verdoppelt (DLE-Stuffing). CRC: CRC-16/BUYPASS (Poly `0x8005`, Init `0`, nicht reflektiert) über den gestopften Nutzdatenteil. Gelesen wird der komplette Block `0x0000`–`0x0176` in einer Anfrage.
