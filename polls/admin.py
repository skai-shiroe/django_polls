from django.contrib import admin
from .models import Poll, Choice, Vote

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3

@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ['question', 'poll_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'poll_type', 'created_at']
    search_fields = ['question']
    inlines = [ChoiceInline]

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['text', 'poll', 'vote_count']
    list_filter = ['poll']

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['user', 'poll', 'choice', 'score']
    list_filter = ['poll', 'score']