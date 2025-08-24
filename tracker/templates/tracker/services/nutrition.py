# tracker/services/nutrition.py

def mifflin_bmr(sex: str, weight_kg: float, height_cm: float, age: int):
    if not (sex and weight_kg and height_cm and age):
        return None
    if sex == "M":
        return 10*weight_kg + 6.25*height_cm - 5*age + 5
    elif sex == "F":
        return 10*weight_kg + 6.25*height_cm - 5*age - 161
    return None

def activity_factor(activity: str):
    return {
        "sedentary":   1.20,
        "light":       1.375,
        "moderate":    1.55,
        "active":      1.725,
        "very_active": 1.90,
    }.get(activity or "moderate", 1.55)

def suggest_calorie_target(goal):
    bmr = mifflin_bmr(goal.sex, goal.weight_kg, goal.height_cm, goal.age)
    if bmr is None:
        return {"recommended": None, "why": "Add sex, age, height, and weight to get a TDEE estimate."}

    tdee = bmr * activity_factor(goal.activity)

    # daily kcal change from kg/week (~7700 kcal/kg)
    delta = (goal.weekly_rate_kg or 0) * 7700 / 7.0
    if goal.objective == "lose":
        delta = -abs(delta)
    elif goal.objective == "gain":
        delta = abs(delta)
    else:
        delta = 0.0

    # safety cap +/- 20% of TDEE
    cap = 0.20 * tdee
    if delta > cap:   delta = cap
    if delta < -cap:  delta = -cap

    recommended = round(tdee + delta)
    percent = round((delta / tdee) * 100.0, 1) if tdee else 0.0
    return {
        "recommended": recommended,
        "tdee": round(tdee),
        "delta_per_day": round(delta),
        "percent": percent,
        "why": f"TDEE ≈ {round(tdee)} kcal; "
               f"{('deficit' if delta<0 else 'surplus' if delta>0 else 'neutral')} ≈ {round(delta)} kcal/day ({percent}%).",
    }

def _round5(x):  # tidy numbers for targets
    return int(round(x / 5.0) * 5)

def suggest_macros(goal, target_calories=None):
    """
    Return macro grams for a given calorie target.
    Priority 1: bodyweight-based (protein ~1.8 g/kg, fat ~0.8 g/kg)
    Priority 2: fallback to ratios if weight unknown (30/25/45 kcal split: P/F/C)
    """
    if not target_calories or target_calories <= 0:
        target_calories = goal.calories or 2000

    w = goal.weight_kg
    if w:
        # per-kg approach (middle of common evidence-based ranges)
        prot_g = max(60, min(250, _round5(1.8 * w)))
        fat_g  = max(30, min(120, _round5(0.8 * w)))
        rem_kcal = target_calories - 4*prot_g - 9*fat_g
        carbs_g  = _round5(max(0, rem_kcal / 4.0))

        # If very low calories caused negative carbs, nudge fat down to make room
        if carbs_g == 0 and rem_kcal < 0:
            fat_g  = max(30, _round5((target_calories - 4*prot_g) / 9.0 * 0.25))  # ~25% of leftover after protein
            rem_kcal = target_calories - 4*prot_g - 9*fat_g
            carbs_g  = _round5(max(0, rem_kcal / 4.0))

        return {
            "calories": target_calories,
            "protein": prot_g,
            "fat": fat_g,
            "carbs": carbs_g,
            "method": "per-kg",
        }

    # ratio fallback (kcal split → grams)
    ratios = {"protein": 0.30, "fat": 0.25, "carbs": 0.45}
    prot_g = _round5((target_calories * ratios["protein"]) / 4.0)
    fat_g  = _round5((target_calories * ratios["fat"]) / 9.0)
    carbs_g = _round5(max(0, (target_calories - 4*prot_g - 9*fat_g) / 4.0))
    return {
        "calories": target_calories,
        "protein": prot_g,
        "fat": fat_g,
        "carbs": carbs_g,
        "method": "ratio",
    }
