import requests

def search_openfoodfacts(q: str, limit: int = 10):
    """
    Returns foods with macros per 100g from OpenFoodFacts (no key needed).
    """
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": q,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit,
    }
    r = requests.get(url, params=params, timeout=6)
    r.raise_for_status()
    out = []
    for p in r.json().get("products", []):
        name = p.get("product_name") or p.get("generic_name") or p.get("brands") or "Food"
        nutr = p.get("nutriments", {}) or {}

        def num(x):
            try:
                return float(nutr.get(x))
            except (TypeError, ValueError):
                return None

        # kcal can be in energy-kcal_100g or energy_100g (kJ → convert)
        kcal = num("energy-kcal_100g")
        if kcal is None and (kJ := num("energy_100g")) is not None:
            kcal = kJ / 4.184

        protein = num("proteins_100g")
        carbs   = num("carbohydrates_100g")
        fat     = num("fat_100g")

        if any(v is not None for v in (kcal, protein, carbs, fat)):
            out.append({
                "id": p.get("code"),
                "name": name.strip(),
                "brand": (p.get("brands") or "").strip(),
                "per": 100,  # values are per 100g
                "calories": round(kcal or 0, 1),
                "protein": round(protein or 0, 1),
                "carbs":   round(carbs or 0, 1),
                "fat":     round(fat or 0, 1),
                "serving_size": (p.get("serving_size") or "").strip(),
            })
    return out
