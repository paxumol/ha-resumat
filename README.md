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
| 02.10 | Externe Anhebung | Zahl | −5 … +5 K |
| 04.04 | Warmwasser Soll | Zahl | 30 … 60 °C |
| 04.05 | Beckenwasser Temperatur Soll | Zahl | 15 … 40 °C |
| 04.06 | Warmwasser-Hysterese | Zahl | 5 … 10 K |
| 04.07 | Beckenwasser-Schaltdifferenz | Zahl | 0,5 … 5 K |
| 02.00 | Handabschaltung | Schalter | an = abgeschaltet |
| 04.00 | Abschaltung (Warmwasser) | Schalter | an = abgeschaltet |
| 02.13 / 02.14 | Sollwertänderung Ein / Aus | Uhrzeit | |
| 04.01 / 04.02 | Warmwasser Zeit ein / aus | Uhrzeit | |

Nach jedem Schreiben wird der Wert zurückgelesen; wurde er nicht übernommen, meldet Home Assistant einen Fehler. Die Bereiche stehen in `number.py` (`LIMITS`). Grenzen laut Waterkotte-Anleitung zum Resümat CD. Die „Externe Anhebung“ (02.10) verschiebt den Rücklauf-Sollwert um −5 … +5 K, wirkt aber nur im Zeitfenster 02.13–02.14 oder bei geschlossenem Digitaleingang „Externe Sollwertänderung“.

Die Uhrzeit der Wärmepumpe (05.00) wird nur angezeigt. Laut Parameterliste wäre sie beschreibbar, der Regler übernimmt geschriebene Werte aber nicht – die Uhr muss am Bedienfeld gestellt werden. Wichtig, weil das Zeitfenster 02.13–02.14 nach der Regleruhr läuft.

Zwei Schreibbefehle direkt nacheinander übernimmt der Regler nicht zuverlässig. Die Integration wartet deshalb nach jedem Schreiben 3 s, bevor der nächste Zugriff erfolgt.

Der Regler kennt 24:00:00 als Tagesende. Home Assistant kann das bei Uhrzeit-Entitäten nicht darstellen; sie zeigen dann 23:59:59, der Rohwert steht im Attribut `raw`.

Nicht angeschlossene Fühler meldet der Regler mit −111,11 °C (z. B. Temp-Raum ohne Raumfühler). Diese Werte werden als „nicht verfügbar“ angezeigt. Einzelne defekte Fühler lassen sich in Home Assistant über die Entitäts-Einstellungen deaktivieren.

Das Abfrageintervall ist in den Optionen der Integration änderbar (Standard 60 s).

## Protokoll

| | Bytes |
|---|---|
| Anfrage | `10 02` · `01 15 <start:2> <len:2>` · `10 03` · CRC16 |
| Antwort | `FF 10 02` · `00 17 <daten>` · `10 03` · CRC16 · `FF` |

`0x10` im Nutzdatenteil wird verdoppelt (DLE-Stuffing). CRC: CRC-16/BUYPASS (Poly `0x8005`, Init `0`, nicht reflektiert) über den gestopften Nutzdatenteil. Gelesen wird der komplette Block `0x0000`–`0x0176` in einer Anfrage.
