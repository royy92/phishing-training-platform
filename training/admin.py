from django.contrib import admin
from .models import Scenario, UserResponse

@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'title_ar', 'message', 'message_ar')


@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = ("user", "scenario", "clicked", "reported", "timestamp")
    list_filter = ("clicked", "reported", "scenario")
    search_fields = ("user__username", "scenario__title")

