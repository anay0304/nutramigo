from django.urls import include, path
from . import views

urlpatterns = [
    path('', views.meal_list, name='meal_list'),
    path('add/', views.add_meal, name='add_meal'),
    path('signup/', views.signup, name='signup'),
    path('edit/<int:pk>/', views.edit_meal, name='edit_meal'),
    path('delete/<int:pk>/', views.delete_meal, name='delete_meal'),
    path('logout-now/', views.logout_now, name='logout_now'),
    path('goals/', views.edit_goal, name='edit_goal'),
    path('export.csv', views.export_csv, name='export_csv'),
    path('copy-yesterday/', views.copy_yesterday, name='copy_yesterday'),
    path('api/food-search/', views.food_search, name='food_search'),
    path('api/quick-add/', views.quick_add_food, name='quick_add_food'),
    path('favorites/add/<int:pk>/', views.add_favorite_from_meal, name='add_favorite'),
    path('favorites/quick-add/<int:fav_id>/', views.quick_add_favorite, name='quick_add_favorite'),
    path('ai/', views.ai_assist, name='ai_assist'),
    path('ai/suggest/', views.ai_suggest_api, name='ai_suggest_api'),
    path("ai/log-plan/", views.ai_log_plan, name="ai_log_plan"),
    path("goals/apply-reco/", views.apply_calorie_reco, name="apply_calorie_reco"),
    path("goals/apply-macros/", views.apply_macro_reco, name="apply_macro_reco"),
    path('favorites/from-meal/<int:pk>/', views.add_favorite_from_meal, name='add_favorite_from_meal'),
    path("accounts/logout/", views.logout_now, name="logout"),  # must be before include()
    path("accounts/", include("django.contrib.auth.urls")),



    


    
]
