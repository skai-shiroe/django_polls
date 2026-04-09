# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/polls/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False, label="Email (optionnel)")

    class Meta:
        model = User
        fields = ['username', 'email']
