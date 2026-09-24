# Huishoudboekje – werkafspraken

- Taal van de app, teksten, commits en changelog: Nederlands.
- **Bij elke wijziging:**
  1. voeg een entry toe aan `CHANGELOG.md` (secties *Toegevoegd*, *Gewijzigd*, *Opgelost*, *Migratie*) met de vergelijkingslink onderaan;
  2. verhoog `app/VERSION` (semver: minor voor functies, patch voor kleine aanpassingen en fixes);
  3. commit met een beschrijvende boodschap;
  4. tag `vX.Y.Z` (annotated) en push commits én tags. GitHub Actions bouwt dan de image `ghcr.io/richrdj/huishoudboekje:X.Y.Z` en maakt de release aan.
- **Geen persoonlijke gegevens in de repo** (die is openbaar): niets uit de eigen bankexport in changelog, README, commits, codecommentaar of standaardregels. Geen bedrijfsnamen, bedragen, plaatsen, maanden of namen daaruit; gebruik verzonnen voorbeelden. Standaardregels bevatten alleen landelijke ketens en diensten.
- Nooit echte bankexports of databases committen (`*.csv` en `*.db` staan in `.gitignore`; `voorbeeld_ing_export.csv` bevat alleen fictieve data).
- Schemawijzigingen: migratie in `init_db()` (idempotent). Wijzigingen in standaardregels of -categorieën: verhoog `RULES_VERSION`.
- Lokaal draaien: `DATA_DIR=./data python app/app.py` (poort 8080; in Docker gemapt op 9393).
