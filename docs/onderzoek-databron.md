# Onderzoek: databron Spaarnelanden (2026-10-19)

Alles hieronder is live geverifieerd met `curl` op 2026-10-19, tenzij anders vermeld.

## Conclusie

Spaarnelanden publiceert de afvalkalender via het eigen webplatform
`https://afvalwijzer.spaarnelanden.nl` (een "Opzet"-platform, dezelfde software als
o.a. Purmerend/Schouwen-Duiveland). Het platform heeft een openbare, ongeauthenticeerde
JSON REST-API (`Access-Control-Allow-Origin: *`, geen API-key). Het loopt **niet** via
Ximmio of mijnafvalwijzer.nl.

Bestaande community-integratie: `xirixiz/homeassistant-afvalwijzer` ondersteunt
Spaarnelanden via zijn `opzet`-collector (gebruikt alleen `/afvalstromen`, dus alleen de
eerstvolgende datum). Geen losse Spaarnelanden-integratie gevonden.

## Endpoints (basis `https://afvalwijzer.spaarnelanden.nl/rest`)

| Endpoint | Doel | Voorbeeld-antwoord |
|---|---|---|
| `GET /adressen/{POSTCODE}-{HUISNR}` | adres → lijst BAG-objecten | `[{"bagId":"0392…","postcode":"9999ZZ","huisnummer":1,"huisletter":"A","huisnummerToevoeging":"","openbareRuimteNaam":"…","woonplaatsNaam":"Haarlem",…}]` |
| `GET /adressen/{bagId}/afvalstromen` | alle afvalstromen + eerstvolgende datum | `[{"id":48,"title":"Gft en etensresten","menu_title":"…","icon":"gft-line","ophaaldatum":"2026-10-27" of null,…}]` (35 items) |
| `GET /adressen/{bagId}/ophaaldata` | alleen eerstvolgende datums | `[{"afvalstroom_id":48,"ophaaldatum":"2026-10-27"},…]` |
| `GET /adressen/{bagId}/kalender/{jaar}` | **volledige jaarkalender** | `[{"afvalstroom_id":48,"ophaaldatum":"2026-01-06"},…]` (~100 items, loopt door tot begin volgend jaar; 2027 is nu al beschikbaar) |
| `GET /feestdagen/{van}/{tot}` | feestdagen/sluitingen | `[{"datum":"2025-12-26","naam":"2e kerstdag; Milieuplein … gesloten"}]` |
| `GET /app/meldingen/{bagId}` | actuele meldingen | `[]` (HTML in `content`) |

Endpoints gevonden in de website-JavaScript (`/js/c-app.*.js`, functies `getOphaaldatums`
→ `/adressen/{bag}/kalender/{jaar}` en `getUpcomingOphaaldatums` → `/ophaaldata`).
`/rest/waste-calendar/dates?...` uit dezelfde JS geeft een 404-HTML-pagina → niet gebruiken.

## Invoer

- Postcode (formaat `1234AB`, zonder spatie) + huisnummer.
- Bij meerdere resultaten: kiezen op `huisletter` of `huisnummerToevoeging`
  (bijv. een adres in het centrum van Haarlem geeft `RD`, `A`, `B`, …). Onbekend adres → `[]`.

## Dekking (getest)

- Haarlem (gemeente-id 392) ✔
- Zandvoort (gemeente-id 473) ✔
- 2051 (Overveen/Bloemendaal) en 2061 (Bloemendaal): geen resultaat bij de geteste nummers.

## Afvalsoorten

Op adressen met kliko's hadden deze stromen een datum (ids zijn per adres/gemeente
dezelfde in de tests, maar er bestaan dubbele ids per soort, bijv. GFT 48 én 3):

| id | titel | icon |
|---|---|---|
| 48 | Gft en etensresten | gft-line |
| 42 | Restafval | rest2-line |
| 44 | Plastic, blik, drinkpakken & papier (duobak) | duocontainer-line |
| 56 | Recyclewagen | recyclewagen-line |

Andere stromen in de lijst (meestal zonder datum, bijv. ondergrondse containers of
brengvoorzieningen): Papier en karton (39/41), PBD (49/2), Glas (53/5), Grof
huishoudelijk afval, Textiel, KCA, Kerstboom, Milieuplein, Recycletas, Tegeltaxi, enz.

Voorbeeldadressen: een centrumadres in Haarlem heeft alleen Recyclewagen met datum;
een wijkadres in Haarlem heeft GFT, Restafval, Duobak, Recyclewagen; een adres in Zandvoort heeft GFT,
Duobak, Restafval.

**Gevolg voor ontwerp:** de lijst afvalsoorten moet dynamisch uit `/afvalstromen` komen
(titel per id), niet hardcoded. Een sensor alleen aanmaken voor stromen die in de kalender
voorkomen.

## Tooling-status (lokaal)

- Python: alleen 3.10 geïnstalleerd. Home Assistant 2025+/
  `pytest-homeassistant-custom-component` vereist Python 3.13.
- Geen `uv`, geen Docker. Git 2.49 aanwezig.
