from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Scenario(models.Model):
    title = models.CharField(max_length=200)
    title_ar = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField()
    message_ar = models.TextField(blank=True, null=True)
    is_phishing = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class UserResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    clicked = models.BooleanField(default=False)
    reported = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
