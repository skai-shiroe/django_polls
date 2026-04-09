# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/polls/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Poll

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False, label="Email (optionnel)")

    class Meta:
        model = User
        fields = ['username', 'email']

class PollForm(forms.ModelForm):
    class Meta:
        model = Poll
        fields = ['question', 'poll_type']
        labels = {
            'question': 'Votre question',
            'poll_type': 'Type de sondage'
        }
        widgets = {
            'question': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border-gray-200 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 transition shadow-sm',
                'placeholder': 'De quoi voulez-vous discuter ?'
            }),
            'poll_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border-gray-200 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 transition shadow-sm',
                'x-model': 'pollType'
            }),
        }

