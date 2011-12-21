from django import forms
from django.forms.widgets import HiddenInput

class LoginForm(forms.Form):
    email = forms.EmailField(required=True, label='E-Mail')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    
class InvitationForm(forms.Form):
    requesting_customer = forms.CharField(max_length=50, required=True)