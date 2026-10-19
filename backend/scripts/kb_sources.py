"""Títulos que carga el script de la base de conocimiento.

Los títulos que no existan se informan y se omiten: se pueden editar sin tocar el resto.
Wikipedia tiene pocos artículos sobre la franquicia; el grueso del contenido viene de la wiki.
"""

WIKIPEDIA_TITLES = {
    "es": [
        "Cyberpunk 2077",
        "Cyberpunk 2077: Phantom Liberty",
        "Cyberpunk: Edgerunners",
        "Cyberpunk 2020",
        "Cyberpunk (juego de rol)",
        "Mike Pondsmith",
        "CD Projekt",
        "Cyberpunk",
    ],
    "en": [
        "Cyberpunk 2077",
        "Cyberpunk 2077: Phantom Liberty",
        "Cyberpunk: Edgerunners",
        "Cyberpunk (role-playing game)",
        "Cyberpunk 2020",
        "Cyberpunk Red",
        "Mike Pondsmith",
        "CD Projekt",
        "Studio Trigger",
        "Cyberpunk",
    ],
}

# Wiki de la comunidad (cyberpunk.fandom.com), texto bajo CC BY-SA.
FANDOM_TITLES = [
    # Obras
    "Cyberpunk 2077", "Cyberpunk 2077: Phantom Liberty", "Cyberpunk: Edgerunners",
    "Cyberpunk 2020", "Cyberpunk RED",
    # Mundo y conceptos
    "Night City", "Cyberpsychosis", "Braindance", "Relic", "Blackwall", "Netrunner",
    "Dogtown", "Afterlife", "Delamain",
    # Corporaciones y facciones
    "Arasaka Corporation", "Militech", "Kang Tao", "Biotechnica", "Trauma Team International",
    "NCPD", "Maelstrom", "Valentinos", "Tyger Claws", "6th Street", "Animals", "Voodoo Boys",
    "Wraiths", "Aldecaldos", "Mox", "Scavengers",
    # Personajes del juego
    "V", "Johnny Silverhand", "Alt Cunningham", "Rogue Amendiares", "Kerry Eurodyne",
    "Samurai (band)", "Goro Takemura", "Saburo Arasaka", "Yorinobu Arasaka", "Hanako Arasaka",
    "Jackie Welles", "Judy Alvarez", "Panam Palmer", "River Ward", "Evelyn Parker",
    "Dexter DeShawn", "Viktor Vektor", "Misty Olszewski", "Adam Smasher", "Solomon Reed",
    "Songbird", "Meredith Stout", "Claire Russell", "T-Bug", "Wakako Okada", "Regina Jones",
    # Edgerunners
    "David Martinez", "Lucy", "Maine", "Rebecca", "Pilar", "Kiwi", "Dorio", "Faraday",
    "Gloria Martinez",
]
