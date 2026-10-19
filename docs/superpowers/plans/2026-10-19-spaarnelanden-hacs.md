# Spaarnelanden HACS-integratie – implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een HACS-installeerbare Home Assistant custom integration `spaarnelanden` die ophaaldata, feestdagen en meldingen van Spaarnelanden als sensoren en kalenders toont.

**Architecture:** Zelfstandige integratie zonder externe Python-dependencies. `api.py` (HTTP + pure parse-functies) → `coordinator.py` (12-uurs ophalen, één `SpaarnelandenData`) → entities (`sensor.py`, `calendar.py`) die zelf relatief aan "vandaag" rekenen en om 00:00:01 hun status opnieuw schrijven.

**Tech Stack:** Python 3.13 via `uv`, Home Assistant (versie zoals vastgezet door `pytest-homeassistant-custom-component`), aiohttp (HA-sessie), pytest + `pytest-homeassistant-custom-component` (fixtures `hass`, `aioclient_mock`, `freezer`, `enable_custom_integrations`).

**Spec:** `docs/superpowers/specs/2026-10-19-spaarnelanden-hacs-design.md` (lees eerst), achtergrond `docs/onderzoek-databron.md`.

## Global Constraints

- Domain `spaarnelanden`; manifest: `version "0.1.0"`, `iot_class "cloud_polling"`, `config_flow true`, `integration_type "service"`, `requirements []`, `dependencies []`.
- `BASE_URL = "https://afvalwijzer.spaarnelanden.nl/rest"`, `UPDATE_INTERVAL = timedelta(hours=12)`, `REQUEST_TIMEOUT = 30` s.
- Postcode-regex na normalisatie: `^[1-9][0-9]{3}[A-Z]{2}$`.
- "Vandaag" = `dt_util.now().date()` (HA-tijdzone), nooit UTC-datum.
- Geen echte adressen of bagIds in de repo: fixtures gebruiken bagId `0000200000000001`, straat `Teststraat`, postcode `9999ZZ`, woonplaats `Haarlem`.
- Git: lokaal, `user.email = noreply@localhost`, commit-trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Nooit pushen.
- Elke uitgevoerde handeling (installaties, testruns, live checks) wordt bijgehouden in `docs/LOGBOEK.md` (Nederlands).
- Afwijking van spec §5: HTTP-mocking gebeurt met HA's `aioclient_mock`-fixture i.p.v. `aioresponses` (zelfde dekking, één afhankelijkheid minder).

## Review Focus

1. **Volgende ophaling staat alleen in de kalender van volgend jaar** (eind december) → sensor moet die datum tonen. Test in Task 4 (`test_merges_next_year`) en Task 6 (`test_next_date_from_next_year`).
2. **Tijdzone rond middernacht**: om 23:30 UTC (= 00:30 Europe/Amsterdam) is "vandaag" de lokale datum. Test in Task 6 (`test_today_uses_local_timezone`).
3. **Kalender bevat een `afvalstroom_id` dat niet in `/afvalstromen` staat** → geen crash; naam `"Afvalstroom {id}"`, standaardicoon. Test in Task 6 (`test_unknown_stream_id_fallback`).
4. **Optioneel endpoint geeft HTML in plaats van JSON** (zoals de 404-pagina van `waste-calendar`) → `SpaarnelandenResponseError`, coordinator negeert het. Test in Task 3 (`test_html_response_raises_response_error`) en Task 4.
5. **Postcode met spatie/kleine letters en huisnummer met veel resultaten** (`"2011 vb"`, flatgebouw) → genormaliseerd; dropdown gesorteerd op label. Test in Task 2 (`test_normalize_postcode`) en Task 5 (`test_multiple_addresses_sorted`).

---

### Task 1: Tooling en scaffold

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `custom_components/spaarnelanden/{__init__.py,manifest.json,const.py}`, `hacs.json`, `tests/__init__.py`, `tests/conftest.py`, `tests/test_manifest.py`

**Interfaces:**
- Produces: `const.py` met `DOMAIN = "spaarnelanden"`, `BASE_URL`, `UPDATE_INTERVAL`, `REQUEST_TIMEOUT`, `ICON_MAP: dict[str, str]` (7 mappings uit spec §3.4), `DEFAULT_ICON = "mdi:trash-can-outline"`, `PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]`, `CONF_BAG_ID = "bag_id"`, `CONF_POSTCODE = "postcode"`, `CONF_HOUSE_NUMBER = "house_number"`, `CONF_LABEL = "label"`. `tests/conftest.py` met autouse-fixture die `enable_custom_integrations` activeert.

- [ ] **Step 1: Dry run installatie** — `winget show astral-sh.uv` en log de versie in `docs/LOGBOEK.md`. Vraag niets opnieuw; de gebruiker heeft uv goedgekeurd.
- [ ] **Step 2: Installeer uv** — `winget install --id astral-sh.uv -e`; open nieuwe shell; `uv --version` toont een versie. Log.
- [ ] **Step 3: `pyproject.toml`** — `[project] name="spaarnelanden-hacs"`, `requires-python=">=3.13"`; `[dependency-groups] dev = ["pytest-homeassistant-custom-component"]`; `[tool.pytest.ini_options] asyncio_mode="auto"`, `testpaths=["tests"]`. Run `uv python install 3.13` en `uv sync`. Expected: geslaagd. Noteer in LOGBOEK welke `homeassistant`-versie meekwam (`uv pip show homeassistant`).
- [ ] **Step 4: `.gitignore`** — `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`, `scratch/`.
- [ ] **Step 5: Failing test `tests/test_manifest.py`**

```python
def test_manifest_fields():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["domain"] == "spaarnelanden"
    assert m["version"] == "0.1.0"
    assert m["iot_class"] == "cloud_polling"
    assert m["config_flow"] is True
    assert m["integration_type"] == "service"
    assert m["requirements"] == []
    assert set(m) >= {"name", "codeowners", "documentation", "issue_tracker", "dependencies"}

def test_hacs_json():
    h = json.loads(HACS.read_text(encoding="utf-8"))
    assert h["name"] == "Spaarnelanden" and h["render_readme"] is True
    assert h["homeassistant"]  # = HA-versie uit Step 3
```

- [ ] **Step 6:** `uv run pytest tests/test_manifest.py -v` → FAIL (bestand ontbreekt).
- [ ] **Step 7:** Maak `manifest.json` (velden zoals Global Constraints; `codeowners: ["@OWNER"]` — placeholder-handle, de gebruiker bevestigt bij publicatie; documentation/issue_tracker naar `https://github.com/OWNER/spaarnelanden-hacs` met dezelfde opmerking in LOGBOEK), `hacs.json`, `const.py`, lege `__init__.py` met docstring. Manifest-sleutels in hassfest-volgorde: `domain`, `name`, daarna alfabetisch.
- [ ] **Step 8:** `uv run pytest -v` → PASS.
- [ ] **Step 9: Commit** — `chore: scaffold integratie en testtooling`.

### Task 2: Dataclasses en parse-functies

**Files:**
- Create: `custom_components/spaarnelanden/api.py`, `tests/fixtures/{addresses_multi.json,addresses_single.json,streams.json,calendar_2026.json,calendar_2027.json,holidays.json,notices.json}`, `tests/test_api_parse.py`

**Interfaces:**
- Produces (in `api.py`): exceptions `SpaarnelandenError`, `SpaarnelandenConnectionError(SpaarnelandenError)`, `SpaarnelandenResponseError(SpaarnelandenError)`; frozen dataclasses `Address(bag_id: str, street: str, house_number: int, house_letter: str, addition: str, postcode: str, city: str)` met property `label: str`; `WasteStream(id: int, title: str, icon: str)`; `Pickup(stream_id: int, date: date)`; `Holiday(date: date, name: str)`; `Notice(id: int, title: str, text: str)`. Functies `normalize_postcode(value: str) -> str` (ValueError bij ongeldig), `parse_addresses(data: Any) -> list[Address]`, `parse_streams(data: Any) -> dict[int, WasteStream]`, `parse_calendar(data: Any) -> list[Pickup]`, `parse_holidays(data: Any) -> list[Holiday]`, `parse_notices(data: Any) -> list[Notice]`. Alle parse-functies: niet-lijst → `SpaarnelandenResponseError`.

- [ ] **Step 1: Fixtures** — ingekorte echte vormen (zie `docs/onderzoek-databron.md`) met uitsluitend de geanonimiseerde waarden uit Global Constraints. `addresses_multi.json`: 3 items (letter `""`/toev. `"RD"`, letter `"A"`, letter `"B"`) in volgorde B, RD, A. `streams.json`: ids 48, 42, 44, 56 met titels/icons uit onderzoek + één item zonder `ophaaldatum` (id 39). `calendar_2026.json`: o.a. `{"afvalstroom_id":48,"ophaaldatum":"2026-10-27"}`, `{"afvalstroom_id":42,"ophaaldatum":"2026-10-29"}`, `{"afvalstroom_id":44,"ophaaldatum":"2026-10-29"}`, één item met `"ophaaldatum": null`, één met `"2026-13-45"`, en één tot `2027-01-05` (48). `calendar_2027.json`: `2027-01-05` (48, duplicaat) en `2027-01-07` (42). `holidays.json`: `{"datum":"2026-12-25","naam":"1e kerstdag; Milieuplein gesloten"}`. `notices.json`: `{"id":1,"kop":"Let op","content":"<p>Ophaling &amp; meer</p>","afwijsbaar":0}` en een item met `content: ""`.
- [ ] **Step 2: Failing tests** in `tests/test_api_parse.py`:

```python
@pytest.mark.parametrize("raw,expected", [("2011VB","2011VB"),("2011 vb","2011VB"),(" 2011vb ","2011VB")])
def test_normalize_postcode(raw, expected): assert normalize_postcode(raw) == expected

@pytest.mark.parametrize("raw", ["0123AB","12345","ABCD12",""])
def test_normalize_postcode_invalid(raw):
    with pytest.raises(ValueError): normalize_postcode(raw)

def test_parse_addresses_labels():
    labels = {a.label for a in parse_addresses(load("addresses_multi.json"))}
    assert labels == {"Teststraat 1 RD, Haarlem", "Teststraat 1A, Haarlem", "Teststraat 1B, Haarlem"}

def test_parse_addresses_empty(): assert parse_addresses([]) == []

def test_parse_streams(): s = parse_streams(load("streams.json")); assert s[48] == WasteStream(48, "Gft en etensresten", "gft-line")

def test_parse_calendar_skips_invalid():
    p = parse_calendar(load("calendar_2026.json"))
    assert Pickup(48, date(2026,10,27)) in p
    assert all(isinstance(x.date, date) for x in p)   # null en 2026-13-45 overgeslagen

def test_parse_holidays(): assert parse_holidays(load("holidays.json"))[0] == Holiday(date(2026,12,25), "1e kerstdag; Milieuplein gesloten")

def test_parse_notices_strips_html():
    n = parse_notices(load("notices.json"))
    assert n == [Notice(1, "Let op", "Ophaling & meer")]   # lege content overgeslagen

@pytest.mark.parametrize("fn", [parse_addresses, parse_streams, parse_calendar, parse_holidays, parse_notices])
def test_non_list_raises(fn):
    with pytest.raises(SpaarnelandenResponseError): fn({"error": "x"})
```

- [ ] **Step 3:** `uv run pytest tests/test_api_parse.py -v` → FAIL (ImportError).
- [ ] **Step 4:** Implementeer in `api.py`. Label: `f"{street} {house_number}{house_letter}"` + (`f" {addition}"` als addition) + `f", {city}"`. HTML strippen met `re.sub(r"<[^>]*>", "", s)` + `html.unescape` + `strip()`.
- [ ] **Step 5:** `uv run pytest tests/test_api_parse.py -v` → PASS.
- [ ] **Step 6: Commit** — `feat: dataclasses en parsers voor Spaarnelanden-API`.

### Task 3: HTTP-client

**Files:**
- Modify: `custom_components/spaarnelanden/api.py`
- Create: `tests/test_api_client.py`

**Interfaces:**
- Consumes: parse-functies en exceptions uit Task 2.
- Produces: `class SpaarnelandenClient(session: aiohttp.ClientSession)` met `async lookup_addresses(postcode: str, house_number: int) -> list[Address]` (normaliseert postcode zelf; ValueError propageert), `async get_streams(bag_id: str) -> dict[int, WasteStream]`, `async get_calendar(bag_id: str, year: int) -> list[Pickup]`, `async get_holidays(start: date, end: date) -> list[Holiday]`, `async get_notices(bag_id: str) -> list[Notice]`. URLs exact zoals spec §2.

- [ ] **Step 1: Failing tests** (fixtures `hass`, `aioclient_mock`; client met `async_get_clientsession(hass)`):

```python
async def test_lookup_addresses_url(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE_URL}/adressen/9999ZZ-1", json=load("addresses_multi.json"))
    assert len(await client(hass).lookup_addresses("9999 zz", 1)) == 3

async def test_get_calendar_url(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE_URL}/adressen/0000200000000001/kalender/2026", json=load("calendar_2026.json"))
    assert await client(hass).get_calendar("0000200000000001", 2026)

async def test_get_holidays_url(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE_URL}/feestdagen/2026-01-01/2027-12-31", json=load("holidays.json"))
    assert await client(hass).get_holidays(date(2026,1,1), date(2027,12,31))

async def test_timeout_raises_connection_error(hass, aioclient_mock):
    aioclient_mock.get(ANY_URL, exc=asyncio.TimeoutError)
    with pytest.raises(SpaarnelandenConnectionError): await client(hass).get_streams("0000200000000001")

async def test_http_500_raises_connection_error(hass, aioclient_mock):
    aioclient_mock.get(ANY_URL, status=500)
    with pytest.raises(SpaarnelandenConnectionError): await client(hass).get_streams("0000200000000001")

async def test_html_response_raises_response_error(hass, aioclient_mock):
    aioclient_mock.get(ANY_URL, text="<!doctype html><html></html>", headers={"Content-Type": "text/html"})
    with pytest.raises(SpaarnelandenResponseError): await client(hass).get_notices("0000200000000001")
```

(`ANY_URL` = de concrete URL van de aangeroepen methode.)

- [ ] **Step 2:** `uv run pytest tests/test_api_client.py -v` → FAIL.
- [ ] **Step 3:** Implementeer één private `_get_json(path: str) -> Any` met `asyncio.timeout(REQUEST_TIMEOUT)`; `aiohttp.ClientError`/`TimeoutError`/status ≥ 400 → `SpaarnelandenConnectionError`; `await resp.json(content_type=None)` en `ValueError`/`aiohttp.ContentTypeError` → `SpaarnelandenResponseError`.
- [ ] **Step 4:** `uv run pytest tests/ -v` → PASS.
- [ ] **Step 5: Commit** — `feat: async HTTP-client met foutvertaling`.

### Task 4: Coordinator

**Files:**
- Create: `custom_components/spaarnelanden/coordinator.py`, `tests/test_coordinator.py`

**Interfaces:**
- Consumes: `SpaarnelandenClient` (Task 3).
- Produces: `@dataclass SpaarnelandenData(streams: dict[int, WasteStream], pickups: list[Pickup], holidays: list[Holiday], notices: list[Notice])`; `class SpaarnelandenCoordinator(DataUpdateCoordinator[SpaarnelandenData])` met `__init__(hass, entry: ConfigEntry, client: SpaarnelandenClient)`, attribuut `bag_id: str` (uit `entry.data[CONF_BAG_ID]`), `update_interval=UPDATE_INTERVAL`. Type-alias `SpaarnelandenConfigEntry = ConfigEntry[SpaarnelandenCoordinator]`.

- [ ] **Step 1: Failing tests** (client als `AsyncMock(spec=SpaarnelandenClient)`, `freezer.move_to("2026-12-30 12:00:00+01:00")`):

```python
async def test_merges_next_year(hass, freezer):  # 2026 + 2027 samengevoegd, duplicaat 48@2027-01-05 één keer, gesorteerd
    data = await coordinator._async_update_data()
    assert data.pickups == sorted(data.pickups, key=lambda p: (p.date, p.stream_id))
    assert data.pickups.count(Pickup(48, date(2027,1,5))) == 1
    client.get_calendar.assert_any_await(BAG, 2027)
    client.get_holidays.assert_awaited_with(date(2026,1,1), date(2027,12,31))

@pytest.mark.parametrize("failing", ["get_notices", "get_holidays", "next_year_calendar"])
async def test_optional_failures_ignored(hass, failing): ...  # raises SpaarnelandenError → resp. lijst leeg / alleen 2026-pickups; geen exception

@pytest.mark.parametrize("failing", ["get_streams", "current_year_calendar"])
async def test_required_failure_raises_update_failed(hass, failing):
    with pytest.raises(UpdateFailed): await coordinator._async_update_data()
```

- [ ] **Step 2:** `uv run pytest tests/test_coordinator.py -v` → FAIL.
- [ ] **Step 3:** Implementeer volgens spec §3.2; "huidig jaar" = `dt_util.now().year`. Optionele aanroepen elk in eigen `try/except SpaarnelandenError` met `_LOGGER.debug`. Ontdubbelen via `sorted(set(pickups), key=lambda p: (p.date, p.stream_id))`.
- [ ] **Step 4:** `uv run pytest tests/ -v` → PASS.
- [ ] **Step 5: Commit** — `feat: coordinator met verplichte en optionele data`.

### Task 5: Config flow en vertalingen

**Files:**
- Create: `custom_components/spaarnelanden/config_flow.py`, `strings.json`, `translations/en.json`, `translations/nl.json`, `tests/test_config_flow.py`

**Interfaces:**
- Consumes: `SpaarnelandenClient.lookup_addresses`, `Address`, `normalize_postcode`, exceptions, `CONF_*`.
- Produces: `SpaarnelandenConfigFlow(ConfigFlow, domain=DOMAIN)`, `VERSION = 1`, stappen `user` en `select_address`; entry `data = {bag_id, postcode, house_number, label}`, `title = label`, `unique_id = bag_id`. Translation keys (ook gebruikt door Tasks 6–7): `entity.sensor.today/tomorrow/notices.name`, `entity.calendar.waste/holidays.name`.

- [ ] **Step 1: Failing tests** (patch `custom_components.spaarnelanden.config_flow.SpaarnelandenClient.lookup_addresses`):

```python
async def test_single_address_creates_entry(hass): ...
    # input {"postcode": "9999 zz", "house_number": 1} → type CREATE_ENTRY,
    # title "Teststraat 1, Haarlem", data["bag_id"] == "0000200000000001", data["postcode"] == "9999ZZ"
async def test_multiple_addresses_sorted(hass): ...
    # → step_id "select_address"; opties-labels in volgorde ["Teststraat 1 RD, Haarlem", "Teststraat 1A, Haarlem", "Teststraat 1B, Haarlem"];
    # kiezen → CREATE_ENTRY met gekozen bag_id
async def test_invalid_postcode(hass): ...      # "12345" → errors == {"postcode": "invalid_postcode"}, client niet aangeroepen
async def test_address_not_found(hass): ...     # [] → errors == {"base": "address_not_found"}
async def test_cannot_connect(hass): ...        # SpaarnelandenConnectionError → errors == {"base": "cannot_connect"}
async def test_response_error_cannot_connect(hass): ...  # SpaarnelandenResponseError → idem
async def test_duplicate_aborts(hass): ...      # bestaande MockConfigEntry unique_id bag_id → ABORT "already_configured"
```

Ook de translations-test: `test_translations_match_strings` — `nl.json` en `en.json` hebben exact dezelfde sleutelstructuur als `strings.json`.

- [ ] **Step 2:** `uv run pytest tests/test_config_flow.py -v` → FAIL.
- [ ] **Step 3:** Implementeer. Schema stap `user`: `vol.Required(CONF_POSTCODE): str`, `vol.Required(CONF_HOUSE_NUMBER): vol.All(vol.Coerce(int), vol.Range(min=1))`. Dropdown via `SelectSelector` met opties gesorteerd op label. Teksten (NL): titel "Adres", velden "Postcode"/"Huisnummer", `address_not_found` "Geen adres gevonden. Deze integratie werkt alleen voor adressen in Haarlem en Zandvoort.", `cannot_connect` "Kan geen verbinding maken met Spaarnelanden.", `invalid_postcode` "Ongeldige postcode (gebruik 1234AB).", abort "Dit adres is al toegevoegd.", stap 2 "Kies je adres". Entity-namen NL: Vandaag, Morgen, Meldingen, Afvalkalender, Feestdagen en sluitingen; EN: Today, Tomorrow, Notices, Waste calendar, Holidays and closures.
- [ ] **Step 4:** `uv run pytest tests/ -v` → PASS.
- [ ] **Step 5: Commit** — `feat: config flow met adreskeuze en NL/EN-vertalingen`.

### Task 6: Setup, basis-entity en sensoren

**Files:**
- Modify: `custom_components/spaarnelanden/__init__.py`
- Create: `custom_components/spaarnelanden/entity.py`, `custom_components/spaarnelanden/sensor.py`, `tests/test_init.py`, `tests/test_sensor.py`, `tests/helpers.py` (fabriek die `SpaarnelandenData` uit fixtures bouwt + `setup_integration(hass, data)` die `SpaarnelandenClient` patcht)

**Interfaces:**
- Consumes: coordinator (Task 4), translation keys (Task 5), `ICON_MAP`, `DEFAULT_ICON`.
- Produces: `async_setup_entry`/`async_unload_entry` (`entry.runtime_data = coordinator`); `SpaarnelandenEntity(CoordinatorEntity[SpaarnelandenCoordinator])` met `_attr_has_entity_name = True`, `DeviceInfo` volgens spec §3.4, en in `async_added_to_hass` een `async_track_time_change(hass, self._handle_midnight, hour=0, minute=0, second=1)` geregistreerd via `self.async_on_remove`. Hulpfunctie `today() -> date` in `entity.py` (= `dt_util.now().date()`), hergebruikt door Task 7.

- [ ] **Step 1: Failing tests `test_init.py`:** `test_setup_and_unload` (state `LOADED` → unload → `NOT_LOADED`); `test_setup_retry_on_error` (get_streams raises `SpaarnelandenConnectionError` → `ConfigEntryState.SETUP_RETRY`).
- [ ] **Step 2: Failing tests `test_sensor.py`** (`freezer.move_to("2026-10-26 10:00:00+01:00")`, tz `Europe/Amsterdam`):

```python
async def test_waste_sensor_next_date(hass):
    s = hass.states.get("sensor.spaarnelanden_teststraat_1_haarlem_gft_en_etensresten")
    assert s.state == "2026-10-27" and s.attributes["dagen_tot"] == 1
    assert s.attributes["afvalstroom_id"] == 48 and s.attributes["icon"] == "mdi:leaf"
async def test_only_streams_with_pickups(hass): ...   # geen sensor voor id 39
async def test_tomorrow_and_today(hass): ...          # morgen == "Gft en etensresten"; vandaag == "Geen", attr afvalsoorten == []
async def test_two_types_joined(hass, freezer): ...   # op 2026-10-28: morgen == "Plastic, blik, drinkpakken & papier (duobak), Restafval"
async def test_notices_sensor(hass): ...              # state "1", attr meldingen == [{"titel": "Let op", "tekst": "Ophaling & meer"}]
async def test_midnight_rollover(hass, freezer): ...  # move_to 2026-10-27 00:00:02 lokaal + async_fire_time_changed → GFT dagen_tot == 0, vandaag == "Gft en etensresten"; client niet opnieuw aangeroepen
async def test_today_uses_local_timezone(hass, freezer): ...  # move_to "2026-10-26T23:30:00+00:00" (= 27 okt 00:30 lokaal) → GFT dagen_tot == 0
async def test_next_date_from_next_year(hass, freezer): ...   # move_to 2026-12-31 → restafval == "2027-01-07"
async def test_unknown_stream_id_fallback(hass): ...  # pickup met stream_id 99 zonder stream → sensor naam eindigt op "afvalstroom_99", icoon DEFAULT_ICON
async def test_no_future_date_unknown(hass, freezer): ...     # na laatste datum → state "unknown"
```

Vastgelegd: "Vandaag"/"Morgen" sorteren titels alfabetisch en scheiden met `", "`; het attribuut `afvalsoorten` heeft dezelfde volgorde.

- [ ] **Step 3:** `uv run pytest tests/test_init.py tests/test_sensor.py -v` → FAIL.
- [ ] **Step 4:** Implementeer `__init__.py`, `entity.py`, `sensor.py` (klassen `WasteTypeSensor`, `DaySensor(offset: int, translation_key)`, `NoticesSensor`). Sensoren met waarden via `native_value` en `extra_state_attributes`, berekend bij elke state-write (geen cache).
- [ ] **Step 5:** `uv run pytest tests/ -v` → PASS.
- [ ] **Step 6: Commit** — `feat: setup en sensoren (afvalsoort, vandaag, morgen, meldingen)`.

### Task 7: Kalenders

**Files:**
- Create: `custom_components/spaarnelanden/calendar.py`, `tests/test_calendar.py`
- Modify: `custom_components/spaarnelanden/const.py` (`PLATFORMS` bevat al CALENDAR; alleen bevestigen)

**Interfaces:**
- Consumes: `SpaarnelandenEntity`, `today()`, `SpaarnelandenData`.
- Produces: `WasteCalendar` (`translation_key "waste"`, unique_id `{bag_id}_calendar`) en `HolidayCalendar` (`"holidays"`, `{bag_id}_holidays`), beide met `event` property en `async_get_events(hass, start_date: datetime, end_date: datetime) -> list[CalendarEvent]`; events hele dag (`start=date`, `end=date+1 dag`).

- [ ] **Step 1: Failing tests** (`freezer.move_to("2026-10-26 10:00:00+01:00")`):

```python
async def test_waste_calendar_state(hass):
    s = hass.states.get("calendar.spaarnelanden_teststraat_1_haarlem_afvalkalender")
    assert s.attributes["message"] == "Gft en etensresten" and s.attributes["start_time"].startswith("2026-10-27")
async def test_get_events_window(hass): ...   # calendar.get_events service, 2026-10-29 t/m 2026-10-30 → 2 events (restafval, duobak)
async def test_holiday_calendar(hass): ...    # message == "1e kerstdag; Milieuplein gesloten"
async def test_holidays_not_in_waste_calendar(hass): ...  # get_events 2026-12-25 op afvalkalender → geen feestdag-event
```

- [ ] **Step 2:** `uv run pytest tests/test_calendar.py -v` → FAIL.
- [ ] **Step 3:** Implementeer `calendar.py`. `event` = eerste event met `start >= today()`.
- [ ] **Step 4:** `uv run pytest tests/ -v` → PASS.
- [ ] **Step 5: Commit** — `feat: afvalkalender en feestdagenkalender`.

### Task 8: README, CI, licentie en validatie

**Files:**
- Create: `README.md` (NL met korte EN-sectie), `LICENSE`, `.github/workflows/validate.yml`, `.github/workflows/tests.yml`, `docs/testchecklist.md`

- [ ] **Step 1: Vraag de gebruiker** welke licentie (voorstel MIT) en welke GitHub-gebruikersnaam in `codeowners`/URLs komt; wacht op antwoord. Pas `manifest.json` aan.
- [ ] **Step 2:** `validate.yml`: jobs `hassfest` (`home-assistant/actions/hassfest@master`) en `hacs` (`hacs/action@main` met `category: integration`), triggers push/pull_request/schedule. `tests.yml`: `astral-sh/setup-uv`, `uv sync`, `uv run pytest`.
- [ ] **Step 3:** README: wat het doet, ondersteunde gemeenten (Haarlem, Zandvoort), installatie via HACS → Custom repositories → categorie Integration, configuratie (postcode + huisnummer), entity-overzicht, automatiseringsvoorbeeld ("om 20:00 als `sensor.…_morgen` ≠ Geen → melding"), databron-disclaimer (onofficieel, geen relatie met Spaarnelanden).
- [ ] **Step 4:** Lokale validatie: `uv run pytest -v` → alles PASS; `uv run python -m script.hassfest` is niet beschikbaar buiten core → in plaats daarvan controleer manifest-sleutels/volgorde en `hacs.json` handmatig tegen de HACS-documentatie (opzoeken, niet aannemen) en log het resultaat.
- [ ] **Step 5:** `docs/testchecklist.md`: handmatige stappen voor HA (toevoegen via UI, foutpaden, entities zichtbaar, kalender in HA-kalenderpaneel, NL/EN-taal, herladen, verwijderen).
- [ ] **Step 6: Commit** — `docs: README, CI-workflows, licentie en testchecklist`.

### Task 9: Live verificatie

**Files:**
- Create: `scripts/live_check.py` (in repo, zonder adres; adres via argumenten), uitvoer naar `scratch/` (genegeerd door git)

- [ ] **Step 1:** `scripts/live_check.py POSTCODE HUISNUMMER` gebruikt `SpaarnelandenClient` met een eigen `aiohttp.ClientSession` en print adressen, soorten met eerstvolgende datum, aantal pickups 2026/2027, feestdagen, meldingen.
- [ ] **Step 2:** Vraag de gebruiker om een adres (eigen of ander) en draai het script. Vergelijk de uitkomst met `afvalwijzer.spaarnelanden.nl` in de browser. Log in LOGBOEK zonder het adres.
- [ ] **Step 3:** Vraag de gebruiker hoe te testen in echte HA (eigen installatie via kopie naar `config/custom_components`, of tijdelijke lokale HA via `uv run hass -c scratch/ha-config`); voer de gekozen weg uit en loop `docs/testchecklist.md` door.
- [ ] **Step 4:** Gevonden fouten → `superpowers:systematic-debugging`, met regressietest.
- [ ] **Step 5: Audit vóór afronding** — `git grep` op echte postcodes/bagIds/e-mail; controleer dat de eerste commit (die echte voorbeeldadressen bevatte) vóór een eventuele push wordt opgeschoond, en meld dat aan de gebruiker. Niet pushen.
- [ ] **Step 6: Commit** — `chore: live-checkscript en verificatieresultaten`.
