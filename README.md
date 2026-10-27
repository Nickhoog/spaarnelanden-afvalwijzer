<p align="center">
  <img src="https://raw.githubusercontent.com/Nickhoog/spaarnelanden-afvalwijzer/master/custom_components/spaarnelanden/brand/icon@2x.png" alt="" width="112">
</p>

<h1 align="center">Spaarnelanden - Afvalwijzer</h1>

<p align="center">
  De afvalkalender van Spaarnelanden in Home Assistant.<br>
  Wanneer gaat welke container aan de straat? Nooit meer vergeten.
</p>

<p align="center">
  <a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Default-41BDF5?style=flat-square" alt="HACS Default"></a>
  <a href="https://github.com/Nickhoog/spaarnelanden-afvalwijzer/releases"><img src="https://img.shields.io/github/v/release/Nickhoog/spaarnelanden-afvalwijzer?style=flat-square&label=versie&color=2e8b57" alt="Versie"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2026.10%2B-18BCF2?style=flat-square&logo=homeassistant&logoColor=white" alt="Home Assistant 2026.10+">
  <img src="https://img.shields.io/badge/regio-Haarlem%20%C2%B7%20Zandvoort-2e8b57?style=flat-square" alt="Haarlem en Zandvoort">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Nickhoog/spaarnelanden-afvalwijzer?style=flat-square&color=lightgrey" alt="MIT"></a>
</p>

---

## ✨ Wat krijg je?

- 🗑️ **Per afvalsoort de volgende ophaaldatum**: restafval, GFT, duobak, recyclewagen; met het aantal dagen tot ophalen.
- 📅 **Afvalkalender** met alle ophaaldagen van dit én volgend jaar, gewoon in de kalender van Home Assistant.
- ⏰ **Vandaag & Morgen**: zie in één oogopslag of er iets aan de straat moet. Ideaal voor een herinnering.
- 🎄 **Feestdagen en sluitingen**: wanneer het Milieuplein dicht is, als aparte kalender.
- 📢 **Meldingen** van Spaarnelanden, zoals storingen of gewijzigde ophaaldagen.
- 🇳🇱 Volledig in het **Nederlands** (en Engels), instellen via de UI met alleen je postcode en huisnummer.

> [!NOTE]
> **Onofficieel.** Deze integratie is niet gemaakt door of verbonden aan Spaarnelanden.
> Ze gebruikt dezelfde openbare gegevens als [afvalwijzer.spaarnelanden.nl](https://afvalwijzer.spaarnelanden.nl).

## 📦 Installatie

[![Open je Home Assistant en toon deze integratie in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Nickhoog&repository=spaarnelanden-afvalwijzer&category=integration)

1. Open **HACS** in Home Assistant en zoek **Spaarnelanden - Afvalwijzer**, of klik op de knop hierboven.
2. Klik **Download** en **herstart** Home Assistant.
3. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen** en kies **Spaarnelanden - Afvalwijzer**.

Vereist Home Assistant **2026.10** of nieuwer.

<details>
<summary><b>Alternatief: als custom repository toevoegen</b></summary>

Vind je de integratie niet in HACS?

1. HACS → menu (⋮) → **Custom repositories**.
2. Repository: `https://github.com/Nickhoog/spaarnelanden-afvalwijzer`, type **Integration** → **Add**.
3. Ga verder bij stap 1 hierboven.

</details>

<details>
<summary><b>Handmatig installeren (zonder HACS)</b></summary>

Kopieer de map `custom_components/spaarnelanden` naar `config/custom_components/` van je
Home Assistant en herstart.

</details>

## ⚙️ Instellen

1. Vul je **postcode** en **huisnummer** in (spaties en kleine letters mogen, `2011 vb` werkt ook).
2. Hebben meerdere adressen hetzelfde huisnummer (bijv. 1A, 1B, 1 RD)? Dan kies je daarna je adres uit een lijst.
3. Klaar. Meer adressen? Voeg de integratie gewoon nog een keer toe.

**Werkt voor** alle adressen waar Spaarnelanden het afval ophaalt: **Haarlem** en **Zandvoort**.

## 🧩 Entities

Per adres komt er één apparaat **Spaarnelanden ‹adres›** met:

| Entity | Waarde | Extra informatie |
|---|---|---|
| 🗑️ **Sensor per afvalsoort** | datum van de volgende ophaling | `dagen_tot`, `afvalsoort`, `afvalstroom_id` |
| ⏰ **Vandaag** | wat er vandaag wordt opgehaald, of `Geen` | `afvalsoorten` (lijst) |
| ⏰ **Morgen** | wat er morgen wordt opgehaald, of `Geen` | `afvalsoorten` (lijst) |
| 📢 **Meldingen** | aantal actuele meldingen | `meldingen` (titel en tekst) |
| 📅 **Afvalkalender** | alle ophaaldagen, dit en volgend jaar | |
| 🎄 **Feestdagen en sluitingen** | feestdagen en sluitingsdagen | |

Je krijgt alleen sensoren voor afvalsoorten die op jouw adres echt worden opgehaald.
De gegevens worden elke 12 uur ververst, en na middernacht schuiven *Vandaag*, *Morgen* en
`dagen_tot` vanzelf door.

## 💡 Voorbeelden

Vervang `teststraat_1_haarlem` hieronder door jouw adres; de exacte entity-id's vind je onder het apparaat.

### Herinnering de avond ervoor

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
          title: "🗑️ Afval buiten zetten"
          message: "Morgen wordt opgehaald: {{ states('sensor.spaarnelanden_teststraat_1_haarlem_morgen') }}"
```

### Dashboardkaart

Een simpele kaart die de komende ophalingen op volgorde toont:

```yaml
type: markdown
title: Afval
content: |
  {%- set ns = namespace(rows=[]) %}
  {%- for s in states.sensor
       if s.entity_id.startswith('sensor.spaarnelanden_teststraat_1_haarlem_')
       and s.attributes.dagen_tot is defined and s.attributes.dagen_tot is not none %}
    {%- set ns.rows = ns.rows + [s] %}
  {%- endfor %}
  {%- for s in ns.rows | sort(attribute='attributes.afvalsoort') | sort(attribute='attributes.dagen_tot') %}
  {%- set d = s.attributes.dagen_tot %}
  - **{{ s.attributes.afvalsoort }}**: {{ 'vandaag' if d == 0 else 'morgen' if d == 1 else 'over ' ~ d ~ ' dagen' }}
  {%- endfor %}
```

## ❓ Veelgestelde vragen

<details>
<summary><b>Mijn adres wordt niet gevonden</b></summary>

Controleer of Spaarnelanden op jouw adres het afval ophaalt (Haarlem of Zandvoort) en of
het adres op [afvalwijzer.spaarnelanden.nl](https://afvalwijzer.spaarnelanden.nl) wel werkt.
Gebruik je postcode zonder huisletter; de letter of toevoeging kies je in de volgende stap.

</details>

<details>
<summary><b>Ik zie geen sensor voor papier of glas</b></summary>

Er komen alleen sensoren voor afvalsoorten die bij jouw adres worden opgehaald. Brengvoorzieningen
zoals ondergrondse containers en glasbakken hebben geen ophaaldag.

</details>

<details>
<summary><b>Wat gebeurt er als de website van Spaarnelanden even niet bereikbaar is?</b></summary>

De sensoren en kalenders blijven de laatst opgehaalde gegevens tonen; bij de volgende
verversing wordt het automatisch bijgewerkt.

</details>

## 🇬🇧 English

Unofficial Home Assistant integration for the waste collection calendar of **Spaarnelanden**
(Haarlem and Zandvoort, the Netherlands). Install it from **HACS** by searching for
*Spaarnelanden - Afvalwijzer* (or, as a fallback, add this repository as a custom repository
of type *Integration*), then add the integration and enter your postal code and house number.
It provides a date sensor per waste type, *Today*/*Tomorrow* sensors, a notices sensor,
a waste calendar and a holidays calendar. UI translations: Dutch and English.

## 🐞 Fout of idee?

[Open een issue](https://github.com/Nickhoog/spaarnelanden-afvalwijzer/issues) op GitHub.

## 📄 Licentie

[MIT](LICENSE)
