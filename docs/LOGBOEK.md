# Logboek spaarnelanden-hacs

## 2026-10-19

- Projectmap `spaarnelanden-hacs` aangemaakt; git-repo lokaal geïnitialiseerd met
  `user.email = noreply@localhost` (geen persoonlijk e-mailadres in commits). Geen remote.
- Brainstorming gestart (pad: architecturaal → vragen, ontwerp, spec, plan, dan bouwen).
- Databron onderzocht en live geverifieerd met `curl` (alleen GET-verzoeken, geen
  wijzigingen): `afvalwijzer.spaarnelanden.nl/rest` (Opzet-platform). Resultaten in
  `docs/onderzoek-databron.md`.
- Tooling gecontroleerd: Python 3.10 (te oud voor HA-testtooling, vereist 3.13), geen uv/Docker.
- Vragen beantwoord: openbaar/HACS-waardig; v1 met kalender, vandaag/morgen, meldingen,
  feestdagen; testen via `uv` + Python 3.13; sensorstatus = datum + attribuut `dagen_tot`.
- Aanpak 1 (zelfstandige integratie met eigen API-module) gekozen; ontwerp deel 1–3
  goedgekeurd in chat.
- Spec geschreven: `docs/superpowers/specs/2026-10-19-spaarnelanden-hacs-design.md`.
- Echte voorbeeldadressen uit de documentatie verwijderd (geanonimiseerd).
- Implementatieplan geschreven: `docs/superpowers/plans/2026-10-19-spaarnelanden-hacs.md` (9 taken).
- uv geïnstalleerd (dry run `winget show astral-sh.uv` → 0.13.1; daarna `winget install --id astral-sh.uv -e`).
- `uv python install 3.14` (3.14.8) + `uv sync`: homeassistant 2026.10.2,
  pytest-homeassistant-custom-component 0.13.373. Actuele HA vereist Python ≥ 3.14.2
  (niet 3.13 zoals in de spec stond); `hacs.json` minimaal 2026.10.0.
- Windows-hindernissen bij testen: `lru-dict` 1.3.0 heeft geen Windows-wheel (override
  naar ≥1.3.1 in pyproject, alleen testomgeving); HA importeert `fcntl`/`resource`
  (Unix-only) en pytest-socket blokkeert de Windows-eventloop. Oplossing: lege stubs in
  `tests/_winstubs/`, alleen actief via `scripts/test-windows.sh` (op Linux/CI niet).
- Gebruiker test de echte integratie zelf in de eigen HA (geen aparte HA-installatie nodig).
- Task 1 (scaffold) klaar: 3 tests groen.
- Tasks 2–7 klaar (TDD, steeds eerst rode test): API-parsers, HTTP-client, coordinator,
  config flow + NL/EN, sensoren, kalenders.
- Task 8: licentie MIT (keuze gebruiker), codeowner `@Nickhoog` (GitHub-account uit `gh auth status`).
  HACS-eisen opgezocht op hacs.xyz: `render_readme` niet meer gedocumenteerd → verwijderd;
  `country: NL` toegevoegd. Brand-icoon: sinds HA 2026.3 in
  `custom_components/spaarnelanden/brand/` (icon.png 256², icon@2x.png 512²) — eigen
  neutraal container-icoon gegenereerd (niet het Spaarnelanden-logo; merkrecht).
  CI-workflows (hassfest, HACS-action, pytest) toegevoegd; draaien pas na een push.
- Task 9: `scripts/live_check.py` tegen de echte API gedraaid (alleen GET). Openbaar adres
  (stadhuis): 2 adressen, geen kliko-ophaling, 10 feestdagen, 0 meldingen. Een wijkadres
  in Haarlem (niet vastgelegd): 4 afvalsoorten, 103 ophalingen 2026 en 78 in 2027;
  eerstvolgende datums gelijk aan het eerdere curl-onderzoek.
- Eindreview (aparte reviewer, Opus): geen kritieke punten. Twee belangrijke punten opgelost
  met eerst een rode test: (1) kalendervenster tot middernacht gaf ook events van de
  volgende dag (einde nu exclusief); (2) één mislukte verversing maakte alle entities
  12 uur onbeschikbaar → entities blijven beschikbaar met laatst geladen data (spec §3.5
  bijgewerkt). Kleine punten genoteerd, niet opgelost. Suite: 70 tests groen.
- feat/v1 lokaal fast-forward gemerged naar master (keuze gebruiker); 70 tests groen op master; branch verwijderd. Niets gepusht.
- Publicatie (verzoek gebruiker: openbare repo voor HACS): audit op persoonlijke gegevens (alleen openbare GitHub-naam Nickhoog aanwezig); lokale geschiedenis samengevoegd tot één schone commit (eerste commit bevatte echte testadressen); auteur Nickhoog met GitHub-noreply-adres.
