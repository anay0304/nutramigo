from django.db import models
from django.conf import settings
from django.conf import settings
from django.db import models
from django.db import models
from django.contrib.auth.models import User


class Meal(models.Model):
    MEAL_TYPES = [
        ('Breakfast','Breakfast'),
        ('Lunch','Lunch'),
        ('Dinner','Dinner'),
        ('Snack','Snack'),
    ]

    user     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meals', null=True, blank=True)
    name     = models.CharField(max_length=100)
    calories = models.IntegerField()
    protein  = models.FloatField()
    carbs    = models.FloatField()
    fat      = models.FloatField()
    date     = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES, default='Lunch')  # ✅ NEW

    def __str__(self):
        return f"{self.meal_type}: {self.name} ({self.calories} kcal)"


class Goal(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    calories = models.IntegerField(default=2000)
    protein  = models.FloatField(default=150)
    carbs    = models.FloatField(default=250)
    fat      = models.FloatField(default=70)

    def __str__(self):
        return f"{self.user.username} goals"
    
class Meal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    date = models.DateField()

    # totals (what you already had)
    calories = models.IntegerField(default=0)
    protein  = models.FloatField(default=0)
    carbs    = models.FloatField(default=0)
    fat      = models.FloatField(default=0)

    # NEW: quantity + per-100g (optional; only used when logged from a food DB)
    grams = models.FloatField(null=True, blank=True)
    cal_per_100g     = models.FloatField(null=True, blank=True)
    protein_per_100g = models.FloatField(null=True, blank=True)
    carbs_per_100g   = models.FloatField(null=True, blank=True)
    fat_per_100g     = models.FloatField(null=True, blank=True)
    source     = models.CharField(max_length=50, blank=True)   # e.g., 'OFF'
    source_id  = models.CharField(max_length=64, blank=True)   # OFF code

    def recalc_totals(self):
        """Recalculate totals from per-100g and grams."""
        if self.grams:
            scale = self.grams / 100.0
            if self.cal_per_100g is not None:
                self.calories = int(round((self.cal_per_100g or 0) * scale))
            if self.protein_per_100g is not None:
                self.protein = round((self.protein_per_100g or 0) * scale, 1)
            if self.carbs_per_100g is not None:
                self.carbs = round((self.carbs_per_100g or 0) * scale, 1)
            if self.fat_per_100g is not None:
                self.fat = round((self.fat_per_100g or 0) * scale, 1)

    def save(self, *args, **kwargs):
        # If we have grams and any per-100g value, recompute totals
        if self.grams and any(v is not None for v in [
            self.cal_per_100g, self.protein_per_100g, self.carbs_per_100g, self.fat_per_100g
        ]):
            self.recalc_totals()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.date})"
    
class FavoriteFood(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True)

    # default quantity you’ll propose in the UI (editable before adding)
    default_grams = models.FloatField(null=True, blank=True)

    # per-100g macros (so grams can rescale totals precisely)
    cal_per_100g     = models.FloatField(null=True, blank=True)
    protein_per_100g = models.FloatField(null=True, blank=True)
    carbs_per_100g   = models.FloatField(null=True, blank=True)
    fat_per_100g     = models.FloatField(null=True, blank=True)

    source    = models.CharField(max_length=50, blank=True)   # e.g. OFF
    source_id = models.CharField(max_length=64, blank=True)   # e.g. barcode/code
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ... existing imports ...

class Goal(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # current targets (you already have these)
    calories = models.IntegerField(default=2000)
    protein  = models.FloatField(default=150.0)
    carbs    = models.FloatField(default=250.0)
    fat      = models.FloatField(default=70.0)

    # NEW: coach inputs for recommendations
    OBJECTIVE_CHOICES = [
        ("lose", "Lose fat"),
        ("maintain", "Maintain"),
        ("gain", "Gain muscle"),
    ]
    objective = models.CharField(max_length=10, choices=OBJECTIVE_CHOICES, default="maintain")

    # desired pace (positive number). We’ll apply the sign from `objective`.
    # 0.25–0.75 kg/week is a sensible range.
    weekly_rate_kg = models.FloatField(default=0.25)

    # simple anthropometrics for TDEE (all optional; if missing we won’t suggest)
    SEX_CHOICES = [("M", "Male"), ("F", "Female")]
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True)
    age = models.PositiveIntegerField(blank=True, null=True)          # years
    height_cm = models.FloatField(blank=True, null=True)
    weight_kg = models.FloatField(blank=True, null=True)

    ACTIVITY_CHOICES = [
        ("sedentary",  "Sedentary"),
        ("light",      "Lightly active"),
        ("moderate",   "Moderately active"),
        ("active",     "Active"),
        ("very_active","Very active"),
    ]
    activity = models.CharField(max_length=12, choices=ACTIVITY_CHOICES, default="moderate")

    def __str__(self):
        return f"Goals for {self.user}"
