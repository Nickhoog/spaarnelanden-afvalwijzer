# Spaarnelanden afvalkalender voor Home Assistant

Een Home Assistant-integratie (via HACS) die de afvalkalender van
[Spaarnelanden](https://www.spaarnelanden.nl) in Home Assistant zet: wanneer wordt
welke container geleegd, plus feestdagen en actuele meldingen.

> **Onofficieel.** Deze integratie is niet gemaakt door of verbonden aan Spaarnelanden.
> Ze gebruikt dezelfde openbare gegevens als
> [afvalwijzer.spaarnelanden.nl](https://afvalwijzer.spaarnelanden.nl).

## Ondersteunde gemeenten

Adressen waarvoor Spaarnelanden het afval ophaalt: **Haarlem** en **Zandvoort**.

## Installatie via HACS

1. Open HACS in Home Assistant.
2. Menu (⋮) → **Custom repositories**.
3. Repository: `https://github.com/Nickhoog/spaarnelanden-afvalwijzer`, type **Integration** → **Add**.
4. Zoek **Spaarnelanden - Afvalwijzer**, klik **Download** en herstart Home Assistant.
5. **Instellingen → Apparaten & diensten → Integratie toevoegen → Spaarnelanden - Afvalwijzer**.

Vereist Home Assistant 2026.10 of nieuwer.

### Handmatig

Kopieer `custom_components/spaarnelanden` naar de map `config/custom_components/` van je
Home Assistant en herstart.

## Configuratie

Vul je **postcode** en **huisnummer** in. Hebben meerdere adressen hetzelfde huisnummer
(bijv. 1A, 1B, 1 RD), dan kies je daarna je adres uit een lijst. Meerdere adressen
toevoegen kan: voeg de integratie gewoon nog een keer toe.

## Entities

Per adres komt er één apparaat "Spaarnelanden ‹adres›" met:

| Entity | Status | Attributen |
|---|---|---|
| Sensor per afvalsoort (bijv. *Gft en etensresten*, *Restafval*, *Plastic, blik, drinkpakken & papier (duobak)*, *Recyclewagen*) | datum van de eerstvolgende ophaling | `dagen_tot`, `afvalsoort`, `afvalstroom_id` |
| Vandaag | afvalsoorten die vandaag worden opgehaald, of `Geen` | `afvalsoorten` |
| Morgen | afvalsoorten die morgen worden opgehaald, of `Geen` | `afvalsoorten` |
| Meldingen | aantal actuele meldingen | `meldingen` (titel + tekst) |
| Kalender *Afvalkalender* | alle ophaaldata van dit en volgend jaar | |
| Kalender *Feestdagen en sluitingen* | feestdagen waarop o.a. het Milieuplein dicht is | |

Er komt alleen een sensor voor afvalsoorten die op jouw adres een ophaaldatum hebben.
De gegevens worden elke 12 uur ververst; na middernacht schuiven "Vandaag", "Morgen" en
`dagen_tot` vanzelf door.

## Voorbeeld: herinnering de avond ervoor

```yaml
automation:
  - alias: "Afval buiten zetten"
    triggers:
      - trigger: time
        at: "20:00:00"
    conditions:
      - condition: not
        conditions:
          - condition: state
            entity_id: sensor.spaarnelanden_teststraat_1_haarlem_morgen
            state: "Geen"
    actions:
      - action: notify.notify
        data:
          message: "Morgen wordt opgehaald: {{ states('sensor.spaarnelanden_teststraat_1_haarlem_morgen') }}"
```

Vervang de entity-id door die van jouw adres (te vinden onder het apparaat).

## English

Unofficial Home Assistant integration for the waste collection calendar of Spaarnelanden
(Haarlem and Zandvoort, the Netherlands). Install via HACS as a custom repository
(type *Integration*), add the integration and enter your postal code and house number.
It provides a date sensor per waste type, *Today*/*Tomorrow* sensors, a notices sensor,
a waste calendar and a holidays calendar. UI translations: Dutch and English.

## Ontwikkeling

```bash
uv sync
uv run pytest
```

Op Windows: `bash scripts/test-windows.sh` (Home Assistant draait niet native op Windows;
dit script zet lege vervangers voor Unix-modules op het pad).

## Licentie

MIT
