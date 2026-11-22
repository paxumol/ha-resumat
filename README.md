# Wärmepumpe (Resümat) für Home Assistant

Home-Assistant-Integration für Wärmepumpen mit Resümat-Regler. Sie spricht **direkt per TCP mit dem Resümat-Adapter** (Standard-Port 6001) – ein zusätzlicher Service ist nicht nötig.

Das Protokoll ist eine Python-Portierung von [wpadapter](https://github.com/paxumol/wpadapter), die Parameterliste stammt aus dessen `MenuAdressen.csv`.

## Installation

**Manuell:** Ordner `custom_components/resumat` nach `/config/custom_components/resumat` kopieren und Home Assistant neu starten.

**HACS (privates Repo):** HACS kann private Repositories nur mit einem GitHub-Token installieren, das Zugriff auf dieses Repo hat. Ohne Token die manuelle Installation verwenden.

## Einrichtung

Einstellungen → Geräte & Dienste → Integration hinzufügen → „Wärmepumpe (Resümat)“ → IP des Adapters (z. B. `192.168.178.35`) und Port `6001`.

Der Adapter verträgt vermutlich nur eine Verbindung gleichzeitig – keine anderen Programme (z. B. wp-resumat-ms) parallel darauf zugreifen lassen.

## Entitäten (nur lesend)

- Temperaturen, Drücke, Betriebsstunden usw. als Sensoren mit Einheit
- 0/1-Werte als Binärsensoren, dazu „Heizbetrieb“, „Kühlbetrieb“, „Warmwasserbetrieb“
- Statusregister (Bitfelder) sind standardmäßig deaktiviert und können bei Bedarf aktiviert werden
- Das Kennwort (Menü 06.00) wird nicht als Entität angelegt

Das Abfrageintervall ist in den Optionen der Integration änderbar (Standard 60 s).

## Protokoll

| | Bytes |
|---|---|
| Anfrage | `10 02` · `01 15 <start:2> <len:2>` · `10 03` · CRC16 |
| Antwort | `FF 10 02` · `00 17 <daten>` · `10 03` · CRC16 · `FF` |

`0x10` im Nutzdatenteil wird verdoppelt (DLE-Stuffing). CRC: CRC-16/BUYPASS (Poly `0x8005`, Init `0`, nicht reflektiert) über den gestopften Nutzdatenteil. Gelesen wird der komplette Block `0x0000`–`0x0176` in einer Anfrage.
