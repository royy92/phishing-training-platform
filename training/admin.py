from django.contrib import admin
from .models import Scenario, UserResponse, Category

@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'message', 'category', 'difficulty', 'is_phishing')
    list_filter = ('category', 'difficulty', 'is_phishing')
    search_fields = ("title", "summary", "content")


@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = ("user", "scenario", "clicked", "reported", "timestamp")
    list_filter = ("clicked", "reported", "scenario")
    search_fields = ("user__username", "scenario__title")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)





