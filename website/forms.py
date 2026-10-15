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

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Please provide your name.")
        return name

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if not message:
            raise forms.ValidationError("Please provide your message.")
        return message

    def clean_subject(self):
        return (self.cleaned_data.get("subject") or "").strip()

