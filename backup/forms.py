from django import forms
from .models import DatabaseProcessing

class BackpForm(forms.ModelForm):
    class Meta:
        model = DatabaseProcessing
        fields = ['source_bank', 'destination_bank']
        widgets = {
            'source_bank': forms.FileInput(attrs={'accept': '.fdb'}),
            'destination_bank': forms.FileInput(attrs={'accept': '.fdb'}),
        }

    def clean_source_bank(self):
        """
        Valida se o arquivo de origem é um .fdb.
        """
        uploaded_file = self.cleaned_data.get('source_bank')
        if uploaded_file:
            # Pega o nome do arquivo
            filename = uploaded_file.name
            # Verifica se a extensão é '.fdb'
            if not filename.lower().endswith('.fdb'):
                raise forms.ValidationError('O arquivo de origem deve ser do tipo .FDB.')
        return uploaded_file

    def clean_destination_bank(self):
        """
        Valida se o arquivo de destino é um .fdb.
        """
        uploaded_file = self.cleaned_data.get('destination_bank')
        if uploaded_file:
            # Pega o nome do arquivo
            filename = uploaded_file.name
            # Verifica se a extensão é '.fdb'
            if not filename.lower().endswith('.fdb'):
                raise forms.ValidationError('O arquivo de destino deve ser do tipo .FDB.')
        return uploaded_file