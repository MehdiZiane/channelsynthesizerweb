import os
from django.db import models
import uuid


class UploadedExcel(models.Model):
    file = models.FileField(upload_to='excel/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return os.path.basename(self.file.name)
    
class ProcessingBatch(models.Model):
    batch_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    excel_file = models.ForeignKey(
        UploadedExcel,
        on_delete=models.CASCADE,
        related_name='batches',
        null=True,
        blank=True
    )

    def __str__(self):
        return str(self.batch_id)

class UploadedPDF(models.Model):
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    provider = models.CharField(max_length=50, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    processed = models.BooleanField(default=False)
    batch = models.ForeignKey(
        ProcessingBatch,
        on_delete=models.CASCADE,
        related_name='pdfs'
    )

class Channel(models.Model):
    name = models.CharField(max_length=200)
    provider_period = models.CharField(max_length=100)
    region_flanders = models.BooleanField()
    brussels = models.BooleanField()
    region_wallonia = models.BooleanField()
    german_community = models.BooleanField()
    basic_option = models.CharField(max_length=10)
    tv_radio = models.CharField(max_length=10)
    hd_sd = models.CharField(max_length=5)
    channel_group_level = models.CharField(max_length=200)



    
