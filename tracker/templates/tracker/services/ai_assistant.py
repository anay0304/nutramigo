# tracker/services/ai_assistant.py
from dataclasses import dataclass
from typing import List, Dict, Any
import datetime as dt

@dataclass
class Food:
    name: str
    cal: float   # per 100g
    p: float
    c: float
    f: float
    tags: set    # e.g. {"vegan","vegetarian","dairy","meat","gluten"}

# Simple food library (per 100g)
FOODS: List[Food] = [
    Food("Grilled Chicken Breast", 165, 31, 0, 3.6, {"meat","gluten-free"}),
    Food("Greek Yogurt (nonfat)",  59,  10, 4, 0,   {"vegetarian","dairy","gluten-free"}),
    Food("Tofu (firm)",            76,  8,  2, 4.8, {"vegan","vegetarian","gluten-free"}),
    Food("Egg (whole)",            155, 13, 1.1, 11,{"vegetarian","gluten-free"}),
    Food("Oats (dry)",             389, 17, 66, 7,  {"vegetarian"}),
    Food("Cooked White Rice",      130, 2.7,28, 0.3,{"vegan","vegetarian","gluten-free"}),
    Food("Banana",                 96,  1.1,23, 0.3,{"vegan","vegetarian","gluten-free"}),
    Food("Almonds",                579, 21, 22, 50, {"vegan","vegetarian","gluten-free","nuts"}),
    Food("Avocado",                160, 2,  9,  15, {"vegan","vegetarian","gluten-free"}),
    Food("Broccoli",               34,  2.8,7,  0.4,{"vegan","vegetarian","gluten-free"}),
]

def _fits(food: Food, prefs: Dict[str,bool]) -> bool:
    """Simple dietary filter from chat constraints."""
    if prefs.get("vegan") and "vegan" not in food.tags:
        return False
    if prefs.get("vegetarian") and "vegetarian" not in food.tags:
        return False
    if prefs.get("no_dairy") and "dairy" in food.tags:
        return False
    if prefs.get("no_nuts") and "nuts" in food.tags:
        return False
    if prefs.get("gluten_free") and "gluten-free" not in food.tags:
        return False
    return True

def parse_message(msg: str) -> Dict[str,bool]:
    """Extract simple intents from a user message."""
    m = msg.lower()
    return {
        "high_protein":  any(k in m for k in ["high protein","more protein","protein"]),
        "low_carb":      any(k in m for k in ["low carb","less carbs","keto"]),
        "low_fat":       any(k in m for k in ["low fat","less fat"]),
        "vegetarian":    "vegetarian" in m,
        "vegan":         "vegan" in m,
        "no_dairy":      any(k in m for k in ["no dairy","dairy-free","lactose"]),
        "no_nuts":       "no nuts" in m,
        "gluten_free":   any(k in m for k in ["gluten-free","no gluten"]),
    }

def _grams_for(food: Food, need: Dict[str,float]) -> float:
    """
    Compute grams to target the *dominant* deficit macro for this food.
    Keep calories reasonable and cap between 30g and 400g.
    """
    # Choose which macro is most needed
    # (weight protein higher, then carbs, then fat)
    weights = {
        "p": max(need["p"], 0) * 1.3,
        "c": max(need["c"], 0) * 1.0,
        "f": max(need["f"], 0) * 0.7,
    }
    key = max(weights, key=weights.get)
    per100 = {"p": food.p, "c": food.c, "f": food.f}[key] or 0.0001
    g = (need[key] / per100) * 100.0

    # sanity: cap and avoid absurd calories
    g = max(30, min(g, 400))
    if (food.cal * g / 100.0) > max(need["kcal"] * 1.2, 400):   # avoid gross overshoot
        g = max(30, min(g, (need["kcal"] / food.cal) * 100.0))
    return round(g, 0)

def _totals(food: Food, g: float) -> Dict[str,float]:
    s = g / 100.0
    return {
        "kcal": round(food.cal * s),
        "p": round(food.p * s, 1),
        "c": round(food.c * s, 1),
        "f": round(food.f * s, 1),
    }

def suggest_meals(need: Dict[str,float], prefs: Dict[str,bool]) -> List[Dict[str,Any]]:
    """
    Return 3 suggestion 'plans'. Each plan has 1–3 foods with grams and totals.
    Very simple greedy pairing based on remaining macros + preferences.
    """
    pool = [f for f in FOODS if _fits(f, prefs)]
    if not pool:
        pool = FOODS[:]  # fallback

    # Sort helpers
    lean_protein  = sorted(pool, key=lambda x: (x.p, -x.f, x.cal), reverse=True)
    carb_sources  = sorted(pool, key=lambda x: (x.c, -x.f, -x.p), reverse=True)
    healthy_fats  = sorted(pool, key=lambda x: (x.f, x.cal), reverse=True)

    out = []

    # 1) High-protein fix
    f1 = next((f for f in lean_protein if f.p >= 10 and f.f <= 6), lean_protein[0])
    g1 = _grams_for(f1, need)
    out.append({
        "title": "Quick Protein Fix",
        "items": [{"name": f1.name, "grams": g1, **_totals(f1, g1)}],
    })

    # 2) Balanced bowl (protein + carb + veg)
    f2p = next((f for f in lean_protein if f.p >= 8 and f.f < 12), lean_protein[0])
    f2c = next((f for f in carb_sources if f.c >= 20 and f.cal <= 200), carb_sources[0])
    f2v = next((f for f in pool if "Broccoli" in f.name), pool[0])
    g2p = _grams_for(f2p, need)
    g2c = _grams_for(f2c, {"kcal": need["kcal"] - _totals(f2p,g2p)["kcal"], "p": 0, "c": need["c"], "f": 0})
    g2v = 100.0
    out.append({
        "title": "Balanced Bowl",
        "items": [
            {"name": f2p.name, "grams": g2p, **_totals(f2p, g2p)},
            {"name": f2c.name, "grams": g2c, **_totals(f2c, g2c)},
            {"name": f2v.name, "grams": g2v, **_totals(f2v, g2v)},
        ],
    })

    # 3) Fill the macro gap that’s largest
    dominant = max([("p", need["p"]), ("c", need["c"]), ("f", need["f"])], key=lambda x:x[1])[0]
    pool_sorted = {"p": lean_protein, "c": carb_sources, "f": healthy_fats}[dominant]
    f3a = pool_sorted[0]
    f3b = (pool_sorted[1] if len(pool_sorted) > 1 else pool_sorted[0])
    g3a = _grams_for(f3a, need)
    need2 = {
        k: max(need[k] - _totals(f3a,g3a)[k], 0)
        for k in ["kcal","p","c","f"]
    }
    g3b = _grams_for(f3b, need2)
    out.append({
        "title": "Macro Gap Filler",
        "items": [
            {"name": f3a.name, "grams": g3a, **_totals(f3a,g3a)},
            {"name": f3b.name, "grams": g3b, **_totals(f3b,g3b)},
        ],
    })

    # attach plan totals
    for plan in out:
        plan["totals"] = {
            "kcal": sum(i["kcal"] for i in plan["items"]),
            "p":    round(sum(i["p"] for i in plan["items"]),1),
            "c":    round(sum(i["c"] for i in plan["items"]),1),
            "f":    round(sum(i["f"] for i in plan["items"]),1),
        }
    return out

# Fast lookup by name when logging plans
# Add below the FOODS list and Food dataclass
FOOD_MAP_CI = {f.name.lower(): f for f in FOODS}

def food_by_name(name: str):
    if not name:
        return None
    return FOOD_MAP_CI.get(name.strip().lower())
