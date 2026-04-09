# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/polls/views.py
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models import Avg, Count
from .models import Poll, Choice, Vote

def poll_list(request):
    polls = Poll.objects.filter(is_active=True).order_by('-created_at')
    user_voted_polls = []
    if request.user.is_authenticated:
        user_voted_polls = Vote.objects.filter(user=request.user).values_list('poll_id', flat=True).distinct()
        
    return render(request, 'polls/list.html', {
        'polls': polls,
        'user_voted_polls': list(user_voted_polls)
    })

@login_required
def vote(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id, is_active=True)
    
    # Verification au niveau de la vue (remplace unique_together)
    if Vote.objects.filter(user=request.user, poll=poll).exists():
        messages.error(request, "Vous avez déjà voté pour ce sondage.")
        return redirect('polls:results', poll_id=poll.id)
            
    if request.method == 'POST':
        ptype = poll.poll_type
        saved_votes = False
        
        if ptype == Poll.SINGLE:
            choice_id = request.POST.get('choice')
            if not choice_id:
                return render(request, 'polls/detail.html', {'poll': poll, 'error_message': "Vous n'avez pas sélectionné de choix."})
            try:
                selected_choice = poll.choices.get(pk=choice_id)
                Vote.objects.create(user=request.user, poll=poll, choice=selected_choice)
                saved_votes = True
            except Choice.DoesNotExist:
                return render(request, 'polls/detail.html', {'poll': poll, 'error_message': "Choix invalide."})
                
        elif ptype == Poll.MULTIPLE:
            choice_ids = request.POST.getlist('choices')
            if not choice_ids:
                return render(request, 'polls/detail.html', {'poll': poll, 'error_message': "Sélectionnez au moins un choix."})
            valid_choices = poll.choices.filter(pk__in=choice_ids)
            if valid_choices.count() == 0:
                return render(request, 'polls/detail.html', {'poll': poll, 'error_message': "Choix invalides."})
            for c in valid_choices:
                Vote.objects.create(user=request.user, poll=poll, choice=c)
            saved_votes = True
            
        elif ptype == Poll.RATING:
            score = request.POST.get('score')
            if not score or not score.isdigit() or not (1 <= int(score) <= 5):
                return render(request, 'polls/detail.html', {'poll': poll, 'error_message': "Veuillez attribuer une note entre 1 et 5."})
            Vote.objects.create(user=request.user, poll=poll, score=int(score))
            saved_votes = True
            
        elif ptype == Poll.TEXT:
            answer_text = request.POST.get('answer_text', '').strip()
            if not answer_text:
                return render(request, 'polls/detail.html', {'poll': poll, 'error_message': "Le texte de réponse ne peut être vide."})
            Vote.objects.create(user=request.user, poll=poll, answer_text=answer_text)
            saved_votes = True
            
        if saved_votes:
            # Broadcast updates via WebSocket
            channel_layer = get_channel_layer()
            ws_data = {}
            if ptype in [Poll.SINGLE, Poll.MULTIPLE]:
                ws_data = {
                    'labels': [c.text for c in poll.choices.all()],
                    'votes': [c.vote_count for c in poll.choices.all()],
                    'total': poll.vote_set.values('user').distinct().count()
                }
            elif ptype == Poll.RATING:
                agg = poll.vote_set.aggregate(avg=Avg('score'))
                counts = list(poll.vote_set.values('score').annotate(c=Count('score')))
                score_dict = {str(item['score']): item['c'] for item in counts}
                ws_data = {
                    'average': round(agg['avg'], 1) if agg['avg'] else 0,
                    'scores': [score_dict.get(str(i), 0) for i in range(1, 6)],
                    'total': poll.vote_set.count()
                }
            elif ptype == Poll.TEXT:
                recent_votes = poll.vote_set.order_by('-id')[:10]
                ws_data = {
                    'texts': [v.answer_text for v in recent_votes],
                    'total': poll.vote_set.count()
                }
            
            async_to_sync(channel_layer.group_send)(
                f'poll_{poll.id}',
                {
                    'type': 'poll_message',
                    'data': ws_data
                }
            )
            
            messages.success(request, "Votre vote a été enregistré.")
            return redirect('polls:results', poll_id=poll.id)
            
    return render(request, 'polls/detail.html', {'poll': poll})

def results(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    
    context = {'poll': poll, 'total_votes': 0}
    ptype = poll.poll_type
    
    if ptype in [Poll.SINGLE, Poll.MULTIPLE]:
        context['total_votes'] = poll.vote_set.values('user').distinct().count()
    elif ptype == Poll.RATING:
        context['total_votes'] = poll.vote_set.count()
        agg = poll.vote_set.aggregate(avg=Avg('score'))
        context['average_score'] = round(agg['avg'], 1) if agg['avg'] else 0
    elif ptype == Poll.TEXT:
        context['total_votes'] = poll.vote_set.count()
        context['recent_texts'] = poll.vote_set.order_by('-id')[:10]
        
    return render(request, 'polls/results.html', context)
