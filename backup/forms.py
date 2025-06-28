from django import forms
from .models import DatabaseProcessing

class BackpForm(forms.ModelForm):
    class Meta:
        model = DatabaseProcessing
        fields = ['source_bank', 'destination_bank']