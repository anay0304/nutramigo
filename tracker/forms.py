from django import forms
from .models import Meal, Goal


class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ["name", "date", "grams", "calories", "protein", "carbs", "fat"]
        widgets = {
            "name":     forms.TextInput(attrs={"class":"form-control"}),
            "date":     forms.DateInput(attrs={"type":"date","class":"form-control"}),
            "grams":    forms.NumberInput(attrs={"class":"form-control","min":0,"step":"1"}),
            "calories": forms.NumberInput(attrs={"class":"form-control","min":0,"step":"1"}),
            "protein":  forms.NumberInput(attrs={"class":"form-control","min":0,"step":"0.1"}),
            "carbs":    forms.NumberInput(attrs={"class":"form-control","min":0,"step":"0.1"}),
            "fat":      forms.NumberInput(attrs={"class":"form-control","min":0,"step":"0.1"}),
        }


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = [
            "calories","protein","carbs","fat",
            "objective","weekly_rate_kg",
            "sex","age","height_cm","weight_kg","activity",
        ]
        help_texts = {
            "weekly_rate_kg": "Positive number. We’ll apply deficit/surplus based on objective.",
        }
