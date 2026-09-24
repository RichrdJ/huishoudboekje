"""Standaardcategorieën en startregels voor Nederlandse huishoudens.

Een regel matcht als het patroon (hoofdletterongevoelig) voorkomt in de naam,
tegenrekening of mededelingen van een transactie. Regels die je zelf in de app
maakt krijgen voorrang op deze standaardregels.
"""

UNCATEGORIZED = "Ongecategoriseerd"

# (naam, soort) - soort: uitgave | inkomen | overboeking
CATEGORIES = [
    ("Boodschappen", "uitgave"),
    ("Thuisbezorgd & afhaal", "uitgave"),
    ("Uit eten & horeca", "uitgave"),
    ("Abonnementen & streaming", "uitgave"),
    ("Wonen", "uitgave"),
    ("Energie & water", "uitgave"),
    ("Telefoon & internet", "uitgave"),
    ("Verzekeringen & zorg", "uitgave"),
    ("Vervoer & auto", "uitgave"),
    ("Online winkelen", "uitgave"),
    ("Kleding & schoenen", "uitgave"),
    ("Drogisterij & verzorging", "uitgave"),
    ("Huis & tuin", "uitgave"),
    ("Kinderen", "uitgave"),
    ("Huisdieren", "uitgave"),
    ("Vrije tijd & uitjes", "uitgave"),
    ("Vakantie & reizen", "uitgave"),
    ("Gezondheid", "uitgave"),
    ("Belastingen & gemeente", "uitgave"),
    ("Goede doelen & cadeaus", "uitgave"),
    ("Contant geld", "uitgave"),
    ("Bankkosten", "uitgave"),
    ("Betaalverzoeken & personen", "uitgave"),
    ("Overige uitgaven", "uitgave"),
    ("Salaris", "inkomen"),
    ("Inleg partners", "inkomen"),
    ("Toeslagen & teruggaven", "inkomen"),
    ("Overige inkomsten", "inkomen"),
    ("Sparen & beleggen", "overboeking"),
    ("Interne overboeking", "overboeking"),
    (UNCATEGORIZED, "uitgave"),
]

# (patroon, categorie, richting) - richting: "af", "bij" of "" (beide)
DEFAULT_RULES = [
    # Boodschappen
    *[(p, "Boodschappen", "") for p in [
        "albert heijn", "ah to go", "jumbo", "lidl", "aldi", "plus ", "dirk ", "dekamarkt",
        "hoogvliet", " ah ", "supermarkt", "coop ", "spar ", "vomar", "poiesz", "picnic", "crisp", "ekoplaza",
        "marqt", "nettorama", "boni ", "jan linders", "flink", "amazing oriental",
        "slagerij", "bakkerij", "bakker ", "groenteboer", "kaashandel", "action ",
    ]],
    # Thuisbezorgd & afhaal
    *[(p, "Thuisbezorgd & afhaal", "") for p in [
        "thuisbezorgd", "takeaway", "uber eats", "ubereats", "deliveroo", "dominos",
        "domino's", "new york pizza", "just eat", "febo", "mcdonald", "burger king", "kfc",
        "subway", "snackbar", "snack", "cafetaria", "friet",
    ]],
    # Horeca
    *[(p, "Uit eten & horeca", "") for p in [
        "restaurant", "cafe ", "café", "eetcafe", "brasserie", "starbucks", "bagels & beans",
        "lunchroom", "ristorante", "ristor", "trattoria", "pizz", "ijssalon", "patisserie", "coffee", "koffie", "bar ", "grand café", "sushi", "pizzeria", "grand cafe", "zettle_*", "sumup *",
    ]],
    # Abonnementen & streaming
    *[(p, "Abonnementen & streaming", "") for p in [
        "netflix", "nlziet", "postcode loterij", "staatsloterij", "vriendenloterij", "kpn tv", "canal digitaal", "spotify", "disney plus", "disney+", "videoland", "hbo max", "max.com",
        "npo plus", "npo start", "apple.com/bill", "itunes", "google play", "youtube",
        "amazon prime", "primevideo", "audible", "storytel", "ad.nl", "volkskrant",
        "nrc", "de telegraaf", "dpg media", "blendle", "sportschool", "basic-fit",
        "basic fit", "anytime fitness", "trainmore", "chatgpt", "openai", "microsoft",
        "icloud", "dropbox", "adobe", "patreon", "viaplay", "ziggo sport", "dazn",
    ]],
    # Wonen
    *[(p, "Wonen", "") for p in [
        "hypotheek", "hypotheken", "huur ", "woningcorporatie", "woonstichting", "vve ", "vereniging van eigenaren",
        "ymere", "eigen haard", "vestia", "portaal", "de alliantie", "obvion", "florius",
        "munt hypotheken", "nationale-nederlanden hypotheken",
    ]],
    # Energie & water
    *[(p, "Energie & water", "") for p in [
        "eneco", "vattenfall", "essent", "greenchoice", "budget energie", "energiedirect",
        "frank energie", "tibber", "zonneplan", "vandebron", "oxxio", "pure energie",
        "waternet", "vitens", "evides", "brabant water", "pwn ", "dunea", "oasen",
        "wml ", "waterbedrijf", "stedin", "liander", "enexis",
    ]],
    # Telefoon & internet
    *[(p, "Telefoon & internet", "") for p in [
        "ziggo", "kpn", "t-mobile", "odido", "vodafone", "tele2", "simyo", "ben ",
        "lebara", "youfone", "hollandsnieuwe", "delta fiber", "caiway", "budget mobiel",
    ]],
    # Verzekeringen & zorg
    *[(p, "Verzekeringen & zorg", "") for p in [
        "zilveren kruis", "vgz", " cz ", "cz groep", "menzis", "dsw", "zorg en zekerheid",
        "ohra", "interpolis", "centraal beheer", "fbto", "anwb verzeker", "unive", "univé",
        "nationale-nederlanden", "allianz", "a.s.r", "asr ", "aegon", "inshared",
        "ditzo", "nn verzekeren", "nn schadeverzekering", "dela ", "dela natura", "zevenwouden", "verzekering", "promovendum", "de goudse", "klaverblad",
    ]],
    # Vervoer & auto
    *[(p, "Vervoer & auto", "") for p in [
        "ns groep", "tankstation", "parkeer", "ns reizigers", "ns-", "ov-chipkaart", "translink", "gvb", "ret ",
        "htm ", "arriva", "connexxion", "qbuzz", "keolis", "shell", "esso", "bp ",
        "tango", "tinq", "texaco", "total", "gulf", "avia", "q8", "fastned",
        "allego", "vattenfall incharge", "parkeren", "parkmobile", "yellowbrick",
        "q-park", "anwb", "kwik-fit", "halfords", "wegenbelasting", "swapfiets",
        "greenwheels", "uber", "bolt.eu",
    ]],
    # Online winkelen
    *[(p, "Online winkelen", "") for p in [
        "bol.com", "vinted", "marktplaats",
        "postnl", "dhl", "etsy", "otto ", "lidl-shop", "hema.nl", "bol com", "coolblue", "amazon", "zalando", "wehkamp", "aliexpress",
        "temu", "shein", "mediamarkt", "paypal", "klarna", "afterpay", "riverty",
    ]],
    # Kleding
    *[(p, "Kleding & schoenen", "") for p in [
        "h&m", "zara", "primark", "c&a", "we fashion", "only ", "jack & jones",
        "scapino", "van haren", "vanharen", "nike", "adidas", "decathlon", "bristol",
        "zeeman", "hunkemoller", "hunkemöller", "the sting", "costes", "jd sports",
    ]],
    # Drogisterij
    *[(p, "Drogisterij & verzorging", "") for p in [
        "kruidvat", "drogist", "dm drogerie", "holland barrett", "holland & barrett", "rossmann", "etos", "trekpleister", "da drogist", "douglas", "ici paris",
        "rituals", "kapper", "barbershop", "hairstyl",
    ]],
    # Huis & tuin
    *[(p, "Huis & tuin", "") for p in [
        "ikea", "bloemen", "bloemist", "fleurop", "tuinmeubel", "gamma", "praxis", "karwei", "hornbach", "intratuin", "hema",
        "blokker", "xenos", "leen bakker", "kwantum", "jysk", "welkoop", "tuincentrum",
        "flying tiger", "sostrene grene", "søstrene grene", "hubo",
    ]],
    # Kinderen
    *[(p, "Kinderen", "") for p in [
        "kinderopvang", "zwangerschap", "kraamzorg", "luiers", "nijntje", "little dutch", "noppies", "kinderdagverblijf", "bso ", "partou", "kinderrijk", "kids foundation",
        "intertoys", "bart smit", "prenatal", "babypark", "zwemles", "school",
    ]],
    # Huisdieren
    *[(p, "Huisdieren", "") for p in [
        "dierenarts", "pets place", "jumper", "zooplus", "dierenspeciaalzaak", "discus ",
        "petsplace", "brekz",
    ]],
    # Vrije tijd
    *[(p, "Vrije tijd & uitjes", "") for p in [
        "pathe", "sauna", "thermen", "escape room", "bowling", "pathé", "vue ", "kinepolis", "bioscoop", "museum", "efteling",
        "ticketmaster", "eventim", "ticketswap", "bol.com cadeau", "steam", "playstation",
        "nintendo", "xbox", "bruna", "ako ", "boekhandel", "libris", "theater",
        "dierentuin", "blijdorp", "artis", "burgers zoo", "zwembad",
    ]],
    # Vakantie
    *[(p, "Vakantie & reizen", "") for p in [
        "booking.com", "airbnb", "transavia", "klm", "easyjet", "ryanair", "vueling",
        "tui ", "corendon", "sunweb", "center parcs", "landal", "roompot", "hotel",
        "expedia", "schiphol", "camping", "eurostar", "flixbus",
    ]],
    # Gezondheid
    *[(p, "Gezondheid", "") for p in [
        "apotheek", "tandarts", "tandarts", "huisarts", "fysiotherap", "ziekenhuis", "opticien",
        "pearle", "hans anders", "specsavers", "mondzorg",
    ]],
    # Belastingen & gemeente
    *[(p, "Belastingen & gemeente", "af") for p in [
        "belastingdienst", "gemeente", "waterschap", "hoogheemraadschap", "cjib",
        "rdw", "belasting", "gbhw", "bghu", "svhw", "blauwe hart", "cocensus",
    ]],
    # Goede doelen & cadeaus
    *[(p, "Goede doelen & cadeaus", "") for p in [
        "kwf", "greetz", "kaartje2go", "hallmark", "unicef", "rode kruis", "artsen zonder grenzen", "greenpeace", "wnf",
        "hartstichting", "amnesty", "giro 555", "cadeaukaart", "vvv cadeau",
    ]],
    # Contant geld
    ("geldautomaat", "Contant geld", "af"),
    ("geldmaat", "Contant geld", "af"),
    # Bankkosten
    ("kosten oranjepakket", "Bankkosten", "af"),
    ("kosten betaalpakket", "Bankkosten", "af"),
    ("ing bank n.v.", "Bankkosten", "af"),
    ("debetrente", "Bankkosten", "af"),
    # Betaalverzoeken
    ("via tikkie", "Betaalverzoeken & personen", ""),
    ("betaalverzoek", "Betaalverzoeken & personen", ""),
    # Inkomsten
    ("salaris", "Salaris", "bij"),
    ("loon ", "Salaris", "bij"),
    ("uwv", "Toeslagen & teruggaven", "bij"),
    ("svb", "Toeslagen & teruggaven", "bij"),
    ("belastingdienst", "Toeslagen & teruggaven", "bij"),
    ("toeslag", "Toeslagen & teruggaven", "bij"),
    ("kinderbijslag", "Toeslagen & teruggaven", "bij"),
    ("teruggave", "Toeslagen & teruggaven", "bij"),
    ("restitutie", "Toeslagen & teruggaven", "bij"),
    ("terugbetaling", "Toeslagen & teruggaven", "bij"),
    # Sparen & beleggen
    ("oranje spaarrekening", "Sparen & beleggen", ""),
    ("spaarrekening", "Sparen & beleggen", ""),
    ("naar oranje spaarrekening", "Sparen & beleggen", ""),
    ("van oranje spaarrekening", "Sparen & beleggen", ""),
    ("spaardoel", "Sparen & beleggen", ""),
    ("beleggen", "Sparen & beleggen", ""),
    ("degiro", "Sparen & beleggen", ""),
    ("meesman", "Sparen & beleggen", ""),
    ("brand new day", "Sparen & beleggen", ""),
    ("bux ", "Sparen & beleggen", ""),
    ("trade republic", "Sparen & beleggen", ""),
    ("peaks", "Sparen & beleggen", ""),
]

# ISO-landcodes die ING achter de naam van buitenlandse pinbetalingen zet.
# Een pinbetaling in het buitenland valt automatisch onder vakantie.
FOREIGN_COUNTRY_CODES = {
    "DEU", "BEL", "LUX", "FRA", "ESP", "PRT", "ITA", "AUT", "CHE", "GBR", "IRL", "DNK", "SWE",
    "NOR", "FIN", "POL", "CZE", "HUN", "HRV", "SVN", "SVK", "GRC", "TUR", "CYP", "MLT", "USA",
    "CAN", "MEX", "THA", "IDN", "ISL", "EST", "LVA", "LTU", "ROU", "BGR", "MAR", "EGY", "ARE",
}
FOREIGN_CATEGORY = "Vakantie & reizen"
