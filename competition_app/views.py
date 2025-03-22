from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.http import HttpResponseNotAllowed
from .models import Competition, Judge, JudgeAssignment, Round, Score, Participant
from .forms import JudgeForm, CustomUserCreationForm
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, FileResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from decimal import Decimal, ROUND_HALF_UP
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable, PageBreak
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os
from django.conf import settings
from datetime import datetime
from django.contrib.auth.models import User
from .models import (
    Competition, Participant, Judge, CompetitionResult, 
    JudgeAssignment, ParticipantCompetition, Score, Round, Criterion
)

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

def dashboard(request):
    context = {
        'active_competitions': Competition.objects.filter(status='ACTIVE').count(),
        'total_participants': Participant.objects.count(),
        'total_judges': Judge.objects.count(),
        'recent_competitions': Competition.objects.all().order_by('-id')[:5],
        'upcoming_events': Competition.objects.filter(status='DRAFT').order_by('start_date')[:3],
    }
    
    # Add additional competition statistics
    for competition in context['recent_competitions']:
        competition.participant_count = competition.participants.count()
        competition.rounds_count = competition.rounds.count()
        
    # Add judge assignment counts
    for judge in Judge.objects.all():
        judge.scores_count = judge.scores.count()
        
    return render(request, 'dashboard.html', context)


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Competition, Round, Participant, Score, Criterion



from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from .models import Judge

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Check if user is a judge
            if hasattr(user, 'judge'):
                return redirect('judge_dashboard')
            # Check if user is admin
            elif user.is_superuser:
                return redirect('dashboard')
        else:
            # Authentication failed
            return render(request, 'auth/login.html', {
                'error_message': 'Invalid username or password. Please try again.',
                'username': username  # Keep the username for better UX
            })
                
    return render(request, 'auth/login.html')
def register_view(request):
    if request.method == 'POST':
        with transaction.atomic():
            # Create the User instance
            user = User.objects.create_user(
                username=request.POST['username'],
                email=request.POST['email'],
                password=request.POST['password1']
            )
            
            # Set the full name
            user.first_name = request.POST['full_name'].split()[0]
            user.last_name = ' '.join(request.POST['full_name'].split()[1:])
            user.save()
            
            # Create the associated Judge instance
            judge = Judge.objects.create(
                user=user,
                phone=request.POST['phone'],
                status='ACTIVE'
            )
            
            return redirect('login')
            
    return render(request, 'auth/register.html')


from django.shortcuts import render, redirect
from .models import Competition, Round
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def create_competition(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Create the competition
                competition = Competition.objects.create(
                    name=request.POST.get('name'),
                    description=request.POST.get('description'),
                    start_date=request.POST.get('start_date'),
                    end_date=request.POST.get('end_date'),
                    status=request.POST.get('status'),
                    created_by=request.user
                )

                # Get round data from form
                round_names = request.POST.getlist('round_names[]')
                round_orders = request.POST.getlist('round_orders[]')
                round_weights = request.POST.getlist('round_weights[]')
                round_statuses = request.POST.getlist('round_statuses[]')

                # Create each round
                for i in range(len(round_names)):
                    if round_names[i].strip():  # Only create if name is not empty
                        round_obj = Round.objects.create(
                            competition=competition,
                            name=round_names[i],
                            order=int(round_orders[i]) if round_orders[i] else i + 1,
                            weight_percentage=float(round_weights[i]) if round_weights[i] else 100,
                            status=round_statuses[i] if round_statuses[i] else 'PENDING'
                        )

                        # Get criteria for this specific round
                        prefix = f'criterion_names_{i+1}[]'
                        criterion_names = request.POST.getlist(prefix)
                        desc_prefix = f'criterion_descriptions_{i+1}[]'
                        criterion_descriptions = request.POST.getlist(desc_prefix)
                        score_prefix = f'criterion_max_scores_{i+1}[]'
                        criterion_max_scores = request.POST.getlist(score_prefix)

                        # Create criteria for this round
                        for j in range(len(criterion_names)):
                            if criterion_names[j].strip():  # Only create if name is not empty
                                Criterion.objects.create(
                                    round=round_obj,
                                    name=criterion_names[j],
                                    description=criterion_descriptions[j] if j < len(criterion_descriptions) else '',
                                    max_score=float(criterion_max_scores[j]) if j < len(criterion_max_scores) and criterion_max_scores[j] else 100
                                )

            messages.success(request, 'Competition created successfully!')
            return redirect('competition_list')
        except Exception as e:
            messages.error(request, f'Error creating competition: {str(e)}')
            return render(request, 'competition_app/create_competition.html')

    return render(request, 'competition_app/create_competition.html')

@login_required
def competition_list(request):
    competitions = Competition.objects.all().order_by('-id')
    return render(request, 'competition_app/competition_list.html', {'competitions': competitions})

@login_required
def competition_detail(request, competition_id):
    competition = get_object_or_404(Competition, id=competition_id)
    rounds = competition.rounds.all().prefetch_related('criteria').order_by('order')
    
    context = {
        'competition': competition,
        'rounds': rounds,
        'total_criteria': sum(round.criteria.count() for round in rounds),
        'total_max_score': sum(
            criterion.max_score 
            for round in rounds 
            for criterion in round.criteria.all()
        )
    }
    return render(request, 'competition_app/competition_detail.html', context)

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Round, Participant, Criterion, Score, Judge
import json

@login_required
def scoring_panel(request, round_id):
    round_obj = get_object_or_404(Round, id=round_id)
    judge = get_object_or_404(Judge, user=request.user)
    
    # Check if judge is assigned to this competition and round
    assignment = JudgeAssignment.objects.filter(
        judge=judge,
        competition=round_obj.competition,
        status='ACTIVE'
    ).exists()
    
    if not assignment:
        messages.error(request, 'You are not assigned to judge this round.')
        return redirect('judge_dashboard')
    
    # Check if round status is ongoing
    if round_obj.status != 'ONGOING':
        messages.warning(request, 'Scoring is only available for ongoing rounds.')
        return redirect('judge_dashboard')
    
    if request.method == 'POST':
        with transaction.atomic():
            participant_id = request.POST.get('participant_id')
            participant = get_object_or_404(Participant, id=participant_id)
            
            # Process scores for each criterion
            for criterion in round_obj.criteria.all():
                score_value = float(request.POST.get(f'score_{participant_id}_{criterion.id}', 0))
                remarks = request.POST.get(f'remarks_{participant_id}_{criterion.id}', '')
                
                Score.objects.update_or_create(
                    participant=participant,
                    criterion=criterion,
                    judge=judge,
                    defaults={
                        'score': score_value,
                        'remarks': remarks,
                        'status': 'SUBMITTED'
                    }
                )
            
            # Calculate total score from all judges
            total_score = calculate_participant_total_score(participant, round_obj)
            
            # Update or create CompetitionResult
            CompetitionResult.objects.update_or_create(
                competition=round_obj.competition,
                participant=participant,
                round=round_obj,
                defaults={
                    'total_score': total_score,
                    'rank': 0  # Will be updated in calculate_rankings
                }
            )
            
            calculate_rankings(round_obj)
            messages.success(request, 'Scores submitted successfully!')

            # For regular form submission, redirect back to the scoring panel
            return redirect('scoring_panel', round_id=round_id)
    
    # Get submitted scores for this judge and round
    submitted_scores = Score.objects.filter(
        judge=judge,
        criterion__round=round_obj,
        status='SUBMITTED'
    ).values_list('participant_id', flat=True).distinct()
    
    participants = Participant.objects.filter(
        participantcompetition__competition=round_obj.competition
    )
    
    # Mark which participants have submitted scores
    for participant in participants:
        participant.scores_submitted = participant.id in submitted_scores

    criteria = round_obj.criteria.all()
    
    # Get existing scores
    existing_scores = Score.objects.filter(
        judge=judge,
        criterion__round=round_obj
    ).select_related('participant', 'criterion')
    
    # Organize existing scores and remarks for easy lookup
    score_lookup = {}
    remarks_lookup = {}
    for score in existing_scores:
        if score.participant_id not in score_lookup:
            score_lookup[score.participant_id] = {}
            remarks_lookup[score.participant_id] = {}
        score_lookup[score.participant_id][score.criterion_id] = score.score
        remarks_lookup[score.participant_id][score.criterion_id] = score.remarks
    
    # Get assigned active competitions for sidebar
    assigned_competitions = Competition.objects.filter(
        status='ACTIVE',
        judge_assignments__judge=judge,
        judge_assignments__status='ACTIVE'
    ).prefetch_related('rounds')
    
    competition_data = []
    for competition in assigned_competitions:
        assigned_rounds = competition.rounds.filter(
            judge_assignments__judge=judge
        )
        
        competition_data.append({
            'competition': competition,
            'rounds': assigned_rounds,
            'participant_count': competition.participants.count(),
        })
    
    context = {
        'round': round_obj,
        'participants': participants,
        'criteria': criteria,
        'existing_scores': score_lookup,
        'existing_remarks': remarks_lookup,
        'judge': judge,
        'total_max_score': sum(criterion.max_score for criterion in criteria),
        'competition_data': competition_data  # Add competition data for sidebar
    }
    
    return render(request, 'competition_app/judge/scoring_panel.html', context)

@login_required
def submit_scores(request, round_id):
    """Handle submission of scores for all participants in a round."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)
    
    try:
        round_obj = get_object_or_404(Round, id=round_id)
        judge = get_object_or_404(Judge, user=request.user)
        
        # Check if round is ongoing
        if round_obj.status != 'ONGOING':
            return JsonResponse({
                'status': 'error',
                'message': 'Scoring is not available for this round'
            }, status=400)

        with transaction.atomic():
            scores_updated = False
            # Process each score input
            for key, value in request.POST.items():
                if not key.startswith('score_'):
                    continue
                    
                parts = key.split('_')
                if len(parts) != 3:
                    continue
                
                try:
                    participant_id = int(parts[1])
                    criterion_id = int(parts[2])
                    score_value = Decimal(value)
                    
                    participant = Participant.objects.get(id=participant_id)
                    criterion = Criterion.objects.get(id=criterion_id)
                    
                    # Validate score
                    if score_value < 0 or score_value > criterion.max_score:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Invalid score for {criterion.name}: {score_value}'
                        }, status=400)
                    
                    # Update or create score
                    Score.objects.update_or_create(
                        participant=participant,
                        criterion=criterion,
                        judge=judge,
                        round=round_obj,
                        defaults={
                            'score': score_value,
                            'status': 'SUBMITTED'
                        }
                    )
                    scores_updated = True
                    
                except (ValueError, Participant.DoesNotExist, Criterion.DoesNotExist) as e:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Error processing score: {str(e)}'
                    }, status=400)
            
            if not scores_updated:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No valid scores were submitted'
                }, status=400)
            
            # Update competition results and rankings
            participants = Participant.objects.filter(
                id__in=[int(k.split('_')[1]) for k in request.POST.keys() if k.startswith('score_')]
            ).distinct()
            
            for participant in participants:
                total_score = calculate_participant_total_score(participant, round_obj)
                CompetitionResult.objects.update_or_create(
                    competition=round_obj.competition,
                    participant=participant,
                    round=round_obj,
                    defaults={
                        'total_score': total_score,
                        'rank': 0  # Will be updated in calculate_rankings
                    }
                )
            
            # Recalculate rankings
            calculate_rankings(round_obj)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Scores submitted successfully'
            })
            
    except Exception as e:
        import traceback
        print(f"Error in submit_scores: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while submitting scores'
        }, status=500)

def update_participant_rankings(round):
    participants = round.competition.participants.all()
    
    for participant in participants:
        # Calculate total score for the participant in this round
        total_score = Score.objects.filter(
            participant=participant,
            criterion__in=round.criteria.all(),
            status='SUBMITTED'
        ).aggregate(total=models.Sum('score'))['total'] or 0.0
        
        # Update or create competition result
        CompetitionResult.objects.update_or_create(
            participant=participant,
            round=round,
            defaults={'total_score': total_score}
        )

def calculate_participant_total_score(participant, round_obj, include_draft=True):
    """Calculate total average score for a participant in a round by averaging scores from all judges for each criterion"""
    total_score = Decimal('0.00')
    criteria = round_obj.criteria.all()
    
    for criterion in criteria:
        scores_query = Score.objects.filter(
            participant=participant,
            criterion=criterion
        )
        
        if not include_draft:
            scores_query = scores_query.filter(status='SUBMITTED')
            
        criterion_scores = scores_query.values_list('score', flat=True)
        
        if criterion_scores:
            # Calculate average score for this criterion
            criterion_avg = Decimal(sum(criterion_scores)) / Decimal(len(criterion_scores))
            # Apply criterion weight if any
            criterion_weight = Decimal(criterion.weight_percentage) / Decimal('100.00') if hasattr(criterion, 'weight_percentage') else Decimal('1.00')
            total_score += criterion_avg * criterion_weight
    
    # Round to 2 decimal places
    return total_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

@login_required
def get_scoring_statistics(request, round_id):
    round_obj = get_object_or_404(Round, id=round_id)
    judge = get_object_or_404(Judge, user=request.user)
    
    stats = Score.objects.filter(
        judge=judge,
        criterion__round=round_obj
    ).aggregate(
        total_scores=Count('id'),
        avg_score=Avg('score'),
        submitted_scores=Count('id', filter=Q(status='SUBMITTED')),
        draft_scores=Count('id', filter=Q(status='DRAFT'))
    )
    
    return JsonResponse(stats)

@login_required
def submit_batch_scores(request, round_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
    
    try:
        round_obj = get_object_or_404(Round, id=round_id)
        
        # Check if round is ongoing
        if round_obj.status != 'ONGOING':
            return JsonResponse({
                'status': 'error',
                'message': 'Scoring is not available for this round'
            }, status=400)
        
        # Check if user is a judge assigned to this round
        if not hasattr(request.user, 'judge'):
            return JsonResponse({
                'status': 'error',
                'message': 'Only judges can submit scores'
            }, status=403)
            
        judge = request.user.judge
        if not round_obj.judge_assignments.filter(judge=judge, status='ACTIVE').exists():
            return JsonResponse({
                'status': 'error',
                'message': 'You are not assigned to judge this round'
            }, status=403)
        
        # Get scores from request
        try:
            scores_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid score data format'
            }, status=400)
        
        # Validate scores
        errors = []
        for score_item in scores_data:
            try:
                participant_id = score_item.get('participant_id')
                criterion_id = score_item.get('criterion_id')
                score_value = score_item.get('score')
                
                if not all([participant_id, criterion_id, score_value is not None]):
                    errors.append(f'Missing required fields for score')
                    continue
                    
                participant = Participant.objects.filter(id=participant_id).first()
                criterion = Criterion.objects.filter(id=criterion_id, round=round_obj).first()
                
                if not participant:
                    errors.append(f'Invalid participant ID: {participant_id}')
                    continue
                    
                if not criterion:
                    errors.append(f'Invalid criterion ID: {criterion_id}')
                    continue
                
                if not isinstance(score_value, (int, float)) or score_value < 0 or score_value > criterion.max_score:
                    errors.append(f'Invalid score value for {participant.name}, {criterion.name}: {score_value}')
                    continue
                    
            except Exception as e:
                errors.append(f'Error validating score: {str(e)}')
        
        if errors:
            return JsonResponse({
                'status': 'error',
                'message': 'Score validation failed',
                'errors': errors
            }, status=400)
        
        # Save scores in transaction
        with transaction.atomic():
            for score_item in scores_data:
                participant_id = score_item['participant_id']
                criterion_id = score_item['criterion_id']
                score_value = Decimal(str(score_item['score']))
                
                score, created = Score.objects.update_or_create(
                    participant_id=participant_id,
                    criterion_id=criterion_id,
                    judge=judge,
                    defaults={
                        'score': score_value,
                        'status': 'SUBMITTED'
                    }
                )
            
            # Update rankings
            calculate_rankings(round_obj)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Scores submitted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=500)

def calculate_rankings(round_obj):
    """Calculate and update rankings for a round"""
    with transaction.atomic():
        # First, get all participants with submitted scores
        participants = Participant.objects.filter(
            scores__criterion__round=round_obj,
            scores__status='SUBMITTED'
        ).distinct()
        
        # Calculate and store scores
        results = []
        for participant in participants:
            total_score = calculate_participant_total_score(participant, round_obj, include_draft=False)
            results.append({
                'participant': participant,
                'total_score': total_score
            })
        
        # Sort by total score in descending order
        results.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Assign ranks, handling ties
        current_rank = 1
        previous_score = None
        rank_count = 0
        
        for result in results:
            if previous_score != result['total_score']:
                current_rank = rank_count + 1
            
            CompetitionResult.objects.update_or_create(
                competition=round_obj.competition,
                participant=result['participant'],
                round=round_obj,
                defaults={
                    'total_score': result['total_score'],
                    'rank': current_rank
                }
            )
            
            previous_score = result['total_score']
            rank_count += 1

@login_required
def competition_results_detail(request, competition_id):
    from decimal import Decimal
    from collections import OrderedDict, defaultdict
    
    # Get tie-breaking preference from URL
    break_ties = request.GET.get('break_ties', '1') == '1'
    
    competition = get_object_or_404(Competition.objects.prefetch_related(
        'rounds',
        'rounds__criteria',
        'rounds__results',
        'rounds__results__participant',
        'participants',
        'judge_assignments',
        'judge_assignments__judge'
    ), id=competition_id)

    # Calculate detailed statistics for each round
    rounds = list(competition.rounds.all().order_by('order'))
    final_round = rounds[-1] if rounds else None
    
    # Store round scores for later tie-breaking
    participant_round_scores = defaultdict(dict)
    participant_first_places = defaultdict(int)
    
    for round_obj in rounds:
        # Use a list to store scores for sorting
        scores_list = []
        for participant in competition.participants.all():
            total_score = calculate_participant_total_score(participant, round_obj, include_draft=False)
            
            # Store round score for tie-breaking
            participant_round_scores[participant.id][round_obj.id] = total_score
            
            # Get individual criterion scores
            scores = Score.objects.filter(
                participant=participant,
                criterion__round=round_obj,
                status='SUBMITTED'
            ).select_related('criterion', 'judge', 'judge__user')
            
            criterion_scores = {}
            judge_scores = {}
            judge_count = 0
            
            # Group scores by judge
            for score in scores:
                judge_id = score.judge.id
                if judge_id not in judge_scores:
                    judge_scores[judge_id] = {
                        'judge_name': score.judge.user.get_full_name() or score.judge.user.username,
                        'scores': {}
                    }
                    judge_count += 1
                judge_scores[judge_id]['scores'][score.criterion_id] = score.score
                
                # Sum up scores for averaging later
                if score.criterion_id not in criterion_scores:
                    criterion_scores[score.criterion_id] = Decimal('0')
                criterion_scores[score.criterion_id] += Decimal(str(score.score))
            
            # Calculate averages for each criterion
            if judge_count > 0:
                for criterion_id in criterion_scores:
                    criterion_scores[criterion_id] /= Decimal(str(judge_count))
            
            scores_list.append({
                'participant_id': participant.id,
                'total_score': total_score,
                'criterion_scores': criterion_scores,
                'judge_scores': judge_scores
            })
        
        # Sort scores by total_score in descending order
        scores_list.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Track first place finishes for tie-breaking
        if scores_list:
            top_score = scores_list[0]['total_score']
            for score_data in scores_list:
                if score_data['total_score'] == top_score:
                    participant_first_places[score_data['participant_id']] += 1
        
        # Convert to OrderedDict and add rank information
        round_obj.participant_scores = OrderedDict()
        
        # First pass: identify ties
        score_counts = {}
        score_to_rank = {}
        current_rank = 1
        
        # Count occurrences of each score
        for score_data in scores_list:
            score = score_data['total_score']
            if score in score_counts:
                score_counts[score] += 1
            else:
                score_counts[score] = 1
                score_to_rank[score] = current_rank
            current_rank += 1
        
        # Second pass: create participant scores with tie information
        for i, score_data in enumerate(scores_list):
            score = score_data['total_score']
            is_tied = score_counts[score] > 1  # True if this score appears more than once
            
            # Use the first rank for all tied scores
            rank = score_to_rank[score]
            
            round_obj.participant_scores[score_data['participant_id']] = {
                'total': score,
                'scores': score_data['criterion_scores'],
                'judge_scores': score_data['judge_scores'],
                'rank': rank,
                'tied': is_tied
            }

    # Calculate final scores for participants with tie-breaking data
    participants = competition.participants.all()
    participant_final_scores = []
    
    for participant in participants:
        total_score = 0
        count = 0
        for round_obj in rounds:
            result = CompetitionResult.objects.filter(
                round=round_obj,
                participant=participant
            ).first()
            if result:
                total_score += result.total_score * (round_obj.weight_percentage / 100)
                count += 1
        
        final_score = total_score / count if count > 0 else 0
        
        # Get final round score for tie-breaking
        final_round_score = Decimal('0')
        if final_round and participant.id in participant_round_scores:
            final_round_score = participant_round_scores[participant.id].get(final_round.id, 0)
        
        # Get highest round score for tie-breaking
        highest_round_score = max(participant_round_scores[participant.id].values()) if participant_round_scores[participant.id] else 0
        
        # Count first place finishes
        first_places = participant_first_places[participant.id]
        
        participant_final_scores.append({
            'participant': participant,
            'final_score': final_score,
            'final_round_score': final_round_score,
            'highest_round_score': highest_round_score,
            'first_places': first_places,
            'name': participant.name  # For alphabetical tie-breaking
        })
    
    # Sort participants based on tie-breaking preference
    if break_ties:
        # Use multi-level tie-breaking
        sorted_participants = sorted(
            participant_final_scores,
            key=lambda p: (
                p['final_score'],                # Primary: Final score
                p['final_round_score'],          # Tiebreaker 1: Final round score
                p['first_places'],               # Tiebreaker 2: Number of first places
                p['highest_round_score'],        # Tiebreaker 3: Highest round score
                p['name'].lower()                # Tiebreaker 4: Alphabetical by name
            ),
            reverse=True  # Descending order
        )
        
        # Assign ranks (no ties)
        for i, p_data in enumerate(sorted_participants):
            participant = p_data['participant']
            participant.final_score = p_data['final_score']
            participant.rank = i + 1
            participant.is_tied = False
            
            # Add tie-breaking info
            participant.tie_breakers = {
                'final_round': p_data['final_round_score'],
                'first_places': p_data['first_places'],
                'highest_score': p_data['highest_round_score']
            }
    else:
        # Sort only by final score, allowing ties
        sorted_participants = sorted(
            participant_final_scores,
            key=lambda p: p['final_score'],
            reverse=True
        )
        
        # Assign ranks with ties
        score_counts = {}
        score_to_rank = {}
        current_rank = 1
        
        # Count occurrences of each score and assign first rank
        for p_data in sorted_participants:
            score = p_data['final_score']
            if score in score_counts:
                score_counts[score] += 1
            else:
                score_counts[score] = 1
                score_to_rank[score] = current_rank
            current_rank += 1
        
        # Reset for final assignment
        for i, p_data in enumerate(sorted_participants):
            participant = p_data['participant']
            score = p_data['final_score']
            
            participant.final_score = score
            participant.rank = score_to_rank[score]
            participant.is_tied = score_counts[score] > 1
            
            # Add tie-breaking info even when not breaking ties
            participant.tie_breakers = {
                'final_round': p_data['final_round_score'],
                'first_places': p_data['first_places'],
                'highest_score': p_data['highest_round_score']
            }

    context = {
        'competition': competition,
        'rounds': rounds,
        'participants': [p_data['participant'] for p_data in sorted_participants],
        'tie_breaking_enabled': break_ties  # Flag to indicate tie-breaking is active
    }
    
    return render(request, 'competition_app/competition_results_detail.html', context)




@login_required
def results_reveal(request, competition_id):
    competition = get_object_or_404(Competition.objects.prefetch_related(
        'rounds',
        'participants',
        'judge_assignments__judge__user',  # Add user to prefetch
        'results'
    ), id=competition_id)

    # Get final results ordered by rank
    results = CompetitionResult.objects.filter(
        competition=competition,
        round=competition.rounds.last()
    ).select_related('participant').order_by('rank')

    # Get judges with their profiles
    judges = Judge.objects.filter(
        assignments__competition=competition,
        assignments__status='ACTIVE'
    ).select_related('user').distinct()

    context = {
        'competition': competition,
        'results': results,
        'first_place': results.filter(rank=1).first(),
        'second_place': results.filter(rank=2).first(),
        'third_place': results.filter(rank=3).first(),
        'judges': judges,
        'total_participants': results.count(),
        'total_judges': judges.count(),
    }
    
    return render(request, 'competition_app/results_reveal.html', context)

@login_required
def toggle_results_visibility(request, competition_id):
    if request.method == 'POST' and request.user.is_superuser:
        competition = get_object_or_404(Competition, id=competition_id)
        show_results = request.POST.get('show_results') == 'true'
        
        competition.show_results = show_results
        competition.save()
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=403)

def landing_page(request):
    return render(request, 'landing_page.html')

@login_required
def edit_competition(request, competition_id):
    competition = get_object_or_404(Competition, id=competition_id)
    
    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title')
        description = request.POST.get('description')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        status = request.POST.get('status')
        
        # Update competition
        competition.title = title
        competition.description = description
        competition.start_date = start_date
        competition.end_date = end_date
        competition.status = status
        competition.save()
        
        messages.success(request, 'Competition updated successfully!')
        return redirect('competition_detail', competition_id=competition.id)
    
    return render(request, 'competition_app/edit_competition.html', {'competition': competition})

@login_required
def manage_judges(request, competition_id):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to manage judges.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    assignments = JudgeAssignment.objects.filter(competition=competition)
    available_judges = Judge.objects.filter(status='ACTIVE')
    
    context = {
        'competition': competition,
        'assignments': assignments,
        'available_judges': available_judges,
    }
    return render(request, 'competition_app/judge_management/manage_judges.html', context)

@login_required
def assign_judges(request, competition_id):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to assign judges.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    
    if request.method == 'POST':
        judge_ids = request.POST.getlist('judges')
        round_ids = request.POST.getlist('rounds')
        
        if not judge_ids:
            messages.error(request, 'Please select at least one judge.')
            return redirect('manage_judges', competition_id=competition_id)
            
        if not round_ids:
            messages.error(request, 'Please select at least one round.')
            return redirect('manage_judges', competition_id=competition_id)
            
        judges = Judge.objects.filter(id__in=judge_ids)
        rounds = Round.objects.filter(id__in=round_ids)
        
        for judge in judges:
            assignment, created = JudgeAssignment.objects.get_or_create(
                judge=judge,
                competition=competition,
                defaults={'status': 'ACTIVE'}
            )
            assignment.rounds.set(rounds)
            
        messages.success(request, 'Judges assigned successfully!')
        return redirect('manage_judges', competition_id=competition_id)
        
    available_judges = Judge.objects.filter(status='ACTIVE')
    competition_rounds = Round.objects.filter(competition=competition)
    
    context = {
        'competition': competition,
        'available_judges': available_judges,
        'competition_rounds': competition_rounds,
    }
    return render(request, 'competition_app/judge_management/assign_judges.html', context)

@login_required
def edit_judge_assignment(request, competition_id, assignment_id):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to edit judge assignments.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    assignment = get_object_or_404(JudgeAssignment, id=assignment_id, competition=competition)
    
    if request.method == 'POST':
        round_ids = request.POST.getlist('rounds')
        status = request.POST.get('status')
        
        if not round_ids:
            messages.error(request, 'Please select at least one round.')
            return redirect('edit_judge_assignment', competition_id=competition_id, assignment_id=assignment_id)
            
        rounds = Round.objects.filter(id__in=round_ids)
        assignment.rounds.set(rounds)
        assignment.status = status
        assignment.save()
        
        messages.success(request, 'Judge assignment updated successfully!')
        return redirect('manage_judges', competition_id=competition_id)
        
    competition_rounds = Round.objects.filter(competition=competition)
    context = {
        'competition': competition,
        'assignment': assignment,
        'competition_rounds': competition_rounds,
    }
    return render(request, 'competition_app/judge_management/edit_assignment.html', context)

@login_required
def delete_judge_assignment(request, competition_id, assignment_id):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to delete judge assignments.')
        return redirect('competition_detail', competition_id=competition_id)
        
    assignment = get_object_or_404(JudgeAssignment, id=assignment_id, competition_id=competition_id)
    assignment.delete()
    messages.success(request, 'Judge assignment deleted successfully.')
    return redirect('manage_judges', competition_id=competition_id)

@login_required
def judge_management(request):
    """Landing page for judge management, showing all competitions."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
        
    competitions = Competition.objects.all().order_by('-id')
    for competition in competitions:
        competition.judge_count = JudgeAssignment.objects.filter(competition=competition).count()
        
    context = {
        'competitions': competitions,
    }
    return render(request, 'competition_app/judge_management/judge_management.html', context)

@login_required
def participant_management(request):
    """Landing page for participant management, showing all competitions."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
        
    competitions = Competition.objects.all().order_by('-id')
    for competition in competitions:
        competition.participant_count = competition.participants.count()
        
    context = {
        'competitions': competitions,
    }
    return render(request, 'competition_app/participant_management/participant_management.html', context)

@login_required
def manage_participants(request, competition_id):
    """View to manage participants for a specific competition."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to manage participants.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    participants = competition.participants.all()
    available_participants = Participant.objects.exclude(competitions=competition)
    
    context = {
        'competition': competition,
        'participants': participants,
        'available_participants': available_participants,
    }
    return render(request, 'competition_app/participant_management/manage_participants.html', context)

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from .models import (
    Competition, Participant, Judge, CompetitionResult, 
    JudgeAssignment, ParticipantCompetition, Score
)

@login_required
def assign_participants(request, competition_id):
    """View to assign participants to a competition."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to assign participants.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                participant_ids = request.POST.getlist('participants')
                if not participant_ids:
                    messages.error(request, 'Please select at least one participant to assign.')
                    return redirect('assign_participants', competition_id=competition_id)
                
                participants = Participant.objects.filter(id__in=participant_ids)
                
                # Get the highest current number for this competition
                highest_number = ParticipantCompetition.objects.filter(
                    competition=competition
                ).aggregate(models.Max('number'))['number__max'] or 0
                next_number = highest_number + 1
                
                # Create participant assignments
                assignments = []
                for participant in participants:
                    # Check if participant is already assigned
                    if not ParticipantCompetition.objects.filter(
                        participant=participant,
                        competition=competition
                    ).exists():
                        assignments.append(
                            ParticipantCompetition(
                                participant=participant,
                                competition=competition,
                                number=next_number
                            )
                        )
                        next_number += 1
                
                if assignments:
                    ParticipantCompetition.objects.bulk_create(assignments)
                    messages.success(request, f'{len(assignments)} participant(s) assigned successfully.')
                else:
                    messages.warning(request, 'Selected participants are already assigned to this competition.')
                
                return redirect('manage_participants', competition_id=competition_id)
                
        except Exception as e:
            messages.error(request, f'Error assigning participants: {str(e)}')
            return redirect('assign_participants', competition_id=competition_id)
    
    # Get all available participants not in this competition
    available_participants = Participant.objects.exclude(competitions=competition)
    
    # Group participants by gender
    grouped_participants = {
        'male': available_participants.filter(gender='male').order_by('name'),
        'female': available_participants.filter(gender='female').order_by('name'),
        'other': available_participants.filter(gender='other').order_by('name'),
        'prefer_not_to_say': available_participants.filter(gender='prefer_not_to_say').order_by('name'),
    }
    
    # Get age ranges for filtering
    age_ranges = []
    if available_participants.filter(age__isnull=False).exists():
        min_age = available_participants.filter(age__isnull=False).order_by('age').first().age
        max_age = available_participants.filter(age__isnull=False).order_by('-age').first().age
        
        # Create age ranges (e.g., 0-18, 19-25, 26-35, 36+)
        current_range = min_age
        while current_range <= max_age:
            next_range = current_range + 9
            age_ranges.append({
                'start': current_range,
                'end': next_range,
                'participants': available_participants.filter(age__gte=current_range, age__lte=next_range)
            })
            current_range = next_range + 1
    
    context = {
        'competition': competition,
        'grouped_participants': grouped_participants,
        'age_ranges': age_ranges,
        'total_available': available_participants.count(),
    }
    
    return render(request, 'competition_app/participant_management/assign_participants.html', context)

@login_required
def delete_participant_assignment(request, competition_id, participant_id):
    competition = get_object_or_404(Competition, id=competition_id)
    participant = get_object_or_404(Participant, id=participant_id)
    
    # Check if user has permission to manage this competition
    if not request.user.is_superuser and competition.organizer != request.user:
        messages.error(request, "You don't have permission to manage this competition.")
        return redirect('competition_detail', competition_id=competition_id)
    
    # Delete the participant assignment
    ParticipantCompetition.objects.filter(
        competition=competition,
        participant=participant
    ).delete()
    
    messages.success(request, f"Successfully removed {participant.name} from {competition.name}.")
    return redirect('manage_participants', competition_id=competition_id)

@login_required
def delete_participant(request, participant_id):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to delete participants.")
        return redirect('participant_list')
    
    try:
        participant = get_object_or_404(Participant, id=participant_id)
        participant_name = participant.name
        
        # Delete all related records first
        Score.objects.filter(participant=participant).delete()
        CompetitionResult.objects.filter(participant=participant).delete()
        ParticipantCompetition.objects.filter(participant=participant).delete()
        
        # Finally delete the participant
        participant.delete()
        
        messages.success(request, f"Successfully deleted participant: {participant_name}")
    except Exception as e:
        messages.error(request, f"Error deleting participant: {str(e)}")
    
    return redirect('participant_list')

@login_required
def manage_rounds(request, competition_id):
    """View to manage rounds for a specific competition."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to manage rounds.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    rounds = competition.rounds.all()
    
    context = {
        'competition': competition,
        'rounds': rounds,
    }
    return render(request, 'competition_app/round_management/manage_rounds.html', context)

@login_required
def create_round(request, competition_id):
    competition = get_object_or_404(Competition, id=competition_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                name = request.POST.get('name')
                description = request.POST.get('description')
                order = request.POST.get('order')
                weight_percentage = request.POST.get('weight_percentage')
                
                # Validate weight percentage
                total_weight = Round.objects.filter(competition=competition).exclude(status='COMPLETED').aggregate(
                    total=models.Sum('weight_percentage')
                )['total'] or 0
                
                new_weight = Decimal(weight_percentage)
                if total_weight + new_weight > 100:
                    remaining_weight = 100 - total_weight
                    messages.error(
                        request, 
                        f'Total weight percentage cannot exceed 100%. Current total is {total_weight}%. '
                        f'You can add up to {remaining_weight}%.'
                    )
                    return redirect('create_round', competition_id=competition_id)
                
                # Create the round
                round_obj = Round.objects.create(
                    competition=competition,
                    name=name,
                    description=description,
                    order=order,
                    weight_percentage=new_weight,
                    status='PENDING'
                )
                
                # Get criteria data from form
                criterion_names = request.POST.getlist('criterion_names[]')
                criterion_descriptions = request.POST.getlist('criterion_descriptions[]')
                criterion_max_scores = request.POST.getlist('criterion_max_scores[]')
                
                # Create criteria for this round
                for i in range(len(criterion_names)):
                    if criterion_names[i].strip():  # Only create if name is not empty
                        Criterion.objects.create(
                            round=round_obj,
                            name=criterion_names[i],
                            description=criterion_descriptions[i] if i < len(criterion_descriptions) else '',
                            max_score=float(criterion_max_scores[i]) if i < len(criterion_max_scores) and criterion_max_scores[i] else 100
                        )
                
                messages.success(request, 'Round and criteria created successfully!')
                return redirect('manage_rounds', competition_id=competition_id)
                
        except Exception as e:
            messages.error(request, f'Error creating round: {str(e)}')
            return redirect('create_round', competition_id=competition_id)
    
    context = {
        'competition': competition,
    }
    return render(request, 'competition_app/round_management/create_round.html', context)

@login_required
def edit_round(request, competition_id, round_id):
    competition = get_object_or_404(Competition, id=competition_id)
    round_obj = get_object_or_404(Round, id=round_id, competition=competition)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                name = request.POST.get('name')
                description = request.POST.get('description')
                order = request.POST.get('order')
                weight_percentage = Decimal(request.POST.get('weight_percentage'))
                
                # Calculate total weight excluding current round
                other_rounds_weight = Round.objects.filter(competition=competition).exclude(id=round_id).exclude(status='COMPLETED').aggregate(
                    total=models.Sum('weight_percentage')
                )['total'] or 0
                
                if other_rounds_weight + weight_percentage > 100:
                    remaining_weight = 100 - other_rounds_weight
                    messages.error(
                        request, 
                        f'Total weight percentage cannot exceed 100%. Current total (excluding this round) is {other_rounds_weight}%. '
                        f'You can set up to {remaining_weight}%.'
                    )
                    return redirect('edit_round', competition_id=competition_id, round_id=round_id)
                
                # Update round details
                round_obj.name = name
                round_obj.description = description
                round_obj.order = order
                round_obj.weight_percentage = weight_percentage
                round_obj.save()
                
                # Update existing criteria
                existing_criteria_ids = set(round_obj.criteria.values_list('id', flat=True))
                updated_criteria_ids = set()
                
                criterion_names = request.POST.getlist('criterion_names[]')
                criterion_descriptions = request.POST.getlist('criterion_descriptions[]')
                criterion_max_scores = request.POST.getlist('criterion_max_scores[]')
                criterion_ids = request.POST.getlist('criterion_ids[]')
                
                # Update or create criteria
                for i in range(len(criterion_names)):
                    if not criterion_names[i].strip():
                        continue
                        
                    criterion_id = criterion_ids[i] if i < len(criterion_ids) else None
                    if criterion_id and criterion_id.isdigit():
                        # Update existing criterion
                        criterion_id = int(criterion_id)
                        if criterion_id in existing_criteria_ids:
                            criterion = Criterion.objects.get(id=criterion_id)
                            criterion.name = criterion_names[i]
                            criterion.description = criterion_descriptions[i] if i < len(criterion_descriptions) else ''
                            criterion.max_score = Decimal(criterion_max_scores[i]) if i < len(criterion_max_scores) and criterion_max_scores[i] else 100
                            criterion.save()
                            updated_criteria_ids.add(criterion_id)
                    else:
                        # Create new criterion
                        criterion = Criterion.objects.create(
                            round=round_obj,
                            name=criterion_names[i],
                            description=criterion_descriptions[i] if i < len(criterion_descriptions) else '',
                            max_score=Decimal(criterion_max_scores[i]) if i < len(criterion_max_scores) and criterion_max_scores[i] else 100
                        )
                        updated_criteria_ids.add(criterion.id)
                
                # Delete criteria that were not updated
                criteria_to_delete = existing_criteria_ids - updated_criteria_ids
                Criterion.objects.filter(id__in=criteria_to_delete).delete()
                
                messages.success(request, 'Round and criteria updated successfully!')
                return redirect('manage_rounds', competition_id=competition_id)
                
        except Exception as e:
            messages.error(request, f'Error updating round: {str(e)}')
            return redirect('edit_round', competition_id=competition_id, round_id=round_id)
    
    context = {
        'competition': competition,
        'round': round_obj,
        'criteria': round_obj.criteria.all(),
    }
    return render(request, 'competition_app/round_management/edit_round.html', context)

@login_required
def delete_round(request, competition_id, round_id):
    print(f"Delete round called with method: {request.method}")
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('manage_rounds', competition_id=competition_id)

    try:
        round_obj = get_object_or_404(Round, id=round_id, competition_id=competition_id)
        print(f"Found round: {round_obj.name}")
        
        # Delete all associated scores first
        Score.objects.filter(criterion__round=round_obj).delete()
        print("Deleted associated scores")
        
        # Delete all criteria
        round_obj.criteria.all().delete()
        print("Deleted criteria")
        
        # Then delete the round
        round_obj.delete()
        print("Round deleted successfully")
        messages.success(request, 'Round and all associated data deleted successfully.')
    except Exception as e:
        print(f"Error deleting round: {str(e)}")
        messages.error(request, f'Error deleting round: {str(e)}')
    
    return redirect('manage_rounds', competition_id=competition_id)

@login_required
def toggle_round_status(request, competition_id, round_id):
    round_obj = get_object_or_404(Round, id=round_id, competition_id=competition_id)
    
    # Define the status flow
    status_flow = {
        'PENDING': 'ONGOING',
        'ONGOING': 'COMPLETED',
        'COMPLETED': 'PENDING'
    }
    
    round_obj.status = status_flow[round_obj.status]
    round_obj.save()
    
    # If round is completed, calculate rankings
    if round_obj.status == 'COMPLETED':
        calculate_rankings(round_obj)
    
    messages.success(request, f'Round status updated to {round_obj.status}.')
    return redirect('manage_rounds', competition_id=competition_id)

@login_required
def round_results(request, competition_id, round_id):
    """View to display results for a specific round."""
    competition = get_object_or_404(Competition, id=competition_id)
    round_obj = get_object_or_404(Round, id=round_id, competition=competition)
    
    if round_obj.status != 'COMPLETED':
        messages.error(request, 'Results are only available for completed rounds.')
        return redirect('manage_rounds', competition_id=competition_id)
    
    # Get criteria for this round
    criteria = round_obj.criteria.all()
    
    # Get results ordered by rank
    results = CompetitionResult.objects.filter(
        round=round_obj
    ).select_related('participant').order_by('rank')
    
    # Calculate average scores for each criterion for each participant
    for result in results:
        criterion_scores = {}
        for criterion in criteria:
            avg_score = Score.objects.filter(
                participant=result.participant,
                criterion=criterion,
                status='SUBMITTED'
            ).aggregate(avg=models.Avg('score'))['avg'] or 0
            criterion_scores[criterion.id] = avg_score
        result.criterion_scores = criterion_scores
    
    # Calculate statistics
    scores = [result.total_score for result in results]
    statistics = {
        'highest_score': max(scores) if scores else 0,
        'average_score': sum(scores) / len(scores) if scores else 0,
        'lowest_score': min(scores) if scores else 0,
        'total_participants': len(scores)
    }
    
    context = {
        'competition': competition,
        'round': round_obj,
        'criteria': criteria,
        'results': results,
        'statistics': statistics
    }
    
    return render(request, 'competition_app/round_management/round_results.html', context)

@login_required
def generate_results_pdf(request, competition_id):
    competition = get_object_or_404(Competition, id=competition_id)
    rounds = competition.rounds.all()
    judges = Judge.objects.filter(assignments__competition=competition)
    
    # Create the PDF document
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{competition.name}_results.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=letter,
                          rightMargin=25, leftMargin=25,
                          topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    elements = []
    
    # Add title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=14,
        spaceAfter=10
    )
    title = Paragraph(f"{competition.name} - Results", title_style)
    elements.append(title)
    elements.append(Spacer(1, 10))
    
    # First section: Round Summary and Final Rankings
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=12,
        spaceAfter=6
    )
    elements.append(Paragraph("Round Summary and Final Rankings", heading_style))
    elements.append(Spacer(1, 6))
    
    # Calculate rankings for each round first
    round_rankings = {}
    for round_obj in rounds:
        round_scores = []
        for participant in competition.participants.all():
            scores = Score.objects.filter(
                participant=participant,
                criterion__round=round_obj,
                status='SUBMITTED'
            ).select_related('criterion')
            
            if scores.exists():
                # Calculate total score for this round
                total_score = 0
                criteria_count = 0
                for criterion in round_obj.criteria.all():
                    criterion_scores = [s.score for s in scores if s.criterion_id == criterion.id]
                    if criterion_scores:
                        avg_score = sum(criterion_scores) / len(criterion_scores)
                        total_score += avg_score
                        criteria_count += 1
                
                round_avg = total_score / criteria_count if criteria_count > 0 else 0
                round_scores.append({
                    'participant': participant,
                    'score': round_avg
                })
        
        # Sort and assign ranks for this round
        round_scores.sort(key=lambda x: x['score'], reverse=True)
        round_rankings[round_obj.id] = {
            score['participant'].id: {'rank': idx + 1, 'score': score['score']}
            for idx, score in enumerate(round_scores)
        }
    
    # Calculate final rankings based on weighted scores and ranks
    participant_data = []
    for participant in competition.participants.all():  # Use original order
        total_weighted_rank = 0
        round_data = {}
        
        for round_obj in rounds:
            round_weight = round_obj.weight_percentage / 100
            if participant.id in round_rankings[round_obj.id]:
                rank_data = round_rankings[round_obj.id][participant.id]
                round_data[round_obj.id] = rank_data
                # Calculate weighted rank for this round
                total_weighted_rank += rank_data['rank'] * round_weight
        
        participant_data.append({
            'participant': participant,
            'total_rank': total_weighted_rank,
            'round_data': round_data
        })
    
    # Calculate final ranks based on total weighted rank
    sorted_by_total = sorted(participant_data, key=lambda x: x['total_rank'])
    rank_lookup = {p['participant'].id: idx + 1 for idx, p in enumerate(sorted_by_total)}
    
    # Create final rankings table
    final_table_data = [['Participant']]
    
    # Add round columns
    for round_obj in rounds:
        final_table_data[0].append(f"{round_obj.name}\n({round_obj.weight_percentage}%)")
    
    # Add Total Rank and Rank columns
    final_table_data[0].extend(['Total Rank', 'Rank'])
    
    # Add participant data (in original order)
    for data in participant_data:
        row = [
            data['participant'].name
        ]
        
        # Add round ranks
        for round_obj in rounds:
            if round_obj.id in data['round_data']:
                round_info = data['round_data'][round_obj.id]
                row.append(str(round_info['rank']))
            else:
                row.append("N/A")
        
        # Add weighted total rank and final rank
        row.extend([
            f"{data['total_rank']:.2f}",  # Weighted total rank
            str(rank_lookup[data['participant'].id])  # Final rank based on total rank order
        ])
        
        final_table_data.append(row)
    
    # Create and style the table
    final_table = Table(final_table_data)
    final_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),  # Center align all cells
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        # Highlight the last two columns (Total Rank and Rank)
        ('BACKGROUND', (-2, 0), (-1, -1), colors.lightgrey),
        ('TEXTCOLOR', (-2, 0), (-1, -1), colors.black),
    ]))
    elements.append(final_table)
    elements.append(Spacer(1, 10))
    
    # Second section: Individual Round Results
    for round_obj in rounds:
        elements.append(Paragraph(f"{round_obj.name} Results", heading_style))
        elements.append(Spacer(1, 6))
        
        # Calculate round scores
        round_scores = []
        for participant in competition.participants.all():
            scores = Score.objects.filter(
                participant=participant,
                criterion__round=round_obj,
                status='SUBMITTED'
            ).select_related('criterion')
            
            if scores.exists():
                # Calculate total score for this round
                total_score = 0
                criteria_count = 0
                for criterion in round_obj.criteria.all():
                    criterion_scores = [s.score for s in scores if s.criterion_id == criterion.id]
                    if criterion_scores:
                        avg_score = sum(criterion_scores) / len(criterion_scores)
                        total_score += avg_score
                        criteria_count += 1
                
                round_avg = total_score / criteria_count if criteria_count > 0 else 0
                round_scores.append({
                    'participant': participant,
                    'score': round_avg
                })
        
        # Sort by total score
        round_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # Create round table
        round_table_data = [['Rank', 'Participant']]
        criteria = round_obj.criteria.all()
        for criterion in criteria:
            round_table_data[0].append(criterion.name)
        round_table_data[0].append('Total Average')  # Changed from 'Total'
        
        for rank, data in enumerate(round_scores, 1):
            row = [str(rank), data['participant'].name]
            for criterion in criteria:
                scores = Score.objects.filter(
                    participant=data['participant'],
                    criterion=criterion,
                    status='SUBMITTED'
                )
                if scores.exists():
                    avg_score = sum(s.score for s in scores) / len(scores)
                    row.append(f"{avg_score:.2f}")
                else:
                    row.append("N/A")
            row.append(f"{data['score']:.2f}")
            round_table_data.append(row)
        
        round_table = Table(round_table_data)
        round_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(round_table)
        elements.append(Spacer(1, 10))
    
    # Third section: Certifications
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("CERTIFICATION", heading_style))
    elements.append(Spacer(1, 6))

    # Certification text
    cert_text = (
        "We, the undersigned, hereby certify that this competition was conducted in accordance "
        "with all applicable rules and regulations, and that the results presented herein are "
        "true and accurate."
    )
    elements.append(Paragraph(cert_text, ParagraphStyle(
        'CertText',
        parent=styles['Normal'],
        fontSize=8,
        leading=10
    )))
    elements.append(Spacer(1, 15))

    # Judge signatures
    judge_data = []
    row = []
    for i, judge in enumerate(judges, 1):
        judge_name = judge.user.get_full_name()
        signature = [
            HRFlowable(width=150, thickness=1, color=colors.black),
            Paragraph(judge_name.upper(), ParagraphStyle(
                'JudgeName',
                parent=styles['Normal'],
                alignment=1,
                fontSize=8,
                textColor=colors.blue
            )),
            Paragraph("Competition Judge", ParagraphStyle(
                'JudgeTitle',
                parent=styles['Normal'],
                alignment=1,
                fontSize=7
            ))
        ]
        row.append(signature)
        
        if i % 2 == 0 or i == len(judges):
            while len(row) < 2:
                row.append([])
            judge_data.append(row)
            row = []

    signature_table = Table(judge_data, colWidths=[200, 200])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    elements.append(signature_table)
    elements.append(Spacer(1, 15))

    # Chairperson signature
    elements.append(Table([[
        HRFlowable(width=300, thickness=1, color=colors.black),
    ]], colWidths=[300]))
    elements.append(Paragraph("Competition Chairperson", ParagraphStyle(
        'ChairTitle',
        parent=styles['Normal'],
        alignment=1,
        fontSize=8
    )))
    elements.append(Paragraph(datetime.now().strftime("%B %d, %Y"), ParagraphStyle(
        'Date',
        parent=styles['Normal'],
        alignment=1,
        fontSize=7
    )))
    elements.append(Spacer(1, 15))

    # Footer
    footer_text = f"OFFICIAL DOCUMENT • Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} • SET"
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    elements.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        alignment=1,
        fontSize=6,
        textColor=colors.gray
    )))
    
    # Build the PDF
    doc.build(elements)
    
    # FileResponse sets the Content-Disposition header so that browsers present the option to save the file
    return response

@login_required
def results_list(request):
    competitions = Competition.objects.prefetch_related(
        'rounds',
        'participants',
        'rounds__results',
        'rounds__results__participant',
        'rounds__criteria'  # Add criteria for score calculations
    ).order_by('-start_date')

    competition_results = []
    for competition in competitions:
        latest_round = competition.rounds.order_by('-order').first()
        
        if latest_round:
            # Recalculate rankings to ensure accuracy
            calculate_rankings(latest_round)
            
            # Get total participants count from CompetitionResult
            total_participants = CompetitionResult.objects.filter(
                round=latest_round
            ).count()
            
            # Get top 3 results
            top_results = CompetitionResult.objects.filter(
                round=latest_round,
                total_score__gt=0  # Only include participants with scores
            ).select_related('participant').order_by('rank', '-total_score')[:3]
            
            # Validate the results
            if top_results:
                # Sort again by total_score to ensure correct order
                top_results = sorted(top_results, key=lambda x: x.total_score, reverse=True)
        else:
            top_results = []
            total_participants = 0

        competition_data = {
            'competition': competition,
            'latest_round': latest_round,
            'results_visible': competition.show_results,
            'total_participants': total_participants,
            'total_rounds': competition.rounds.count(),
            'top_results': top_results if competition.show_results else []
        }
        competition_results.append(competition_data)

    return render(request, 'competition_app/results_list.html', {
        'competition_results': competition_results,
        'page_title': 'Competition Results'
    })
def toggle_competition_status(request, competition_id):
    if request.method == 'POST':
        competition = get_object_or_404(Competition, id=competition_id)
        
        # Define the status flow
        status_flow = {
            'PENDING': 'DRAFT',
            'DRAFT': 'ACTIVE',
            'ACTIVE': 'COMPLETED',
            'COMPLETED': 'DRAFT'
        }
        
        # Update the status, defaulting to DRAFT if current status not in flow
        competition.status = status_flow.get(competition.status, 'DRAFT')
        competition.save()
        
        messages.success(request, f'Competition status updated to {competition.status}')
        return redirect('competition_list')

@login_required
def create_participant(request):
    if request.method == 'POST':
        try:
            # Debug logging
            print("POST data:", request.POST)
            
            participant = Participant.objects.create(
                name=request.POST.get('name'),
                email=request.POST.get('email'),
                phone=request.POST.get('phone'),
                age=request.POST.get('age'),
                gender=request.POST.get('gender'),
                bio=request.POST.get('bio'),
                achievements=request.POST.get('achievements'),
                status='ACTIVE'
            )
            
            if 'profile_image' in request.FILES:
                participant.profile_image = request.FILES['profile_image']
                participant.save()
            
            # Debug logging to confirm participant was created
            print("Participant created successfully:", participant.id, participant.name, participant.email)
            
            messages.success(request, 'Participant created successfully!')
            
            # Check if we need to redirect to assign participants
            next_url = request.POST.get('next')
            if next_url and 'assign_participants' in next_url:
                return redirect(next_url)
            return redirect('participant_list')  # Changed to redirect to participant list
            
        except Exception as e:
            print("Error creating participant:", str(e))  # Debug logging
            messages.error(request, f'Error creating participant: {str(e)}')
    
    # Get the next URL if we're coming from assign_participants
    next_url = request.GET.get('next', '')
    
    return render(request, 'competition_app/participant_management/create_participant.html', {
        'next_url': next_url
    })

@login_required
def participant_list(request):
    participants = Participant.objects.all().order_by('-registration_date')
    return render(request, 'competition_app/participant_list.html', {'participants': participants})

@login_required
def participant_detail(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    participant_competitions = ParticipantCompetition.objects.filter(
        participant=participant
    ).select_related(
        'competition'
    ).prefetch_related(
        'competition__results'
    ).order_by('-competition__start_date')

    context = {
        'participant': participant,
        'participant_competitions': participant_competitions,
    }
    return render(request, 'competition_app/participant_detail.html', context)

@login_required
def judge_dashboard(request):
    judge = get_object_or_404(Judge, user=request.user)
    
    # Get only assigned active competitions
    assigned_competitions = Competition.objects.filter(
        status='ACTIVE',
        judge_assignments__judge=judge,
        judge_assignments__status='ACTIVE'
    ).prefetch_related('rounds')
    
    competition_data = []
    for competition in assigned_competitions:
        assigned_rounds = competition.rounds.filter(
            judge_assignments__judge=judge
        )
        
        competition_data.append({
            'competition': competition,
            'rounds': assigned_rounds,
            'participant_count': competition.participants.count(),
        })
    
    context = {
        'judge': judge,
        'competition_data': competition_data,
        'pending_scores': Score.objects.filter(judge=judge, status='DRAFT').count(),
        'submitted_scores': Score.objects.filter(judge=judge, status='SUBMITTED').count(),
    }
    return render(request, 'competition_app/judge/dashboard.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        profile_image = request.FILES.get('profile_image')

        user = request.user
        user.username = username
        user.email = email

        if profile_image:
            # Assuming you have a profile model with an image field
            if hasattr(user, 'judge'):
                user.judge.profile_image = profile_image
                user.judge.save()

        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('judge_dashboard')

    return render(request, 'competition_app/profile.html')

@login_required
def settings_view(request):
    return render(request, 'settings.html')

@login_required
def start_round(request, competition_id, round_id):
    if request.method == 'POST':
        competition = get_object_or_404(Competition, id=competition_id)
        round_obj = get_object_or_404(Round, id=round_id, competition=competition)
        
        # Check if there's already an active round
        if competition.rounds.filter(is_active=True).exists():
            messages.error(request, "Another round is currently active. Please complete it first.")
            return redirect('manage_rounds', competition_id=competition_id)
        
        # Start the round
        round_obj.is_active = True
        round_obj.save()
        
        messages.success(request, f"Round '{round_obj.name}' has been started successfully.")
        return redirect('manage_rounds', competition_id=competition_id)
    
    return redirect('manage_rounds', competition_id=competition_id)

@login_required
def complete_round(request, competition_id, round_id):
    if request.method == 'POST':
        competition = get_object_or_404(Competition, id=competition_id)
        round_obj = get_object_or_404(Round, id=round_id, competition=competition)
        
        if not round_obj.is_active:
            messages.error(request, "This round is not currently active.")
            return redirect('manage_rounds', competition_id=competition_id)
        
        # Complete the round
        round_obj.is_active = False
        round_obj.is_completed = True
        round_obj.save()
        
        # Calculate final rankings for this round
        calculate_rankings(round_obj)
        
        messages.success(request, f"Round '{round_obj.name}' has been completed successfully.")
        return redirect('manage_rounds', competition_id=competition_id)
    
    return redirect('manage_rounds', competition_id=competition_id)

@login_required
def delete_competition(request, competition_id):
    if request.method == 'POST':
        competition = get_object_or_404(Competition, id=competition_id)
        competition.delete()
        messages.success(request, 'Competition deleted successfully.')
        return redirect('competition_list')
    return redirect('competition_list')

@login_required
def remove_participant_from_competition(request, competition_id, participant_id):
    try:
        competition = Competition.objects.get(id=competition_id)
        participant = Participant.objects.get(id=participant_id)
        
        # Remove the participant from the competition
        competition.participants.remove(participant)
        
        messages.success(request, f'Successfully removed {participant.name} from {competition.name}')
    except Competition.DoesNotExist:
        messages.error(request, 'Competition not found.')
    except Participant.DoesNotExist:
        messages.error(request, 'Participant not found.')
    except Exception as e:
        messages.error(request, f'Error removing participant: {str(e)}')
    
    return redirect('manage_participants', competition_id=competition_id)

@login_required
def update_score(request, round_id):
    if not request.headers.get('HX-Request'):
        return HttpResponseBadRequest("Not an HTMX request")
    
    try:    
        judge = get_object_or_404(Judge, user=request.user)
        
        # Get the first score field from POST data that contains a value
        score_field = next((key for key in request.POST.keys() if key.startswith('score_')), None)
        if not score_field:
            return HttpResponseBadRequest("No score field found")
            
        # Parse participant_id and criterion_id from the field name
        # Field name format: score_<participant_id>_<criterion_id>
        try:
            _, participant_id, criterion_id = score_field.split('_')
            score_value = request.POST.get(score_field)
            
            print(f"Debug - Parsed values: participant_id={participant_id}, criterion_id={criterion_id}, score_value={score_value}")
            
            if not all([participant_id, criterion_id, score_value]):
                return HttpResponseBadRequest("Missing required parameters")
                
            score_value = float(score_value)
        except (ValueError, IndexError) as e:
            print(f"Debug - Error parsing values: {str(e)}")
            return HttpResponseBadRequest("Invalid score format")
        
        # Get the objects
        round_obj = get_object_or_404(Round, id=round_id)
        participant = get_object_or_404(Participant, id=participant_id)
        criterion = get_object_or_404(Criterion, id=criterion_id)
        
        # Update or create the score
        score, created = Score.objects.update_or_create(
            participant=participant,
            criterion=criterion,
            judge=judge,
            defaults={
                'score': score_value,
                'status': 'DRAFT'
            }
        )
        
        # Calculate total score for this participant including draft scores
        total_score = calculate_participant_total_score(participant, round_obj, include_draft=True)
        
        # Return the updated total score
        return HttpResponse(f"{total_score:.1f}")
    except Exception as e:
        print(f"Debug - Error in update_score: {str(e)}")
        return HttpResponseBadRequest(str(e))

@login_required
def search(request):
    query = request.GET.get('q', '')
    
    if query:
        competitions = Competition.objects.filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query)
        )
        participants = Participant.objects.filter(
            models.Q(name__icontains=query) |
            models.Q(email__icontains=query)
        )
        results = CompetitionResult.objects.filter(
            models.Q(competition__name__icontains=query) |
            models.Q(participant__name__icontains=query)
        )
    else:
        competitions = Competition.objects.none()
        participants = Participant.objects.none()
        results = CompetitionResult.objects.none()
    
    context = {
        'query': query,
        'competitions': competitions,
        'participants': participants,
        'results': results,
        'total_results': competitions.count() + participants.count() + results.count()
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'competition_app/partials/search_results.html', context)
    return render(request, 'competition_app/search.html', context)

@login_required
def generate_judges_breakdown_pdf(request, competition_id):
    competition = get_object_or_404(Competition, id=competition_id)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    elements.append(Paragraph(f"Judges Scoring Breakdown - {competition.name}", title_style))
    elements.append(Spacer(1, 20))
    
    # For each round
    for round_obj in competition.rounds.all():
        # Round Header
        elements.append(Paragraph(f"Round {round_obj.order}: {round_obj.name}", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        # Get all judges and participants for this round
        judges = Judge.objects.filter(assignments__competition=competition)
        participants = Participant.objects.filter(participantcompetition__competition=competition)
        criteria = round_obj.criteria.all()
        
        if not judges or not participants or not criteria:
            elements.append(Paragraph("No data available for this round", styles['Normal']))
            elements.append(Spacer(1, 20))
            continue
            
        # For each judge, create a separate table
        for judge in judges:
            # Judge Header
            judge_name = judge.user.get_full_name()
            elements.append(Paragraph(f"Judge: {judge_name}", styles['Heading3']))
            elements.append(Spacer(1, 10))
            
            # Create header row for the table
            header = ['Rank', 'Participant']
            for criterion in criteria:
                header.append(criterion.name)
            header.append('Total Average')  # Changed from 'Total'
            
            # Collect scores for ranking
            participant_scores = []
            for participant in participants:
                row_data = {'participant': participant, 'scores': [], 'total': 0, 'valid_scores': 0}
                for criterion in criteria:
                    score = Score.objects.filter(
                        judge=judge,
                        participant=participant,
                        criterion=criterion,
                        criterion__round=round_obj,
                        status='SUBMITTED'
                    ).first()
                    score_value = score.score if score else '-'
                    row_data['scores'].append(score_value)
                    if score and isinstance(score_value, (int, float, Decimal)):
                        row_data['total'] += float(score_value)
                        row_data['valid_scores'] += 1
                
                # Calculate average if there are valid scores
                if row_data['valid_scores'] > 0:
                    row_data['average'] = row_data['total'] / row_data['valid_scores']
                else:
                    row_data['average'] = 0
                participant_scores.append(row_data)
            
            # Sort participants by average score and assign ranks
            participant_scores.sort(key=lambda x: x['average'], reverse=True)
            current_rank = 1
            previous_score = None
            for i, p_score in enumerate(participant_scores):
                if previous_score is not None and p_score['average'] != previous_score:
                    current_rank = i + 1
            
                p_score['rank'] = current_rank
                previous_score = p_score['average']
            
            # Create data rows with ranks
            data = [header]
            for p_score in participant_scores:
                row = [str(p_score['rank']), p_score['participant'].name]
                row.extend(p_score['scores'])
                # Show average score for criteria breakdown
                row.append(f'{p_score["average"]:.2f}' if p_score['valid_scores'] > 0 else '-')
                data.append(row)
            
            # Create and style the table
            col_widths = [50, 150] + [100] * (len(header) - 3) + [80]  # Added width for rank column
            table = Table(data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('WORDWRAP', (0, 0), (-1, -1), True),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 20))
        
        # Add round summary table with final rankings
        elements.append(Paragraph("Round Summary and Final Rankings", styles['Heading3']))
        elements.append(Spacer(1, 10))
        
        # Create summary header
        summary_header = ['Rank', 'Participant']
        for judge in judges:
            summary_header.append(f'{judge.user.get_full_name()}\nTotal')
        summary_header.append('Total Average')  # Changed from 'Final Total'
        
        # Collect and calculate final scores for ranking
        final_scores = []
        for participant in participants:
            participant_data = {
                'participant': participant,
                'judge_totals': [],  # Keep as list to maintain order
                'final_total': 0
            }
            for judge in judges:
                judge_total = 0
                scores = Score.objects.filter(
                    judge=judge,
                    participant=participant,
                    criterion__round=round_obj,
                    status='SUBMITTED'
                )
                for score in scores:
                    if score.score:
                        judge_total += float(score.score)
                participant_data['judge_totals'].append(judge_total)
                participant_data['final_total'] += judge_total
            final_scores.append(participant_data)
        
        # Sort and assign final ranks
        final_scores.sort(key=lambda x: x['final_total'], reverse=True)
        current_rank = 1
        previous_score = None
        for i, f_score in enumerate(final_scores):
            if previous_score is not None and f_score['final_total'] != previous_score:
                current_rank = i + 1
            
            f_score['rank'] = current_rank
            previous_score = f_score['final_total']
        
        # Create summary data with ranks
        summary_data = [summary_header]
        for f_score in final_scores:
            row = [str(f_score['rank']), f_score['participant'].name]
            # Add judge totals from the list in order
            row.extend([f'{total:.2f}' for total in f_score['judge_totals']])
            # Calculate average for round summary
            avg_score = f_score['final_total'] / len(judges) if judges else 0
            row.append(f"{avg_score:.2f}")
            summary_data.append(row)
        
        # Create and style summary table
        summary_col_widths = [50, 150] + [100] * (len(judges)) + [80]
        summary_table = Table(summary_data, colWidths=summary_col_widths)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements.append(Paragraph(f"Generated on: {timestamp}", styles['Normal']))
        elements.append(Spacer(1, 30))
        
        # Add page break between rounds
        elements.append(PageBreak())
    
    # Build the PDF
    doc.build(elements)
    
    # FileResponse sets the Content-Disposition header so that browsers present the option to save the file
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'judges_breakdown_{competition.name}.pdf')

@login_required
def submit_scores(request, round_id):
    """Handle submission of scores for a participant in a round."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)
    
    round_obj = get_object_or_404(Round, id=round_id)
    participant_id = request.POST.get('participant_id')
    judge = get_object_or_404(Judge, user=request.user)
    
    # Check if scores are already submitted for this participant
    if Score.objects.filter(
        participant_id=participant_id,
        judge=judge,
        criterion__in=round_obj.criteria.all(),
        status='SUBMITTED'
    ).exists():
        return JsonResponse({
            'status': 'error',
            'message': 'Scores have already been submitted for this participant'
        }, status=400)
    
    try:
        with transaction.atomic():
            # Process each criterion score
            for key, value in request.POST.items():
                if key.startswith('score_') and '_' in key:
                    # Parse participant_id and criterion_id from the field name
                    # Field name format: score_<participant_id>_<criterion_id>
                    try:
                        _, participant_id, criterion_id = key.split('_')
                    except ValueError:
                        continue
                    
                    criterion = get_object_or_404(Criterion, id=criterion_id)
                    
                    # Update or create score
                    score, created = Score.objects.update_or_create(
                        participant_id=participant_id,
                        criterion=criterion,
                        judge=judge,
                        defaults={
                            'score': Decimal(value),
                            'status': 'SUBMITTED'
                        }
                    )
            
            # Calculate total score from all judges
            total_score = calculate_participant_total_score(participant_id, round_obj)
            
            # Update or create CompetitionResult
            CompetitionResult.objects.update_or_create(
                competition=round_obj.competition,
                participant_id=participant_id,
                round=round_obj,
                defaults={
                    'total_score': total_score,
                    'rank': 0  # Will be updated in calculate_rankings
                }
            )
            
            # Recalculate rankings
            calculate_rankings(round_obj)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Scores submitted successfully'
            })
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
def save_scores(request, round_id):
    """Save scores without finalizing them"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

    round_obj = get_object_or_404(Round, id=round_id)
    judge = get_object_or_404(Judge, user=request.user)
    
    try:
        with transaction.atomic():
            for key, value in request.POST.items():
                if key.startswith('score_'):
                    _, participant_id, criterion_id = key.split('_')
                    
                    participant = get_object_or_404(Participant, id=participant_id)
                    criterion = get_object_or_404(Criterion, id=criterion_id)
                    
                    # Update or create score with DRAFT status
                    score, created = Score.objects.update_or_create(
                        participant=participant,
                        judge=judge,
                        criterion=criterion,
                        defaults={'score': float(value), 'status': 'DRAFT'}
                    )

            # Update rankings but don't finalize
            update_participant_rankings(round_obj)

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def view_all_judges(request):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to view all judges.')
        return redirect('dashboard')
        
    judges = Judge.objects.all().select_related('user').order_by('user__first_name')
    
    context = {
        'judges': judges,
    }
    return render(request, 'competition_app/judge_management/view_all_judges.html', context)

@login_required
def add_judge(request):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to add judges.')
        return redirect('dashboard')
        
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        judge_form = JudgeForm(request.POST, request.FILES)
        
        if user_form.is_valid() and judge_form.is_valid():
            user = user_form.save()
            judge = judge_form.save(commit=False)
            judge.user = user
            judge.save()
            
            messages.success(request, 'Judge added successfully.')
            return redirect('view_all_judges')
    else:
        user_form = CustomUserCreationForm()
        judge_form = JudgeForm()
    
    context = {
        'user_form': user_form,
        'judge_form': judge_form,
    }
    return render(request, 'competition_app/judge_management/add_judge.html', context)

@login_required
def delete_judge(request, judge_id):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to delete judges.')
        return redirect('dashboard')
        
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    judge = get_object_or_404(Judge, id=judge_id)
    user = judge.user
    
    try:
        with transaction.atomic():
            judge.delete()
            user.delete()
        messages.success(request, 'Judge deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting judge: {str(e)}')
    
    return redirect('view_all_judges')

