# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/polls/admin.py
from django.contrib import admin
from .models import Poll, Choice

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3

class PollAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ['question', 'is_active', 'created_at']

admin.site.register(Poll, PollAdmin)
admin.site.register(Choice)
