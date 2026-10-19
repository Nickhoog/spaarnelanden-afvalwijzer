# Spec: Spaarnelanden afvalkalender voor Home Assistant (HACS)

Datum: 2026-10-19 · Status: ontwerp goedgekeurd in chat, spec ter review

## 1. Doel en gebruikers

Een Home Assistant custom integration (installeerbaar via HACS) die de afvalkalender van
Spaarnelanden (Haarlem, Zandvoort) in Home Assistant zet. Bedoeld voor alle inwoners van
het verzorgingsgebied: netjes genoeg om openbaar te delen en later in de standaard
HACS-lijst te komen.

**Succescriteria**
- Toevoegen via de UI met alleen postcode + huisnummer (+ keuze bij meerdere adressen).
- Per afvalsoort een sensor met de juiste eerstvolgende ophaaldatum, ook na middernacht
  zonder nieuwe API-aanroep.
- Kalender met alle ophaaldata van dit en volgend jaar; aparte kalender met feestdagen.
- Sensoren 'Vandaag', 'Morgen' en 'Meldingen'.
- NL- en EN-vertalingen; alle tests groen onder Python 3.13 met
  `pytest-homeassistant-custom-component`; manifest/hacs.json voldoen aan hassfest/HACS.
- Live geverifieerd tegen de echte API en in een echte HA-installatie.

## 2. Databron (geverifieerd, zie `docs/onderzoek-databron.md`)

Basis-URL `https://afvalwijzer.spaarnelanden.nl/rest`, open JSON, geen authenticatie.

| Aanroep | Gebruik |
|---|---|
| `GET /adressen/{POSTCODE}-{HUISNUMMER}` | adres → `[{bagId, postcode, huisnummer, huisletter, huisnummerToevoeging, openbareRuimteNaam, woonplaatsNaam, …}]` |
| `GET /adressen/{bagId}/afvalstromen` | `[{id, title, menu_title, icon, ophaaldatum|null, …}]` → namen en iconen |
| `GET /adressen/{bagId}/kalender/{jaar}` | `[{afvalstroom_id, ophaaldatum}]` |
| `GET /feestdagen/{YYYY-MM-DD}/{YYYY-MM-DD}` | `[{datum, naam}]` |
| `GET /app/meldingen/{bagId}` | `[{id, kop, content(HTML), afwijsbaar}]` |

## 3. Architectuur

Aanpak: zelfstandige integratie met eigen kleine API-module, geen externe Python-
afhankelijkheden (`requirements: []`).

```
custom_components/spaarnelanden/
  __init__.py        setup/unload van config entry, platforms [sensor, calendar]
  manifest.json      domain "spaarnelanden", name "Spaarnelanden", version "0.1.0",
                     iot_class "cloud_polling", config_flow true,
                     integration_type "service", requirements [], dependencies [],
                     codeowners, documentation, issue_tracker
  const.py           DOMAIN, BASE_URL, UPDATE_INTERVAL = 12 h, REQUEST_TIMEOUT = 30 s,
                     ICON_MAP, DEFAULT_ICON
  api.py             SpaarnelandenClient + dataclasses + pure parse-functies
  coordinator.py     SpaarnelandenCoordinator (DataUpdateCoordinator[SpaarnelandenData])
  entity.py          gemeenschappelijke basisklasse (DeviceInfo, has_entity_name)
  config_flow.py     stappen "user" en "select_address"
  sensor.py          afvalsoort-, vandaag-, morgen- en meldingen-sensoren
  calendar.py        afvalkalender en feestdagenkalender
  strings.json, translations/nl.json, translations/en.json
hacs.json            {"name": "Spaarnelanden", "render_readme": true,
                      "homeassistant": gelijk aan de HA-versie waartegen de tests
                      draaien (de versie die pytest-homeassistant-custom-component vastzet)}
README.md, LICENSE, .github/workflows/validate.yml (hassfest + hacs/action),
.github/workflows/tests.yml (pytest), pyproject.toml (testafhankelijkheden),
tests/ + tests/fixtures/*.json
```

### 3.1 `api.py`

Dataclasses (frozen):
- `Address(bag_id, street, house_number: int, house_letter, addition, postcode, city)`
  met property `label` → bv. `"Teststraat 1A, Haarlem"` (toevoeging met spatie:
  `"Teststraat 1 RD, Haarlem"`).
- `WasteStream(id: int, title: str, icon: str)`.
- `Pickup(stream_id: int, date: date)`.
- `Holiday(date: date, name: str)`.
- `Notice(id, title, text)` (HTML gestript, entities gedecodeerd).

Pure functies: `normalize_postcode(str) -> str` (spaties weg, hoofdletters, valideert
`^[1-9][0-9]{3}[A-Z]{2}$`, anders `ValueError`), `parse_addresses`, `parse_streams`,
`parse_calendar`, `parse_holidays`, `parse_notices`. Items zonder of met ongeldige datum
worden overgeslagen; een top-level antwoord dat geen lijst is → `SpaarnelandenResponseError`.

`SpaarnelandenClient(session: aiohttp.ClientSession)` met async methoden
`lookup_addresses(postcode, house_number)`, `get_streams(bag_id)`,
`get_calendar(bag_id, year)`, `get_holidays(start, end)`, `get_notices(bag_id)`.
Timeout/verbindingsfout/HTTP-status ≥ 400 → `SpaarnelandenConnectionError`; ongeldige
JSON of verkeerde vorm → `SpaarnelandenResponseError`. Beide erven van
`SpaarnelandenError`.

### 3.2 `coordinator.py`

`SpaarnelandenData(streams: dict[int, WasteStream], pickups: list[Pickup] (gesorteerd),
holidays: list[Holiday], notices: list[Notice])`.

`_async_update_data` (elke 12 uur):
1. `get_streams` en `get_calendar(huidig jaar)` — **verplicht**; fout → `UpdateFailed`.
2. `get_calendar(volgend jaar)`, `get_holidays(1 jan huidig jaar, 31 dec volgend jaar)`,
   `get_notices` — **optioneel**; fout → debug-log, lege lijst.
3. Pickups samenvoegen, dubbele (stream_id, datum) ontdubbelen, sorteren.

De coordinator rekent niets relatief aan "vandaag"; dat doen de entities.

### 3.3 `config_flow.py`

- Stap `user`: velden `postcode` (tekst), `house_number` (positief geheel getal).
  - Ongeldige postcode → fout `invalid_postcode` op het veld.
  - API-fout → `cannot_connect`; leeg resultaat → `address_not_found`.
  - Precies één adres → direct entry aanmaken.
  - Meerdere adressen → stap `select_address`.
- Stap `select_address`: dropdown met `Address.label`, waarde = `bag_id`.
- `unique_id` = `bag_id`; `_abort_if_unique_id_configured()` → `already_configured`.
- Entry-titel = `Address.label`; entry-data: `bag_id`, `postcode`, `house_number`, `label`.

### 3.4 Entities

Alle entities: `CoordinatorEntity`, `has_entity_name = True`, één `DeviceInfo` per entry
(`identifiers {(DOMAIN, bag_id)}`, naam `"Spaarnelanden {label}"`, manufacturer
`"Spaarnelanden"`, `entry_type SERVICE`).

Elke entity registreert een `async_track_time_change(hour=0, minute=0, second=1)` die
`async_write_ha_state()` aanroept, zodat datums relatief aan vandaag kloppen na middernacht.
"Vandaag" = `dt_util.now().date()` (HA-tijdzone).

| Entity | unique_id | Status | Attributen |
|---|---|---|---|
| Sensor per afvalsoort (alleen soorten met ≥1 pickup in data) | `{bag_id}_{stream_id}` | eerstvolgende datum ≥ vandaag, `device_class DATE`; geen → `None` | `dagen_tot`, `afvalsoort`, `afvalstroom_id` |
| Sensor "Vandaag" (translation_key `today`) | `{bag_id}_today` | titels van soorten vandaag, `", "`-gescheiden, anders `"Geen"` | `afvalsoorten` (lijst) |
| Sensor "Morgen" (`tomorrow`) | `{bag_id}_tomorrow` | idem voor morgen | `afvalsoorten` |
| Sensor "Meldingen" (`notices`) | `{bag_id}_notices` | aantal meldingen (int) | `meldingen`: lijst `{titel, tekst}` |
| Kalender "Afvalkalender" (`waste`) | `{bag_id}_calendar` | eerstvolgende ophaling | — |
| Kalender "Feestdagen en sluitingen" (`holidays`) | `{bag_id}_holidays` | eerstvolgende feestdag | — |

- Afvalsoort-sensor: naam = `WasteStream.title`; icoon via `ICON_MAP`
  (`gft-line→mdi:leaf`, `rest2-line→mdi:trash-can`, `duocontainer-line→mdi:recycle`,
  `recyclewagen-line→mdi:truck`, `papier-line→mdi:newspaper`, `pbd-line→mdi:bottle-soda`,
  `glas-line→mdi:glass-fragile`), anders `mdi:trash-can-outline`.
- Kalender-events: hele dag (`start = datum`, `end = datum + 1 dag`), `summary` = titel
  van de soort resp. naam van de feestdag; `async_get_events(start, end)` geeft events die
  overlappen met het venster.
- Soorten die bij een latere update nieuw verschijnen krijgen pas een sensor na herladen
  van de integratie (v1; bewust eenvoudig).

### 3.5 Foutafhandeling

- Eerste refresh mislukt → `ConfigEntryNotReady` (via
  `async_config_entry_first_refresh`).
- Latere fout in verplichte data → `UpdateFailed`; entities blijven beschikbaar met de
  laatst geladen gegevens (`available` = er is data), want de kalender blijft maanden
  geldig. Gewijzigd na de eindreview (2026-10-19); eerder: `unavailable` tot de volgende
  geslaagde update.
- Optionele data mislukt → rest blijft werken; debug-log.

## 4. Vertalingen

`strings.json` (EN, bron) + `translations/en.json` + `translations/nl.json`: config-flow
titels/velden/beschrijvingen, fouten (`invalid_postcode`, `cannot_connect`,
`address_not_found` met hint "alleen Haarlem en Zandvoort"), abort `already_configured`,
entity-namen `today`, `tomorrow`, `notices`, `waste`, `holidays`. Afvalsoortnamen komen
onvertaald uit de API.

## 5. Tests

Testtooling: `uv` (gebruiker akkoord) met Python 3.13, `pytest`,
`pytest-homeassistant-custom-component`, `aioresponses`, `freezegun` (via HA-fixture).
Werkwijze: test eerst, dan code, kleine stappen.

- `tests/fixtures/`: ingekorte echte API-antwoorden, **geanonimiseerd** (verzonnen bagId
  `0000200000000001`, verzonnen straat "Teststraat", postcode `9999ZZ`).
- `test_api.py`: normalisatie postcode; parse van adressen (één/meerdere/leeg), streams,
  kalender (null/ongeldige datum overslaan), feestdagen, meldingen (HTML strippen);
  client-foutvertaling (timeout, 500, ongeldige JSON, geen lijst).
- `test_config_flow.py`: één adres → entry; meerdere → select_address → entry; elke fout;
  duplicaat → abort.
- `test_coordinator.py`: samenvoegen/ontdubbelen jaren; optionele fouten worden
  opgevangen; verplichte fout → UpdateFailed.
- `test_sensor.py`: volgende datum en `dagen_tot`; vandaag/morgen/"Geen"; meldingen;
  overgang na middernacht (bevroren tijd verschuiven).
- `test_calendar.py`: events binnen venster; eerstvolgend event; feestdagenkalender.
- `test_init.py`: setup en unload van een entry; `ConfigEntryNotReady` bij fout.

## 6. Verificatie en oplevering

- Lokaal: volledige pytest-run groen; handmatige controle manifest/hacs.json tegen de
  HACS/hassfest-eisen.
- Live: klein script tegen de echte API met een adres dat de gebruiker opgeeft (niet in de
  repo), daarna test in een echte HA-installatie (keuze welke volgt bij uitvoering).
- GitHub Actions-workflows staan klaar maar draaien pas na een push.
- Alles uitgevoerd wordt bijgehouden in `docs/LOGBOEK.md`; testchecklist in
  `docs/testchecklist.md`.

## 7. Buiten scope v1

Options flow, diagnostics, eigen notificaties, dynamisch toevoegen van nieuwe soorten
zonder herladen, publicatie (GitHub-repo, release, brand-icoon, aanmelding standaard
HACS-lijst). Publicatie gebeurt pas na expliciet akkoord en een audit op gevoelige
gegevens; repo standaard privé.
