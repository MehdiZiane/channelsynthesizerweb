from django.db import models

class Report(models.Model):
    generated_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='reports/')