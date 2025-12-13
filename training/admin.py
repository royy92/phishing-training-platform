from django.contrib import admin
from .models import Scenario, UserResponse, Category
from .models import ScenarioStep

@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'phase', 'difficulty', 'is_phishing')
    list_filter = ('category', 'phase', 'difficulty', 'is_phishing')
    search_fields = ("title", "message", "content")


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


@admin.register(ScenarioStep)
class ScenarioStepAdmin(admin.ModelAdmin):
    verbose_name = "Scenario Step"
    verbose_name_plural = "Scenario Steps"
    list_display = ("scenario", "order", "step_type", "title")
    list_filter = ("scenario", "step_type")
    search_fields = ("title", "body")



