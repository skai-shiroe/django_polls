# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/polls/admin.py
from django.contrib import admin
from .models import Poll, Choice

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3

class PollAdmin(admin.ModelAdmin):
    list_display = ['question', 'poll_type', 'is_active', 'created_at']

    def get_inline_instances(self, request, obj=None):
        # Initialiser avec la configuration par défaut
        inlines = []
        # N'afficher ChoiceInline que si le sondage est single ou multiple
        # Si c'est en création (obj=None), on l'affiche par défaut.
        if not obj or obj.poll_type in [Poll.SINGLE, Poll.MULTIPLE]:
            inlines.append(ChoiceInline(self.model, self.admin_site))
        return inlines

admin.site.register(Poll, PollAdmin)
admin.site.register(Choice)
