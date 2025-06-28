from django.db import models

class DatabaseProcessing(models.Model):
    source_bank = models.FileField(upload_to='upload/origem/')
    destination_bank = models.FileField(upload_to='upload/destino/')
    data_upload = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    final_destination_path = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'Processamento de {self.source_bank} para {self.destination_bank}'
