# The Baby's Corner — In-store AI-assistent

Web-applicatie voor de winkel: een klant doorloopt op een tablet een korte
vragenlijst en krijgt daarna een persoonlijk kinderwagenadvies. De klant kan
favorieten aanduiden en de sessie doorgeven aan een medewerker, die het advies
en de antwoorden opzoekt via een sessiecode.

- [Wat de app doet](#wat-de-app-doet)
- [Techniek](#techniek)
- [Structuur van de repo](#structuur-van-de-repo)
- [Lokaal draaien](#lokaal-draaien)
- [Draaien met Docker](#draaien-met-docker)
- [Configuratie](#configuratie)
- [Beheer: medewerker en admin](#beheer-medewerker-en-admin)
- [Teksten en vragen aanpassen](#teksten-en-vragen-aanpassen)
- [Productcatalogus bijwerken](#productcatalogus-bijwerken)
- [Tests](#tests)
- [Eigendom](#eigendom)

## Wat de app doet

De klantflow bestaat uit 9 stappen (`frontend/src/config/flowSteps.ts`):

| Stap | Pagina | Inhoud |
|---|---|---|
| 1–2 | `/quiz/1` … `/quiz/2` | Twee profielvragen. Hieruit volgt een profiel (A minimalist, B ontdekker, C planner). |
| 3 | `/categories` | Overzicht van de acht productcategorieën. |
| 4 | `/category/:id` | Intro van de gekozen categorie. |
| 5–8 | `/quiz/5` … `/quiz/8` | Vier tagvragen (wensen zoals compact, lichtgewicht, twee kinderen). |
| 9 | `/quiz/9` | Vrije notitie, optioneel over te slaan. |
| — | `/recommendations` | Aanbevelingen, gerangschikt van exacte match naar ruimere match. |
| — | `/shortlist` | Favorieten van de klant. |
| — | `/complete` | Afronding met sessiecode. |
| — | `/handoff` | Doorgeven aan een medewerker (naam, e-mail). |

Alleen de categorie **Kinderwagens & buggy's** geeft echt advies. De zeven
andere categorieën staan op status `soon` en zijn zichtbaar maar nog niet actief
(`backend/content/categories.json`).

Verder:

- **Sessiecode**: 6 tekens uit `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (geen 0/O/1/I/L,
  om verwarring bij het voorlezen te vermijden).
- **Favorieten** blijven bewaard, ook wanneer de klant de flow opnieuw start.
- **Inactiviteit**: na 10 minuten zonder activiteit volgt een waarschuwing en
  daarna een reset, zodat de tablet klaarstaat voor de volgende klant.
- **E-mail**: bij het doorgeven aan een medewerker gaat er een mail naar
  `STAFF_EMAIL`. Zonder SMTP-instellingen slaat de app dit over.

## Techniek

| Onderdeel | Keuze |
|---|---|
| Backend | Python 3.12, FastAPI, SQLite (`aiosqlite`), pakketbeheer met `uv` |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Zustand, React Router, Framer Motion |
| LLM | Azure OpenAI met twee deployments, OpenRouter als terugvaloptie |
| Serveren | nginx (statische build + proxy naar `/api`), Caddy voor HTTPS in productie |
| E-mail | SMTP via `aiosmtplib` |

Het LLM rangschikt de aanbevelingen en herschrijft productbeschrijvingen. Per
taak probeert de app de twee Azure-deployments na elkaar en daarna OpenRouter;
welke deployment eerst komt, hangt af van de taak (zie
`backend/app/services/llm.py`). Valt het LLM weg of is er geen sleutel
ingesteld, dan gebruikt de app een vaste, deterministische volgorde. De app
blijft dus werken zonder LLM.

De namen `NANO` en `MINI` verwijzen naar deployments in Azure. Die namen zijn
vrij te kiezen en hoeven niet overeen te komen met het onderliggende model.

## Structuur van de repo

```
backend/
  app/
    main.py            FastAPI-app, CORS, startup-checks
    config.py          alle instellingen uit .env
    database.py        SQLite-schema en verbinding
    content.py         inlezen van vragen en categorieën
    routers/           API-endpoints (session, staff, admin, filters, auth)
    services/          catalogus, aanbevelingen, LLM, e-mail, export, rate limiting
  catalog/
    catalog.json       de productcatalogus die de app gebruikt
    generate_catalog.py  bouwt catalog.json uit ai_tool_feed.csv
    feed_diff.py       toont vooraf wat een nieuwe feed zou wijzigen
    format_descriptions.py  LLM-herschrijving van beschrijvingen
  content/             quiz_questions.json, tag_questions.json, categories.json
  tests/               223 tests (unit en integratie)
frontend/
  src/pages/           één bestand per pagina uit de flow
  src/components/      productkaarten, modals, header, inactiviteitswaarschuwing
  src/store/           sessionStore.ts, de client-side sessiestatus
  src/api/client.ts    alle API-aanroepen
deploy/Caddyfile       HTTPS-configuratie voor productie
docs/                  runbook en achtergrond bij de productfeed
ai_tool_feed.csv       de ruwe productfeed uit de webshop
```

## Lokaal draaien

Nodig: Python 3.12 met [uv](https://docs.astral.sh/uv/), Node 20 of nieuwer, en
een `.env` in de hoofdmap (kopieer `.env.example` en vul aan).

**Backend** (poort 8000):

```bash
cd backend
uv sync
DATABASE_PATH=data/sessions.db uv run --env-file ../.env uvicorn app.main:app --reload --port 8000
```

`DATABASE_PATH` staat in `.env` op het containerpad `/app/data/sessions.db`, dat
lokaal niet bestaat. De variabele vooraan de regel overschrijft de waarde uit het
bestand, zodat de database in `backend/data/` terechtkomt.

**Frontend** (poort 5173):

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite stuurt `/api` door naar `http://localhost:8000`
(`frontend/vite.config.ts`), dus beide processen moeten draaien.

## Draaien met Docker

**Zonder HTTPS**, voor lokaal gebruik en voor de VM zonder Caddy:

```bash
docker compose up --build
```

De frontend is dan bereikbaar op twee poorten die naar dezelfde container
verwijzen:

| Poort | Gebruik |
|---|---|
| 8019 | lokale deployment |
| 3000 | de VM |

Beide mappings staan in `docker-compose.yml`; ze zijn er allebei met opzet, zodat
lokaal en de VM hun eigen poort houden. De backend zit achter nginx en is niet
rechtstreeks van buiten bereikbaar. De SQLite-database staat in het Docker-volume
`sqlite_data` en blijft dus bewaard tussen herstarts.

**Productie**, met Caddy voor HTTPS en automatische certificaten:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Zet vooraf in `.env`:

```
APP_ENV=production
SESSION_SECRET_KEY=<minstens 32 willekeurige tekens>
STAFF_ADMIN_PASSWORD=<sterk wachtwoord>
PXL_ADMIN_PASSWORD=<sterk wachtwoord>
SESSION_COOKIE_SECURE=true
PUBLIC_DOMAIN=<domeinnaam>
CORS_ORIGINS=https://<domeinnaam>
```

Het domein moet met een A-record naar de server wijzen en poort 80 en 443 moeten
open staan; Caddy vraagt zelf het certificaat aan.

Let op: deze overlay haalt de poorten 3000 en 8019 weg (`ports: !reset []` in
`docker-compose.prod.yml`). Al het verkeer loopt dan via Caddy op 80 en 443. Wie
de app op poort 3000 wil blijven bereiken, draait dus de gewone
`docker compose up` zonder deze overlay — en dan is er geen HTTPS.

Genereer een sleutel met:

```bash
openssl rand -base64 48
```

## Configuratie

Alles staat in `.env` in de hoofdmap. `.env.example` bevat alle sleutels met
uitleg. `.env` zelf staat in `.gitignore` en hoort niet in versiebeheer.

| Variabele | Nodig | Uitleg |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | voor LLM | Endpoint van de Azure OpenAI-resource. |
| `AZURE_OPENAI_API_KEY` | voor LLM | Sleutel van diezelfde resource. |
| `AZURE_OPENAI_DEPLOYMENT_NANO` | voor LLM | Naam van de eerste deployment in Azure. |
| `AZURE_OPENAI_DEPLOYMENT_MINI` | voor LLM | Naam van de tweede deployment in Azure. |
| `OPENROUTER_API_KEY` | optioneel | Terugvaloptie wanneer Azure niet antwoordt. |
| `OPENROUTER_MODEL` | optioneel | Model bij OpenRouter. |
| `SMTP_HOST`, `SMTP_PORT` | voor e-mail | Mailserver, standaard Gmail op poort 587. |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | voor e-mail | Aanmelding op de mailserver. |
| `STAFF_EMAIL` | voor e-mail | Ontvanger van de sessiemail. |
| `STAFF_ADMIN_USERNAME` / `_PASSWORD` | ja | Aanmelding voor medewerkers. |
| `PXL_ADMIN_USERNAME` / `_PASSWORD` | ja | Aanmelding voor beheer, inclusief export. |
| `SESSION_SECRET_KEY` | in productie | Ondertekent de aanmeldcookie. |
| `SESSION_COOKIE_SECURE` | in productie | Op `true` zetten zodra er HTTPS is. |
| `APP_ENV` | ja | `development` of `production`. |
| `CORS_ORIGINS` | ja | Toegelaten herkomsten, met komma's gescheiden. Geen `*`. |
| `PUBLIC_DOMAIN` | in productie | Domeinnaam voor Caddy. |
| `CATALOG_PATH` | nee | Pad naar `catalog.json`. Bestaat het pad niet, dan valt de app terug op `backend/catalog/catalog.json`. |
| `DATABASE_PATH` | ja | Pad naar het SQLite-bestand. |

Staat `APP_ENV` op `production`, dan controleert de app bij het opstarten of
`SESSION_SECRET_KEY` minstens 32 tekens heeft, of beide wachtwoorden minstens 12
tekens hebben en of `SESSION_COOKIE_SECURE` op `true` staat. Klopt er iets niet,
dan start de backend niet op en staat de reden in de logs
(`backend/app/config.py`).

Zonder LLM-sleutel start de app wel, met een waarschuwing in de logs.

## Beheer: medewerker en admin

| Pad | Rol | Mogelijkheden |
|---|---|---|
| `/staff` | `staff` of `admin` | Sessie opzoeken via de sessiecode van de klant: profiel, antwoorden, favorieten en gesprekspunten. |
| `/admin` | `admin` | Alle sessies bekijken en exporteren naar Excel. |

Aanmelden gebeurt met de gebruikersnamen en wachtwoorden uit `.env`. Na aanmelden
zet de server een `auth_token`-cookie (`HttpOnly`). Na tien mislukte pogingen
binnen vijf minuten blokkeert hetzelfde IP-adres tijdelijk.

De export haalt `GET /api/admin/sessions/export` op en levert een `.xlsx` met
één regel per sessie.

## Teksten en vragen aanpassen

Alle vragen en teksten van de flow staan in JSON, zonder code:

| Bestand | Inhoud |
|---|---|
| `backend/content/quiz_questions.json` | De twee profielvragen en de tekst van de notitiestap. |
| `backend/content/tag_questions.json` | De vier tagvragen en hun antwoordopties. |
| `backend/content/categories.json` | De acht categorieën: label, status (`ai` of `soon`) en introtekst. |

De backend leest deze bestanden één keer in en houdt ze daarna in het geheugen.
**Herstart de backend na een wijziging**, anders blijft de oude tekst zichtbaar.
Dat geldt ook voor `catalog.json`.

## Productcatalogus bijwerken

De catalogus komt uit `ai_tool_feed.csv`, de productfeed van de webshop. Het
volledige stappenplan staat in **[`docs/feed-update-runbook.md`](docs/feed-update-runbook.md)**.
Kort:

```bash
# 1. Bekijk eerst wat er zou wijzigen (wijzigt niets)
python backend/catalog/feed_diff.py --new ~/Downloads/ai_tool_feed.csv

# 2. Vervang de feed en bouw de catalogus opnieuw
cp ~/Downloads/ai_tool_feed.csv ai_tool_feed.csv
python backend/catalog/generate_catalog.py

# 3. Laat het LLM alleen de nieuwe of gewijzigde producten herschrijven
cd backend && uv run --env-file ../.env python catalog/format_descriptions.py

# 4. Controleer
cd backend && uv run python -m pytest -q
```

Stap 3 kost geld en tijd, en is daarom bewust incrementeel: beschrijvingen van
onveranderde producten worden hergebruikt. De achtergrond hiervan staat in
[`docs/ai-feed-refresh-and-variant-collapse-plan.md`](docs/ai-feed-refresh-and-variant-collapse-plan.md).

## Tests

```bash
cd backend
uv run python -m pytest -q
```

223 tests, unit en integratie. Ze gebruiken elk een eigen tijdelijke database en
versturen geen echte e-mail of LLM-aanvragen.

Voor de frontend controleert de build ook de types:

```bash
cd frontend
npm run build
```

## Eigendom

Zie [`LICENSE`](LICENSE).
