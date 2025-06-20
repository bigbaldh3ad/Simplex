# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    calculations_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} Profile"
