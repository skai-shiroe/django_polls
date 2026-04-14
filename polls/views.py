import json
import csv
from io import BytesIO
from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Avg, Count
from django.contrib.auth import login

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from .models import Poll, Choice, Vote
from .forms import RegisterForm, PollForm

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

def register(request):
    if request.user.is_authenticated:
        return redirect('polls:list')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Bienvenue {user.username} !")
        return redirect('polls:list')
    return render(request, 'registration/register.html', {'form': form})
@user_passes_test(lambda u: u.is_staff)
def poll_create(request):
    if request.method == 'POST':
        form = PollForm(request.POST)
        if form.is_valid():
            poll = form.save()
            
            # Handle choices if necessary
            if poll.poll_type in [Poll.SINGLE, Poll.MULTIPLE]:
                choice_texts = request.POST.getlist('choice_text')
                for text in choice_texts:
                    if text.strip():
                        Choice.objects.create(poll=poll, text=text.strip())
            
            messages.success(request, "Le sondage a été créé avec succès.")
            return redirect('polls:list')
    else:
        form = PollForm()
    
    return render(request, 'polls/poll_create.html', {'form': form, 'poll_types': Poll.POLL_TYPES})


# ─── Dashboard ────────────────────────────────────────────────────────────────

@user_passes_test(lambda u: u.is_staff)
def dashboard(request):
    polls = Poll.objects.annotate(vote_count=Count('vote')).order_by('-created_at')

    total_polls = polls.count()
    total_votes = Vote.objects.count()
    active_polls = polls.filter(is_active=True).count()

    # Répartition par type
    type_counts = {
        'single':   polls.filter(poll_type=Poll.SINGLE).count(),
        'multiple': polls.filter(poll_type=Poll.MULTIPLE).count(),
        'rating':   polls.filter(poll_type=Poll.RATING).count(),
        'text':     polls.filter(poll_type=Poll.TEXT).count(),
    }

    # Top 5 sondages les plus actifs
    top_polls = polls.order_by('-vote_count')[:5]

    context = {
        'polls': polls,
        'total_polls': total_polls,
        'total_votes': total_votes,
        'active_polls': active_polls,
        'type_counts': type_counts,
        'type_counts_json': json.dumps(type_counts),
        'top_polls': top_polls,
    }
    return render(request, 'polls/dashboard.html', context)


# ─── Export CSV ───────────────────────────────────────────────────────────────

@user_passes_test(lambda u: u.is_staff)
def export_poll_csv(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="sondage_{poll.id}.csv"'
    response.write('\ufeff')  # BOM pour Excel

    writer = csv.writer(response)

    if poll.poll_type in [Poll.SINGLE, Poll.MULTIPLE]:
        writer.writerow(['Choix', 'Nombre de votes', '% du total'])
        total = Vote.objects.filter(poll=poll, choice__isnull=False).count()
        for choice in poll.choices.all():
            count = choice.vote_count
            pct = round(count / total * 100, 1) if total > 0 else 0
            writer.writerow([choice.text, count, pct])

    elif poll.poll_type == Poll.RATING:
        writer.writerow(['Note', 'Nombre de votes'])
        counts = {item['score']: item['c'] for item in Vote.objects.filter(poll=poll).values('score').annotate(c=Count('score'))}
        for i in range(1, 6):
            writer.writerow([f'Note {i}', counts.get(i, 0)])
        avg = Vote.objects.filter(poll=poll).aggregate(avg=Avg('score'))['avg']
        writer.writerow([])
        writer.writerow(['Moyenne', round(avg, 2) if avg else 0])

    elif poll.poll_type == Poll.TEXT:
        writer.writerow(['Utilisateur', 'Réponse', 'Date'])
        for vote in Vote.objects.filter(poll=poll).select_related('user').order_by('-id'):
            writer.writerow([vote.user.username, vote.answer_text, ''])

    writer.writerow([])
    writer.writerow(['Sondage', poll.question])
    writer.writerow(['Type', poll.get_poll_type_display()])
    writer.writerow(['Exporté le', datetime.now().strftime('%d/%m/%Y %H:%M')])

    return response


# ─── Export PDF ───────────────────────────────────────────────────────────────

BRAND_COLOR   = colors.HexColor('#2563EB')
BRAND_DARK    = colors.HexColor('#1E40AF')
ACCENT_COLOR  = colors.HexColor('#7C3AED')
BG_LIGHT      = colors.HexColor('#EFF6FF')
GRAY_BORDER   = colors.HexColor('#E2E8F0')
TEXT_DARK     = colors.HexColor('#0F172A')
TEXT_MUTED    = colors.HexColor('#64748B')
WHITE         = colors.white


def _build_bar_chart(labels, values, max_val, width=390, bar_height=22, gap=8):
    """Génère un graphique à barres horizontal en SVG ReportLab."""
    label_w = 120
    bar_area = width - label_w - 50
    row_h = bar_height + gap
    total_h = len(labels) * row_h + 20
    d = Drawing(width, total_h)

    for i, (label, val) in enumerate(zip(labels, values)):
        y = total_h - (i + 1) * row_h + gap // 2

        # Fond gris
        bg = Rect(label_w, y, bar_area, bar_height, fillColor=colors.HexColor('#F1F5F9'), strokeColor=None)
        d.add(bg)

        # Barre colorée
        bar_w = (val / max_val * bar_area) if max_val > 0 else 0
        bar = Rect(label_w, y, bar_w, bar_height, fillColor=BRAND_COLOR, strokeColor=None, rx=4, ry=4)
        d.add(bar)

        # Label
        lbl = String(label_w - 6, y + 6, str(label), textAnchor='end',
                     fontSize=8, fillColor=TEXT_DARK)
        d.add(lbl)

        # Valeur à droite
        val_str = String(label_w + bar_w + 6, y + 6, str(val),
                         fontSize=8, fillColor=TEXT_MUTED)
        d.add(val_str)

    return d


@user_passes_test(lambda u: u.is_staff)
def export_poll_pdf(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title=f"Rapport – {poll.question}"
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    header_style = ParagraphStyle(
        'Header', fontSize=20, leading=26, textColor=WHITE,
        spaceAfter=0, alignment=TA_LEFT, fontName='Helvetica-Bold'
    )
    sub_style = ParagraphStyle(
        'Sub', fontSize=10, leading=14, textColor=colors.HexColor('#BFDBFE'),
        spaceAfter=0, alignment=TA_LEFT, fontName='Helvetica'
    )
    header_data = [
        [Paragraph("📊 Rapport de Sondage", header_style)],
        [Paragraph(f"Sondages Pro &nbsp;·&nbsp; {datetime.now().strftime('%d %B %Y')}", sub_style)],
    ]
    header_table = Table(header_data, colWidths=[17*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BRAND_COLOR),
        ('TOPPADDING',    (0, 0), (-1, 0), 18),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 18),
        ('LEFTPADDING',   (0, 0), (-1, -1), 20),
        ('ROUNDEDCORNERS', [8]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Méta-infos ──────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        'PollTitle', fontSize=16, leading=22, textColor=TEXT_DARK,
        fontName='Helvetica-Bold', spaceAfter=4
    )
    story.append(Paragraph(poll.question, title_style))

    badge_label  = poll.get_poll_type_display()
    status_label = "Actif" if poll.is_active else "Clôturé"
    status_color = "#22C55E" if poll.is_active else "#EF4444"

    meta_style = ParagraphStyle('Meta', fontSize=9, leading=13, textColor=TEXT_MUTED, fontName='Helvetica')
    story.append(Paragraph(
        f'Type : <b>{badge_label}</b> &nbsp;|&nbsp; Statut : '
        f'<font color="{status_color}"><b>{status_label}</b></font>',
        meta_style
    ))
    story.append(HRFlowable(width='100%', thickness=1, color=GRAY_BORDER, spaceAfter=12, spaceBefore=8))

    # ── KPIs ─────────────────────────────────────────────────────────────────
    kpi_label_style = ParagraphStyle('KpiL', fontSize=8, textColor=TEXT_MUTED, fontName='Helvetica', alignment=TA_CENTER)
    kpi_value_style = ParagraphStyle('KpiV', fontSize=22, textColor=BRAND_COLOR, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=28)

    ptype = poll.poll_type

    if ptype in [Poll.SINGLE, Poll.MULTIPLE]:
        total_voters = poll.vote_set.values('user').distinct().count()
        total_votes_c = Vote.objects.filter(poll=poll, choice__isnull=False).count()
        kpi_data = [
            [Paragraph("Votants uniques", kpi_label_style), Paragraph("Votes totaux", kpi_label_style)],
            [Paragraph(str(total_voters), kpi_value_style), Paragraph(str(total_votes_c), kpi_value_style)],
        ]
    elif ptype == Poll.RATING:
        total_v = poll.vote_set.count()
        avg = poll.vote_set.aggregate(avg=Avg('score'))['avg']
        avg_str = f"{round(avg, 1)}/5" if avg else "—"
        kpi_data = [
            [Paragraph("Réponses", kpi_label_style), Paragraph("Note moyenne", kpi_label_style)],
            [Paragraph(str(total_v), kpi_value_style), Paragraph(avg_str, kpi_value_style)],
        ]
    else:
        total_v = poll.vote_set.count()
        kpi_data = [
            [Paragraph("Réponses", kpi_label_style)],
            [Paragraph(str(total_v), kpi_value_style)],
        ]

    kpi_cols = [8.5*cm] * len(kpi_data[0])
    kpi_table = Table(kpi_data, colWidths=kpi_cols)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BG_LIGHT),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [BG_LIGHT]),
        ('TOPPADDING',    (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID',          (0, 0), (-1, -1), 1, GRAY_BORDER),
        ('ROUNDEDCORNERS', [6]),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Tableau de résultats ──────────────────────────────────────────────────
    section_style = ParagraphStyle(
        'Section', fontSize=13, textColor=TEXT_DARK, fontName='Helvetica-Bold',
        spaceBefore=10, spaceAfter=8
    )

    if ptype in [Poll.SINGLE, Poll.MULTIPLE]:
        story.append(Paragraph("Résultats par choix", section_style))

        total_v = Vote.objects.filter(poll=poll, choice__isnull=False).count()
        col_style  = ParagraphStyle('Col', fontSize=9, textColor=WHITE, fontName='Helvetica-Bold', alignment=TA_CENTER)
        cell_style = ParagraphStyle('Cell', fontSize=9, textColor=TEXT_DARK, fontName='Helvetica', alignment=TA_CENTER)
        lcell_style = ParagraphStyle('LCell', fontSize=9, textColor=TEXT_DARK, fontName='Helvetica', alignment=TA_LEFT)

        rows = [[
            Paragraph("Choix", col_style),
            Paragraph("Votes", col_style),
            Paragraph("Pourcentage", col_style),
        ]]
        labels, values = [], []
        for choice in poll.choices.all():
            count = choice.vote_count
            pct = round(count / total_v * 100, 1) if total_v > 0 else 0
            rows.append([
                Paragraph(choice.text, lcell_style),
                Paragraph(str(count), cell_style),
                Paragraph(f"{pct}%", cell_style),
            ])
            labels.append(choice.text[:20])
            values.append(count)

        col_widths = [9*cm, 3.5*cm, 4.5*cm]
        results_table = Table(rows, colWidths=col_widths)
        ts = TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), BRAND_COLOR),
            ('TEXTCOLOR',     (0, 0), (-1, 0), WHITE),
            ('TOPPADDING',    (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
            ('GRID',          (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ])
        results_table.setStyle(ts)
        story.append(results_table)
        story.append(Spacer(1, 0.4*cm))

        # Graphique à barres
        story.append(Paragraph("Visualisation", section_style))
        max_val = max(values) if values else 1
        chart = _build_bar_chart(labels, values, max_val)
        story.append(chart)

    elif ptype == Poll.RATING:
        story.append(Paragraph("Distribution des notes", section_style))
        counts_qs = Vote.objects.filter(poll=poll).values('score').annotate(c=Count('score'))
        counts_map = {item['score']: item['c'] for item in counts_qs}
        total_v = poll.vote_set.count()

        col_style  = ParagraphStyle('Col', fontSize=9, textColor=WHITE, fontName='Helvetica-Bold', alignment=TA_CENTER)
        cell_style = ParagraphStyle('Cell', fontSize=9, textColor=TEXT_DARK, fontName='Helvetica', alignment=TA_CENTER)

        rows = [[Paragraph("Note", col_style), Paragraph("Votes", col_style), Paragraph("Pourcentage", col_style)]]
        labels, values = [], []
        for i in range(1, 6):
            count = counts_map.get(i, 0)
            pct = round(count / total_v * 100, 1) if total_v > 0 else 0
            rows.append([
                Paragraph(f"⭐ {i}/5", cell_style),
                Paragraph(str(count), cell_style),
                Paragraph(f"{pct}%", cell_style),
            ])
            labels.append(f"{i}/5")
            values.append(count)

        col_widths = [5.5*cm, 5.5*cm, 6*cm]
        results_table = Table(rows, colWidths=col_widths)
        results_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), BRAND_COLOR),
            ('TOPPADDING',    (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
            ('GRID',          (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ]))
        story.append(results_table)
        story.append(Spacer(1, 0.4*cm))

        story.append(Paragraph("Visualisation", section_style))
        max_val = max(values) if values else 1
        story.append(_build_bar_chart(labels, values, max_val))

    elif ptype == Poll.TEXT:
        story.append(Paragraph("Réponses textuelles", section_style))
        col_style  = ParagraphStyle('Col', fontSize=9, textColor=WHITE, fontName='Helvetica-Bold')
        cell_style = ParagraphStyle('Cell', fontSize=8, textColor=TEXT_DARK, fontName='Helvetica')

        rows = [[Paragraph("Utilisateur", col_style), Paragraph("Réponse", col_style)]]
        for vote in Vote.objects.filter(poll=poll).select_related('user').order_by('-id')[:20]:
            rows.append([
                Paragraph(vote.user.username, cell_style),
                Paragraph(vote.answer_text or '—', cell_style),
            ])

        results_table = Table(rows, colWidths=[4*cm, 13*cm])
        results_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), BRAND_COLOR),
            ('TOPPADDING',    (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
            ('GRID',          (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ]))
        story.append(results_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width='100%', thickness=1, color=GRAY_BORDER))
    footer_style = ParagraphStyle('Footer', fontSize=8, textColor=TEXT_MUTED, alignment=TA_CENTER, fontName='Helvetica', spaceBefore=6)
    story.append(Paragraph(f"Sondages Pro &nbsp;·&nbsp; Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", footer_style))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_sondage_{poll.id}.pdf"'
    return response
