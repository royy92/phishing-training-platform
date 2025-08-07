from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Scenario(models.Model):
    title = models.CharField(max_length=100)
    email_subject = models.CharField(max_length=200)
    email_body = models.TextField()
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
