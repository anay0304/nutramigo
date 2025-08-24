# tracker/views.py
import datetime as dt
import json as _json
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET
import csv
from django.http import HttpResponse
from django.urls import reverse
from .forms import GoalForm, MealForm
from .models import Goal, Meal
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from tracker.templates.tracker.services.food_api import search_openfoodfacts
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Meal, Goal, FavoriteFood
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
import json
from django.views.decorators.http import require_POST
from tracker.templates.tracker.services.ai_assistant import parse_message, suggest_meals, food_by_name
from tracker.templates.tracker.services.nutrition import suggest_calorie_target, suggest_macros


@require_GET
def logout_now(request):
    """Optional GET-based logout (Django’s built-in uses POST)."""
    logout(request)
    return redirect("login")


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect("meal_list")
    else:
        form = UserCreationForm()
    return render(request, "tracker/signup.html", {"form": form})


# ---- Meals ------------------------------------------------------------------

@login_required
def meal_list(request):
    # Date filter (defaults to today)
    selected_date_str = request.GET.get("date")
    if selected_date_str:
        try:
            day = dt.date.fromisoformat(selected_date_str)
        except ValueError:
            day = dt.date.today()
    else:
        day = dt.date.today()

    # Meals for the selected day (scoped to current user)
    meals = (
        Meal.objects.filter(user=request.user, date=day)
        .order_by("-id")
    )

    # Daily totals
    totals = {
        "calories": sum(m.calories for m in meals),
        "protein": sum(m.protein for m in meals),
        "carbs":   sum(m.carbs   for m in meals),
        "fat":     sum(m.fat     for m in meals),
    }

    # Goals (create defaults if missing)
    goal, _ = Goal.objects.get_or_create(user=request.user)
    reco = suggest_calorie_target(goal)
    macro_reco = suggest_macros(goal, (reco.get("recommended") or goal.calories))


    # Progress % and capped values for bar widths
    def pct(x, g):  # avoid div-by-zero
        return round(100 * x / g, 1) if g else 0

    progress = {
        "calories": pct(totals["calories"], goal.calories),
        "protein":  pct(totals["protein"],  goal.protein),
        "carbs":    pct(totals["carbs"],    goal.carbs),
        "fat":      pct(totals["fat"],      goal.fat),
    }
    progress_capped = {k: min(100, v) for k, v in progress.items()}

    # ---- Last 7 days calories (for the bar chart) ----
    today = dt.date.today()
    days = [today - dt.timedelta(days=i) for i in range(6, -1, -1)]
    labels = [d.strftime("%b %d") for d in days]
    kcal_map = {d: 0 for d in days}

    agg = (
        Meal.objects.filter(user=request.user, date__range=[days[0], days[-1]])
        .values("date")
        .annotate(kcal=Sum("calories"))
    )
    for row in agg:
        kcal_map[row["date"]] = row["kcal"] or 0

    weekly_kcal = [kcal_map[d] for d in days]
    favorites = FavoriteFood.objects.filter(user=request.user).order_by('-created_at')
    
    recent_qs = Meal.objects.filter(user=request.user).order_by('-date', '-id')[:100]
    seen, recents = set(), []
    for m in recent_qs:
        key = (m.name or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)

        cal100  = m.cal_per_100g
        pro100  = m.protein_per_100g
        carb100 = m.carbs_per_100g
        fat100  = m.fat_per_100g
        if (cal100 is None or pro100 is None or carb100 is None or fat100 is None) and m.grams:
            s = 100.0 / m.grams
            cal100  = cal100  if cal100  is not None else round(m.calories * s, 1)
            pro100  = pro100  if pro100  is not None else round(m.protein  * s, 1)
            carb100 = carb100 if carb100 is not None else round(m.carbs    * s, 1)
            fat100  = fat100  if fat100  is not None else round(m.fat      * s, 1)

        recents.append({
            "name": m.name,
            "default_grams": m.grams or 100,
            "cal_per_100g": cal100 or 0,
            "protein_per_100g": pro100 or 0,
            "carbs_per_100g": carb100 or 0,
            "fat_per_100g": fat100 or 0,
        })
        if len(recents) >= 8:
            break

            # ---- badge colors for totals vs goals ----
    def badge_status(total, goal_val, kind):
        if not goal_val or goal_val <= 0:
            return "secondary"
        ratio = total / goal_val
        if kind == "calories":
            # under/on target = green, up to +10% = amber, beyond = red
            if ratio <= 1.00:
                return "success"
            elif ratio <= 1.10:
                return "warning"
            else:
                return "danger"
        else:  # macros
            # within ±10% of goal = green, under = amber, over = red
            if 0.90 <= ratio <= 1.10:
                return "success"
            elif ratio < 0.90:
                return "warning"
            else:
                return "danger"

    badges = {
        "calories": badge_status(totals["calories"], goal.calories, "calories"),
        "protein":  badge_status(totals["protein"],  goal.protein,  "macro"),
        "carbs":    badge_status(totals["carbs"],    goal.carbs,    "macro"),
        "fat":      badge_status(totals["fat"],      goal.fat,      "macro"),
    }


    context = {
        "meals": meals,
        "totals": totals,
        "selected_date": day.strftime("%Y-%m-%d"),
        "goal": goal,
        "progress": progress,                 # raw % (e.g., 120.0)
        "progress_capped": progress_capped,   # 0–100 (for bar widths)
        "weekly_labels": _json.dumps(labels),
        "weekly_kcal": _json.dumps(weekly_kcal),
        "favorites": favorites,
        "recents": recents,
        "badges": badges, 
        "reco": reco,
        "macro_reco": macro_reco,

    }

    return render(request, "tracker/meal_list.html", context)


@login_required
def add_meal(request):
    if request.method == "POST":
        form = MealForm(request.POST)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.user = request.user
            meal.save()
            messages.success(request, "Meal added.")
            return redirect("meal_list")
    else:
        form = MealForm()
    return render(request, "tracker/add_meal.html", {"form": form})



@login_required
def edit_meal(request, pk):
    meal = get_object_or_404(Meal, pk=pk, user=request.user)
    form = MealForm(request.POST or None, instance=meal)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Meal updated.")
        return redirect("meal_list")
    return render(request, "tracker/add_meal.html", {"form": form, "edit": True})
    

@login_required
def delete_meal(request, pk):
    """
    Delete via POST for safety. The template will submit a tiny form with CSRF.
    """
    meal = get_object_or_404(Meal, pk=pk, user=request.user)
    if request.method == "POST":
        meal.delete()
        messages.success(request, "Meal deleted.")
        return redirect("meal_list")
    return render(request, "tracker/confirm_delete.html", {"meal": meal})

@login_required
def edit_goal(request):
    goal, _ = Goal.objects.get_or_create(user=request.user)
    form = GoalForm(request.POST or None, instance=goal)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Goals updated.")
        return redirect("meal_list")
    return render(request, "tracker/edit_goal.html", {"form": form})

@login_required
def export_csv(request):
    """
    Download meals as CSV.
    Supports:
      - ?date=YYYY-MM-DD  (single day)
      - ?start=YYYY-MM-DD&end=YYYY-MM-DD  (range)
      - otherwise: all meals for the user
    """
    qs = Meal.objects.filter(user=request.user)

    start = request.GET.get('start')
    end   = request.GET.get('end')
    date_str = request.GET.get('date')

    filename = "meals.csv"
    try:
        if start and end:
            s = dt.date.fromisoformat(start)
            e = dt.date.fromisoformat(end)
            qs = qs.filter(date__range=[s, e])
            filename = f"meals_{s.isoformat()}_to_{e.isoformat()}.csv"
        elif date_str:
            d = dt.date.fromisoformat(date_str)
            qs = qs.filter(date=d)
            filename = f"meals_{d.isoformat()}.csv"
    except ValueError:
        messages.warning(request, "Invalid date format in query; exporting all meals.")

    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    w = csv.writer(resp)
    w.writerow(['Date', 'Name', 'Calories', 'Protein', 'Carbs', 'Fat'])
    for m in qs.order_by('date', 'id'):
        w.writerow([m.date, m.name, m.calories, m.protein, m.carbs, m.fat])
    return resp


@login_required
def copy_yesterday(request):
    """
    Copy all meals from yesterday to a target date (default = today).
    Usage: /copy-yesterday/?to=YYYY-MM-DD  (or ?date=)
    """
    target_str = request.GET.get('to') or request.GET.get('date')
    try:
        target = dt.date.fromisoformat(target_str) if target_str else dt.date.today()
    except ValueError:
        target = dt.date.today()

    source = target - dt.timedelta(days=1)

    src_meals = Meal.objects.filter(user=request.user, date=source)
    clones = [
        Meal(
            user=request.user,
            name=m.name,
            calories=m.calories,
            protein=m.protein,
            carbs=m.carbs,
            fat=m.fat,
            date=target,
        )
        for m in src_meals
    ]

    if clones:
        Meal.objects.bulk_create(clones)
        messages.success(request, f"Copied {len(clones)} meal(s) from {source} → {target}.")
    else:
        messages.info(request, f"No meals found on {source} to copy.")

    return redirect(f"{reverse('meal_list')}?date={target.isoformat()}")


@login_required
def food_search(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"results": []})
    try:
        results = search_openfoodfacts(q)
    except Exception:
        results = []
    return JsonResponse({"results": results})


# tracker/views.py

@login_required
@require_POST
def quick_add_food(request):
    try:
        name     = request.POST['name']
        grams    = float(request.POST.get('grams', 100))
        # per-100g values from client (preferred), else compute from totals+grams
        cal100   = request.POST.get('cal_per_100g')
        pro100   = request.POST.get('protein_per_100g')
        carb100  = request.POST.get('carbs_per_100g')
        fat100   = request.POST.get('fat_per_100g')
        date_str = request.POST.get('date') or dt.date.today().isoformat()
        day      = dt.date.fromisoformat(date_str)

        # Totals (client may send them, but we'll recompute on save)
        calories = int(float(request.POST.get('calories', 0)))
        protein  = float(request.POST.get('protein', 0))
        carbs    = float(request.POST.get('carbs', 0))
        fat      = float(request.POST.get('fat', 0))

        meal = Meal(
            user=request.user,
            name=name,
            date=day,
            grams=grams,
            calories=calories, protein=protein, carbs=carbs, fat=fat,
            # set per-100g if provided
            cal_per_100g=float(cal100) if cal100 else None,
            protein_per_100g=float(pro100) if pro100 else None,
            carbs_per_100g=float(carb100) if carb100 else None,
            fat_per_100g=float(fat100) if fat100 else None,
            source="OFF",
            source_id=request.POST.get('source_id',''),
        )

        # If per-100g missing but totals+grams present, derive them (so future edits still work)
        if meal.grams and meal.cal_per_100g is None and grams > 0:
            scale100 = 100.0 / grams
            meal.cal_per_100g     = round(meal.calories * scale100, 1)
            meal.protein_per_100g = round(meal.protein  * scale100, 1)
            meal.carbs_per_100g   = round(meal.carbs    * scale100, 1)
            meal.fat_per_100g     = round(meal.fat      * scale100, 1)

        meal.save()  # .save() will recalc totals from per-100g if available
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    

@login_required
def add_favorite_from_meal(request, pk):
    """Create/update a FavoriteFood from an existing meal."""
    meal = get_object_or_404(Meal, pk=pk, user=request.user)

    # Prefer existing per-100g fields; otherwise derive from totals + grams
    cal100 = meal.cal_per_100g
    pro100 = meal.protein_per_100g
    carb100 = meal.carbs_per_100g
    fat100 = meal.fat_per_100g
    default_grams = meal.grams or 100

    if (cal100 is None or pro100 is None or carb100 is None or fat100 is None) and meal.grams:
        scale100 = 100.0 / meal.grams
        cal100  = cal100  if cal100  is not None else round(meal.calories * scale100, 1)
        pro100  = pro100  if pro100  is not None else round(meal.protein  * scale100, 1)
        carb100 = carb100 if carb100 is not None else round(meal.carbs    * scale100, 1)
        fat100  = fat100  if fat100  is not None else round(meal.fat      * scale100, 1)

    fav, created = FavoriteFood.objects.update_or_create(
        user=request.user,
        name=meal.name,
        defaults={
            "brand": "",
            "default_grams": default_grams,
            "cal_per_100g": cal100,
            "protein_per_100g": pro100,
            "carbs_per_100g": carb100,
            "fat_per_100g": fat100,
            "source": meal.source if hasattr(meal, "source") else "",
            "source_id": meal.source_id if hasattr(meal, "source_id") else "",
        }
    )
    messages.success(request, ("Added to favorites." if created else "Updated favorite."))
    return redirect(f"{reverse('meal_list')}?date={meal.date.isoformat()}")


@login_required
@require_POST
def quick_add_favorite(request, fav_id):
    """Create a Meal from a FavoriteFood for a given date + grams."""
    fav = get_object_or_404(FavoriteFood, id=fav_id, user=request.user)
    try:
        grams = float(request.POST.get("grams") or fav.default_grams or 100)
        day = dt.date.fromisoformat(request.POST.get("date")) if request.POST.get("date") else dt.date.today()
    except Exception:
        messages.error(request, "Invalid grams/date.")
        return redirect("meal_list")

    meal = Meal(
        user=request.user,
        name=fav.name,
        date=day,
        grams=grams,
        cal_per_100g=fav.cal_per_100g,
        protein_per_100g=fav.protein_per_100g,
        carbs_per_100g=fav.carbs_per_100g,
        fat_per_100g=fav.fat_per_100g,
        source=fav.source,
        source_id=fav.source_id,
    )
    # save() will compute totals from per-100g + grams (your recalc logic)
    meal.save()
    messages.success(request, f"Added {fav.name} ({int(grams)} g).")
    return redirect(f"{reverse('meal_list')}?date={day.isoformat()}")


@login_required
def ai_assist(request):
    # Use selected date or today
    selected_date_str = request.GET.get("date")
    day = dt.date.fromisoformat(selected_date_str) if selected_date_str else dt.date.today()

    meals = Meal.objects.filter(user=request.user, date=day)
    totals = {
        "kcal": sum(m.calories for m in meals),
        "p":    sum(m.protein  for m in meals),
        "c":    sum(m.carbs    for m in meals),
        "f":    sum(m.fat      for m in meals),
    }
    goal, _ = Goal.objects.get_or_create(user=request.user)
    need = {
        "kcal": max(goal.calories - totals["kcal"], 0),
        "p":    max(goal.protein  - totals["p"],    0),
        "c":    max(goal.carbs    - totals["c"],    0),
        "f":    max(goal.fat      - totals["f"],    0),
    }
    # default suggestions with no constraints
    plans = suggest_meals(need, prefs={})
    return render(request, "tracker/ai_assist.html", {
        "selected_date": day.strftime("%Y-%m-%d"),
        "need": need,
        "plans": plans,
    })

@login_required
@require_POST
def ai_suggest_api(request):
    # compute remaining need for the posted date
    day = dt.date.fromisoformat(request.POST.get("date"))
    meals = Meal.objects.filter(user=request.user, date=day)
    totals = {
        "kcal": sum(m.calories for m in meals),
        "p":    sum(m.protein  for m in meals),
        "c":    sum(m.carbs    for m in meals),
        "f":    sum(m.fat      for m in meals),
    }
    goal, _ = Goal.objects.get_or_create(user=request.user)
    need = {
        "kcal": max(goal.calories - totals["kcal"], 0),
        "p":    max(goal.protein  - totals["p"],    0),
        "c":    max(goal.carbs    - totals["c"],    0),
        "f":    max(goal.fat      - totals["f"],    0),
    }

    msg = request.POST.get("message", "")
    prefs = parse_message(msg)
    plans = suggest_meals(need, prefs)
    return JsonResponse({"need": need, "plans": plans})


# ... your ai_assist and ai_suggest_api already exist ...
@login_required
@require_POST
def ai_log_plan(request):
    created = 0
    errors = []
    seen = 0

    # date
    date_str = request.POST.get("date")
    try:
        day = dt.date.fromisoformat(date_str) if date_str else dt.date.today()
    except Exception:
        day = dt.date.today()

    # items (json)
    try:
        items = _json.loads(request.POST.get("items", "[]"))
    except Exception as e:
        return JsonResponse({"ok": False, "created": 0, "errors": [f"Bad JSON: {e}"]})

    for it in items:
        seen += 1
        name = (it.get("name") or "").strip()
        try:
            grams = float(it.get("grams") or 0)
        except Exception:
            grams = 0

        if not name:
            errors.append("Missing name")
            continue
        if grams <= 0:
            errors.append(f"{name}: grams <= 0")
            continue

        f = food_by_name(name)

        if f:
            cal100, p100, c100, fat100 = f.cal, f.p, f.c, f.f
        else:
            # fallback from totals sent by client
            try:
                kcal = float(it.get("kcal") or 0)
                p    = float(it.get("p") or 0)
                c    = float(it.get("c") or 0)
                fat  = float(it.get("f") or 0)
            except Exception:
                kcal = p = c = fat = 0.0

            if (kcal, p, c, fat) == (0, 0, 0, 0):
                errors.append(f"{name}: not in library and no macros provided")
                continue

            factor = 100.0 / grams  # grams > 0 checked above
            cal100 = round(kcal * factor, 2)
            p100   = round(p    * factor, 2)
            c100   = round(c    * factor, 2)
            fat100 = round(fat  * factor, 2)

        Meal.objects.create(
            user=request.user,
            name=name,
            date=day,
            grams=grams,
            cal_per_100g=cal100,
            protein_per_100g=p100,
            carbs_per_100g=c100,
            fat_per_100g=fat100,
            source="coach",
            source_id="plan",
        )
        created += 1

    return JsonResponse({
        "ok": True,
        "created": created,
        "seen": seen,
        "errors": errors,
        "redirect": reverse("meal_list") + f"?date={day.isoformat()}",
    })

# tracker/views.py (inside meal_list, after totals/goal are computed)


@login_required
@require_POST
def apply_calorie_reco(request):
    goal, _ = Goal.objects.get_or_create(user=request.user)
    rec = suggest_calorie_target(goal)
    if rec.get("recommended"):
        goal.calories = rec["recommended"]
        goal.save()
        messages.success(request, f"Updated daily calories to {rec['recommended']} (Coach).")
    else:
        messages.warning(request, "Please add sex, age, height and weight in Goals to enable recommendations.")
    return redirect("meal_list")

@login_required
@require_POST
def apply_macro_reco(request):
    goal, _ = Goal.objects.get_or_create(user=request.user)

    # decide which calories to use: current or the coach's recommended
    use_reco = request.POST.get("use_reco") == "1"
    calories_target = goal.calories or 2000
    if use_reco:
        rec = suggest_calorie_target(goal)
        if rec.get("recommended"):
            calories_target = rec["recommended"]
            goal.calories = calories_target  # also update calories when using reco

    m = suggest_macros(goal, calories_target)
    goal.protein = m["protein"]
    goal.carbs   = m["carbs"]
    goal.fat     = m["fat"]
    goal.save()

    from django.contrib import messages
    messages.success(
        request,
        f"Updated targets → {calories_target} kcal • P {m['protein']} g • C {m['carbs']} g • F {m['fat']} g."
    )
    return redirect("meal_list")