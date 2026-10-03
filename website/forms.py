from django import forms

from .models import Contact


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ("name", "email", "subject", "message")
        widgets = {
            "name": forms.TextInput(attrs={"maxlength": 100}),
            "email": forms.EmailInput(),
            "subject": forms.TextInput(attrs={"maxlength": 200}),
            "message": forms.Textarea(),
        }
