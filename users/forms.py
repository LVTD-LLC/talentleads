from allauth.account.forms import LoginForm, SignupForm
from django import forms
from django.forms import Form, ModelForm

from utils.forms import DivErrorList

from .models import OutreachTemplate


class CustomSignUpForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super(CustomSignUpForm, self).__init__(*args, **kwargs)
        self.error_class = DivErrorList


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super(CustomLoginForm, self).__init__(*args, **kwargs)
        self.error_class = DivErrorList


class SupportForm(Form):
    # user = forms.CharField()
    message = forms.CharField(widget=forms.Textarea)

    def __init__(self, current_user=None, *args, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["current_user"] = self.current_user
        return cleaned_data


class CreateOutreachTemplateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(CreateOutreachTemplateForm, self).__init__(*args, **kwargs)

    class Meta:
        model = OutreachTemplate
        fields = [
            "title",
            "subject_line",
            "text",
            "cc_s",
        ]
        labels = {
            "cc_s": "CCs",
            "text": "Message",
        }


class UpdateOutreachTemplateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(UpdateOutreachTemplateForm, self).__init__(*args, **kwargs)

    class Meta:
        model = OutreachTemplate
        fields = [
            "title",
            "subject_line",
            "text",
            "cc_s",
        ]
        labels = {
            "cc_s": "CCs",
            "text": "Message",
        }
