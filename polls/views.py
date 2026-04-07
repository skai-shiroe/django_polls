# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/polls/views.py
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Poll, Choice, Vote

def poll_list(request):
    polls = Poll.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'polls/list.html', {'polls': polls})

@login_required
def vote(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id, is_active=True)
    
    if request.method == 'POST':
        try:
            selected_choice = poll.choices.get(pk=request.POST['choice'])
        except (KeyError, Choice.DoesNotExist):
            return render(request, 'polls/detail.html', {
                'poll': poll,
                'error_message': "Vous n'avez pas sélectionné de choix.",
            })
        else:
            # Check if user already voted
            if Vote.objects.filter(user=request.user, poll=poll).exists():
                messages.error(request, "Vous avez déjà voté pour ce sondage.")
                return redirect('polls:results', poll_id=poll.id)
            
            # Create vote
            Vote.objects.create(user=request.user, poll=poll, choice=selected_choice)
            
            # Broadcast update via WebSocket
            channel_layer = get_channel_layer()
            labels = [c.text for c in poll.choices.all()]
            votes = [c.vote_count for c in poll.choices.all()]
            
            async_to_sync(channel_layer.group_send)(
                f'poll_{poll.id}',
                {
                    'type': 'poll_message',
                    'data': {
                        'labels': labels,
                        'votes': votes
                    }
                }
            )
            
            messages.success(request, "Votre vote a été enregistré.")
            return redirect('polls:results', poll_id=poll.id)
            
    return render(request, 'polls/detail.html', {'poll': poll})

def results(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    return render(request, 'polls/results.html', {'poll': poll})
