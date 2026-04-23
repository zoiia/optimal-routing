"""Port coordinate database. Minimal set for common freight lanes."""

# Coordinates in decimal degrees (lat, lon)
# Source: maritime references, UNLOCODE registry
PORTS = {
    "CNSHA": {"name": "Shanghai", "lat": 31.23, "lon": 121.47, "country": "CN"},
    "CNNGB": {"name": "Ningbo", "lat": 29.87, "lon": 121.55, "country": "CN"},
    "CNSZX": {"name": "Shenzhen", "lat": 22.54, "lon": 114.06, "country": "CN"},
    "HKHKG": {"name": "Hong Kong", "lat": 22.28, "lon": 114.16, "country": "HK"},
    "SGSIN": {"name": "Singapore", "lat": 1.26, "lon": 103.82, "country": "SG"},
    "KRPUS": {"name": "Busan", "lat": 35.10, "lon": 129.04, "country": "KR"},
    "VNSGN": {"name": "Ho Chi Minh", "lat": 10.76, "lon": 106.70, "country": "VN"},
    "INMUN": {"name": "Mundra", "lat": 22.74, "lon": 69.71, "country": "IN"},
    "INNSA": {"name": "Nhava Sheva", "lat": 18.95, "lon": 72.95, "country": "IN"},
    "AEJEA": {"name": "Jebel Ali", "lat": 25.01, "lon": 55.05, "country": "AE"},
    "NLRTM": {"name": "Rotterdam", "lat": 51.95, "lon": 4.14, "country": "NL"},
    "DEHAM": {"name": "Hamburg", "lat": 53.54, "lon": 9.98, "country": "DE"},
    "BEANR": {"name": "Antwerp", "lat": 51.22, "lon": 4.40, "country": "BE"},
    "FRLEH": {"name": "Le Havre", "lat": 49.48, "lon": 0.11, "country": "FR"},
    "GBFXT": {"name": "Felixstowe", "lat": 51.96, "lon": 1.35, "country": "GB"},
    "ESALG": {"name": "Algeciras", "lat": 36.13, "lon": -5.44, "country": "ES"},
    "ESVLC": {"name": "Valencia", "lat": 39.44, "lon": -0.32, "country": "ES"},
    "ITGOA": {"name": "Genoa", "lat": 44.40, "lon": 8.93, "country": "IT"},
    "PTLIS": {"name": "Lisbon", "lat": 38.70, "lon": -9.14, "country": "PT"},
    "USNYC": {"name": "New York", "lat": 40.68, "lon": -74.04, "country": "US"},
    "USLAX": {"name": "Los Angeles", "lat": 33.74, "lon": -118.27, "country": "US"},
    "USLGB": {"name": "Long Beach", "lat": 33.76, "lon": -118.20, "country": "US"},
    "USSAV": {"name": "Savannah", "lat": 32.08, "lon": -81.09, "country": "US"},
    "USCHS": {"name": "Charleston", "lat": 32.78, "lon": -79.93, "country": "US"},
    "USHOU": {"name": "Houston", "lat": 29.72, "lon": -95.02, "country": "US"},
    "BRSSZ": {"name": "Santos", "lat": -23.96, "lon": -46.33, "country": "BR"},
    "MXZLO": {"name": "Manzanillo", "lat": 19.05, "lon": -104.32, "country": "MX"},
    "PAPTY": {"name": "Panama City", "lat": 8.97, "lon": -79.53, "country": "PA"},
    "EGPSD": {"name": "Port Said", "lat": 31.26, "lon": 32.30, "country": "EG"},
    "EGSUZ": {"name": "Suez", "lat": 29.97, "lon": 32.52, "country": "EG"},
    "ZADUR": {"name": "Durban", "lat": -29.87, "lon": 31.02, "country": "ZA"},
    "AUSYD": {"name": "Sydney", "lat": -33.86, "lon": 151.21, "country": "AU"},
}


def find_port(query: str) -> dict | None:
    """Look up port by UNLOCODE or city name (case-insensitive, fuzzy)."""
    query = query.strip().upper()

    # Exact UNLOCODE match
    if query in PORTS:
        return {"code": query, **PORTS[query]}

    # Case-insensitive name match
    query_lower = query.lower()
    for code, data in PORTS.items():
        if data["name"].lower() == query_lower:
            return {"code": code, **data}

    # Partial name match (contains)
    for code, data in PORTS.items():
        if query_lower in data["name"].lower() or data["name"].lower() in query_lower:
            return {"code": code, **data}

    return None