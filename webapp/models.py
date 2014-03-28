from django.db import models

class EarlySignup(models.Model):
	email = models.EmailField(blank=False, null=False, unique=True)
	signup_datetime = models.DateTimeField(auto_now_add=True)