# Changelog

Alle noemenswaardige wijzigingen per versie. Nieuwste bovenaan.
Versienummers volgen [Semantic Versioning](https://semver.org/lang/nl/): het middelste cijfer gaat omhoog bij nieuwe functies, het laatste bij kleine aanpassingen en fixes.

Updaten in Portainer: open de stack → **Pull and redeploy**. De database wordt bij het opstarten automatisch bijgewerkt en je gegevens blijven bewaard.

## [0.8.0] - 2026-09-24

### Toegevoegd
- In *Instellingen* staat een blok **Gegevens verwijderen** met twee keuzes:
  - **Alle transacties verwijderen**: categorieën, regels en eigen rekeningen blijven staan, handig om opnieuw te importeren.
  - **Alles verwijderen**: transacties, eigen categorieën, eigen regels en eigen rekeningen. De app gaat terug naar de begintoestand, met de standaardcategorieën en -regels.
- Verwijderen moet je bevestigen met je wachtwoord. Daarna wordt het databasebestand opgeschoond, zodat verwijderde gegevens er ook echt uit zijn.
- Je login blijft in beide gevallen bewaard, zodat de app niet terugvalt op admin/admin.

### Gewijzigd
- De oude knop *Alle transacties wissen…* onderaan het tabblad *Regels* is vervangen door het blok in *Instellingen*.

## [0.7.0] - 2026-09-24

### Toegevoegd
- Deze changelog, met terugwerkend alle eerdere wijzigingen.
- Elke versie krijgt een Git-tag. GitHub Actions publiceert dan een Docker-image met dat versienummer (bijv. `ghcr.io/richrdj/huishoudboekje:0.7.0`) en maakt automatisch een GitHub Release met de tekst uit deze changelog.
- Het versienummer staat onderaan in het tabblad *Instellingen* en in `/health`.

## [0.6.0] - 2026-09-24

### Gewijzigd
- De standaardcategorieën zijn een stuk compacter:
  - *Uitgaven*: Boodschappen, Thuisbezorgd en afhaal, Uit eten en horeca, Abonnementen en streaming, Hypotheek, Energie, Water, Verzekeringen, Vervoer, Online winkelen, Kinderen, Overige uitgaven
  - *Inkomsten*: Salaris, Inleg partners, Overige inkomsten
  - *Overboeking*: Sparen
- Energie en water zijn gesplitst. Telefoon en internet vallen onder *Abonnementen en streaming*. *Wonen* heet nu *Hypotheek*.
- Pinbetalingen in het buitenland gaan niet meer automatisch naar *Vakantie*.

### Migratie
- Een bestaande database wordt bij het opstarten automatisch omgezet. Oude categorieën gaan naar de nieuwe; kleding, drogist, vakantie en dergelijke naar *Overige uitgaven*. Transacties en eigen regels verhuizen mee, en zelf aangemaakte categorieën blijven staan.

## [0.5.0] - 2026-09-24

### Gewijzigd
- Bij een jaar of *Alles* toont het dashboard bedragen **per maand** als hoofdgetal (KPI's, categorieën, inkomsten). Het totaal staat eronder.
- Maandgemiddelden rekenen alleen met volledige maanden; de lopende maand telt niet mee.
- Het dashboard opent standaard op de **laatste volledige maand**. De lopende maand is gemarkeerd met *(lopend)*.

## [0.4.0] - 2026-09-24

### Toegevoegd
- Nieuwe keuze bij het wijzigen van een categorie: **alleen transacties van deze partij met hetzelfde bedrag**, handig voor een vaste overboeking of een abonnement. Werkt met terugwerkende kracht en voor toekomstige uploads.
- Regels kunnen een exact bedrag hebben (ook zelf in te stellen bij *Regels*). Een regel met bedrag gaat voor op een algemene regel.

### Opgelost
- Regels vanuit het keuzevenster zoeken alleen nog in naam en rekeningnummer, niet in de mededelingen. Voorheen ging een overboeking met de winkelnaam in de omschrijving onterecht mee.

## [0.3.0] - 2026-09-24

### Gewijzigd
- Bij het wijzigen van een categorie verschijnt een keuzevenster in de app in plaats van een browserpop-up: *alle transacties van deze partij* of *alleen deze*.
- De app stelt een zoektekst voor die alle filialen van een winkel dekt: de winkelnaam zonder filiaalnummer en plaats. Die kun je aanpassen, en je ziet direct hoeveel transacties meegaan.
- *Alle transacties* verplaatst ook eerder handmatig ingedeelde transacties, en de keuze wordt als regel onthouden.

## [0.2.1] - 2026-09-24

### Gewijzigd
- De standaardpoort op de server is nu **9393** (`http://<server>:9393`).

## [0.2.0] - 2026-09-24

### Toegevoegd
- Inlogpagina met standaardlogin **admin / admin**, die bij de eerste keer inloggen gewijzigd moet worden.
- Tabblad **Instellingen**: eigen rekeningen aanvinken (de app stelt ze voor) en gebruikersnaam en wachtwoord wijzigen.
- Tabblad **Categorieën**: aanmaken, hernoemen, soort wijzigen en verwijderen (met keuze waar de transacties heen gaan).
- Meerdere transacties tegelijk selecteren en in één keer verplaatsen.

### Gewijzigd
- In Portainer hoeft niets meer ingevuld te worden: de environment variables `PARTNER_IBANS`, `APP_USER` en `APP_PASSWORD` zijn vervangen door instellingen in de app.

## [0.1.0] - 2026-09-24

### Toegevoegd
- Eerste versie: een Flask- en SQLite-app in Docker die ING CSV-exports inleest.
- Automatische categorisatie met ruim 500 regels voor Nederlandse winkels en diensten. Retouren verlagen de uitgaven in die categorie, en spaaroverboekingen tellen niet mee.
- Dashboard met KPI's, een maandgrafiek, uitgaven per categorie met drill-down en de grootste ontvangers.
- Automatische herkenning van vaste lasten.
- Regels beheren, en de categorie per transactie aanpassen.
- Compose-bestanden voor Portainer en een GitHub Actions-workflow die de image naar ghcr.io publiceert.

[0.8.0]: https://github.com/RichrdJ/huishoudboekje/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/RichrdJ/huishoudboekje/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/RichrdJ/huishoudboekje/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/RichrdJ/huishoudboekje/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/RichrdJ/huishoudboekje/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/RichrdJ/huishoudboekje/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/RichrdJ/huishoudboekje/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/RichrdJ/huishoudboekje/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/RichrdJ/huishoudboekje/releases/tag/v0.1.0
