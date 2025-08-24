from django.contrib import admin
from django.urls import path, include
from tracker import views as tracker_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  
    path('', include('tracker.urls')),    
    path("signup/", tracker_views.signup, name="signup"),
                   
]
