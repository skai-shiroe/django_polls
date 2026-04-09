# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/polls/models.py
from django.db import models
from django.contrib.auth.models import User

class Poll(models.Model):
    SINGLE   = 'single'
    MULTIPLE = 'multiple'
    RATING   = 'rating'
    TEXT     = 'text'
    POLL_TYPES = [
        (SINGLE,   'Choix unique'),
        (MULTIPLE, 'Choix multiple'),
        (RATING,   'Échelle 1 à 5'),
        (TEXT,     'Texte libre'),
    ]
    poll_type = models.CharField(max_length=20, choices=POLL_TYPES, default=SINGLE)
    
    question = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question

class Choice(models.Model):
    poll = models.ForeignKey(Poll, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)

    @property
    def vote_count(self):
        return self.votes.count()

    def __str__(self):
        return self.text

class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, related_name='votes', on_delete=models.CASCADE, null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    answer_text = models.TextField(null=True, blank=True)
