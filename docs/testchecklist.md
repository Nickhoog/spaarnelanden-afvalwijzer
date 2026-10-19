# Testchecklist in je eigen Home Assistant

Installeer eerst: kopieer `custom_components/spaarnelanden` naar `config/custom_components/`
(of via HACS custom repository zodra de repo bestaat) en herstart HA.

## Toevoegen

- [ ] Instellingen → Apparaten & diensten → Integratie toevoegen → "Spaarnelanden" is vindbaar, met groen container-icoon.
- [ ] Postcode met spatie en kleine letters (bijv. `2011 vb`) wordt geaccepteerd.
- [ ] Postcode `12345` → melding "Ongeldige postcode (gebruik 1234AB)."
- [ ] Postcode buiten het gebied (bijv. `1012AB` 1) → "Geen adres gevonden…".
- [ ] Huisnummer met meerdere adressen → keuzelijst, gesorteerd.
- [ ] Eigen adres → integratie aangemaakt, titel = je adres.
- [ ] Zelfde adres nog eens toevoegen → "Dit adres is al toegevoegd."

## Entities

- [ ] Apparaat "Spaarnelanden ‹adres›" bestaat.
- [ ] Sensor per afvalsoort; datums kloppen met afvalwijzer.spaarnelanden.nl.
- [ ] Attribuut `dagen_tot` klopt.
- [ ] "Vandaag" en "Morgen" tonen de juiste soorten of "Geen".
- [ ] "Meldingen" toont een aantal (meestal 0).
- [ ] Kalenderpaneel: "Afvalkalender" toont ophaaldata als hele-dag-items, ook in januari volgend jaar.
- [ ] Kalenderpaneel: "Feestdagen en sluitingen" toont feestdagen.

## Taal en levenscyclus

- [ ] Profiel op Engels → entity-namen Today/Tomorrow/Notices/Waste calendar/Holidays and closures (bij nieuw aangemaakte entities).
- [ ] Integratie herladen werkt zonder fouten in het logboek.
- [ ] Na middernacht schuiven "Vandaag"/"Morgen" en `dagen_tot` door (volgende dag controleren).
- [ ] Integratie verwijderen ruimt apparaat en entities op.
- [ ] Instellingen → Systeem → Logboeken: geen fouten van `custom_components.spaarnelanden`.
