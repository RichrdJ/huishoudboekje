# Huishoudboekje

Een klein, zelf-gehost huishoudboekje voor de ING-rekening. Upload elke maand de CSV-export uit de ING app. De app deelt alle transacties automatisch in categorieën in en geeft een overzicht van inkomsten, uitgaven, vaste lasten en trends.

Alles draait lokaal in één container met SQLite. Er gaan geen bankgegevens naar externe diensten. Alle instellingen doe je in de app zelf; in Portainer hoef je niets in te vullen.

## Functies

- **Upload** van ING CSV-exports (puntkomma- en kommaformaat, Nederlands en Engels). Overlappende periodes geven geen dubbele transacties.
- **Automatische categorieën**: ruim 500 herkenningsregels voor Nederlandse winkels en diensten (AH, Jumbo, Thuisbezorgd, Netflix, Vattenfall, Zilveren Kruis, bol, Coolblue…).
  - Pinbetalingen in het buitenland → *Vakantie & reizen*
  - Terugbetalingen (bijv. een retour bij bol) verlagen de uitgaven in die categorie
  - Overboekingen van en naar de spaarrekening tellen niet als inkomen of uitgave
  - Stortingen vanaf jullie privérekeningen → *Inleg partners*. Die rekeningen vink je aan in *Instellingen*; de app stelt ze zelf voor.
- **Overzicht** per maand, per jaar of over alles: KPI's, vergelijking met het gemiddelde van de 6 maanden ervoor, een maandgrafiek, uitgaven per categorie met drill-down, en de grootste ontvangers.
- **Vaste lasten** worden automatisch herkend: posten die elke maand met (bijna) hetzelfde bedrag terugkomen.
- **Zelf indelen**:
  - Pas de categorie van een transactie aan. De app vraagt dan of dat voor álle transacties van die partij moet gelden, en maakt zo nodig een regel.
  - Selecteer meerdere transacties en verplaats ze in één keer.
  - Maak categorieën aan, hernoem ze, verander hun soort (uitgave / inkomen / overboeking) of verwijder ze.
  - Beheer regels in het tabblad *Regels*.

## Installeren in Portainer

### Optie A: Web editor met kant-en-klare image (aanbevolen)

GitHub Actions bouwt bij elke push naar `main` een image: `ghcr.io/richrdj/huishoudboekje:latest` (amd64 + arm64).

1. Portainer → **Stacks** → **Add stack** → **Web editor**
2. Plak de inhoud van [`portainer-stack.yml`](portainer-stack.yml).
3. **Deploy the stack** → open `http://<server>:9393`

> Is de repository privé? Maak dan het package op GitHub openbaar (Packages → huishoudboekje → Package settings → Change visibility), of voeg `ghcr.io` toe als registry in Portainer met een GitHub-token met de scope `read:packages`.

### Optie B: Rechtstreeks vanuit Git (Portainer bouwt zelf)

1. Portainer → **Stacks** → **Add stack** → **Repository**
2. Repository URL: `https://github.com/RichrdJ/huishoudboekje`, Compose path: `docker-compose.yml`
3. Bij een privé-repo: zet *Authentication* aan en gebruik een GitHub-token.
4. Deploy. Met *GitOps updates* haalt Portainer nieuwe versies automatisch op.

### Eerste keer inloggen

Log in met **admin** / **admin**. Je moet dan direct een eigen gebruikersnaam en wachtwoord kiezen; tot die tijd is verder niets bereikbaar. Wijzigen kan later onder **Instellingen**.

Vink daarna onder **Instellingen → Eigen rekeningen** jullie privérekeningen aan, zodat stortingen als inleg tellen.

Wil je de app buiten je thuisnetwerk bereikbaar maken? Zet er dan een reverse proxy met HTTPS voor, bijvoorbeeld Nginx Proxy Manager, Traefik of Caddy.

De database staat in het volume `huishoudboekje-data` (`/data/huishoudboekje.db`). Neem dat volume mee in je back-ups.

## Maandelijkse routine

1. ING app → gezamenlijke rekening → **Af- en bijschrijvingen downloaden** → CSV
2. Sleep het bestand in de app, of gebruik **Upload export**.
3. Kijk bij de melding *"x transacties nog niet gecategoriseerd"* en deel die in. Nieuwe regels worden onthouden, dus dit wordt elke maand minder.

## Lokaal ontwikkelen

```bash
pip install -r requirements.txt
DATA_DIR=./data python app/app.py
```

Open daarna http://localhost:8080. Met [`voorbeeld_ing_export.csv`](voorbeeld_ing_export.csv) (fictieve data) kun je de app uitproberen.
