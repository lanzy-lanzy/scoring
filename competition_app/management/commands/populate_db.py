from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from competition_app.models import (
    Competition, Round as CompetitionRound, Criterion, Participant,
    ParticipantCompetition, Judge, Score, JudgeAssignment, CompetitionResult
)
from django.utils import timezone
from datetime import timedelta
import random
import faker
from decimal import Decimal
from django.db.models import Avg, Sum

fake = faker.Faker()

class Command(BaseCommand):
    help = 'Populates the database with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample data...')

        # Create a superuser if it doesn't exist
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_superuser': True,
                'is_staff': True
            }
        )
        if not admin_user.check_password('admin123'):
            admin_user.set_password('admin123')
            admin_user.save()

        # Create or get 5 users for judges
        users = []
        for i in range(5):
            username = f'judge{i+1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'judge{i+1}@example.com',
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name()
                }
            )
            if created:
                user.set_password('judge123')
                user.save()
            users.append(user)

        # Create or get judges
        judges = []
        for user in users:
            judge, _ = Judge.objects.get_or_create(
                user=user,
                defaults={
                    'phone': fake.phone_number(),
                    'expertise': fake.job(),
                    'bio': fake.text()
                }
            )
            judges.append(judge)

        # Delete existing competitions to avoid conflicts
        Competition.objects.all().delete()

        # Create 5 competitions
        competitions = []
        for i in range(5):
            start_date = timezone.now() + timedelta(days=random.randint(1, 30))
            competition = Competition.objects.create(
                name=f'Competition {i+1}: {fake.catch_phrase()}',
                description=fake.text(),
                start_date=start_date,
                end_date=start_date + timedelta(days=random.randint(1, 7)),
                status=random.choice(['DRAFT', 'ACTIVE', 'COMPLETED']),
                created_by=admin_user,
                show_results=random.choice([True, False])
            )
            competitions.append(competition)

        # Create rounds for each competition
        for competition in competitions:
            for i in range(3):
                round = CompetitionRound.objects.create(
                    competition=competition,
                    name=f'Round {i+1}',
                    description=fake.text(),
                    order=i+1,
                    status=random.choice(['PENDING', 'ONGOING', 'COMPLETED']),
                    weight_percentage=random.randint(20, 40)
                )
                
                # Create criteria for each round
                for j in range(3):
                    Criterion.objects.create(
                        round=round,
                        name=f'Criterion {j+1}',
                        description=fake.text(),
                        max_score=random.choice([10.0, 20.0, 25.0, 50.0])
                    )

        # Create 5 participants (clear existing ones first)
        Participant.objects.all().delete()
        participants = []
        for i in range(5):
            participant = Participant.objects.create(
                name=fake.name(),
                email=fake.email(),
                phone=fake.phone_number(),
                age=random.randint(18, 40),
                bio=fake.text(),
                achievements=fake.text(),
                status='ACTIVE',
                profile_image=None
            )
            participants.append(participant)

        # Register participants in competitions
        for competition in competitions:
            for i, participant in enumerate(participants, 1):
                ParticipantCompetition.objects.create(
                    participant=participant,
                    competition=competition,
                    number=i
                )

        # Assign judges to competitions and their rounds
        for competition in competitions:
            for judge in judges:
                assignment = JudgeAssignment.objects.create(
                    judge=judge,
                    competition=competition,
                    status='ACTIVE'
                )
                # Assign judge to all rounds in the competition
                assignment.rounds.set(competition.rounds.all())

        # Create some scores only for ACTIVE competitions and ONGOING rounds
        for competition in competitions:
            if competition.status == 'ACTIVE':
                for round in competition.rounds.all():
                    if round.status == 'ONGOING':
                        for criterion in round.criteria.all():
                            for participant in participants:
                                for judge in judges:
                                    # Check if judge is assigned to this round
                                    if round in judge.assignments.filter(competition=competition).first().rounds.all():
                                        Score.objects.create(
                                            participant=participant,
                                            criterion=criterion,
                                            judge=judge,
                                            score=Decimal("{:.2f}".format(random.uniform(0, float(criterion.max_score)))),
                                            remarks=fake.text(),
                                            status=random.choice(['DRAFT', 'SUBMITTED', 'VERIFIED'])
                                        )

        # Create CompetitionResults for completed competitions
        for competition in competitions:
            if competition.status == 'COMPLETED':
                for round in competition.rounds.all():
                    # Calculate total scores for each participant in this round
                    participant_scores = []
                    for participant in participants:
                        # Calculate average score for each criterion
                        total_score = Decimal('0')
                        for criterion in round.criteria.all():
                            criterion_scores = Score.objects.filter(
                                participant=participant,
                                criterion=criterion,
                                status='VERIFIED'
                            ).values_list('score', flat=True)
                            
                            if criterion_scores:
                                # Average the scores for this criterion
                                avg_criterion_score = sum(criterion_scores) / len(criterion_scores)
                                total_score += Decimal(str(avg_criterion_score))
                        
                        participant_scores.append({
                            'participant': participant,
                            'total_score': total_score
                        })
                    
                    # Sort participants by score and assign ranks
                    ranked_participants = sorted(
                        participant_scores,
                        key=lambda x: x['total_score'],
                        reverse=True
                    )
                    
                    # Create CompetitionResult records with proper rank handling
                    current_rank = 1
                    previous_score = None
                    
                    for idx, p_score in enumerate(ranked_participants):
                        if previous_score != p_score['total_score']:
                            current_rank = idx + 1
                        
                        CompetitionResult.objects.create(
                            competition=competition,
                            participant=p_score['participant'],
                            round=round,
                            total_score=p_score['total_score'],
                            rank=current_rank
                        )
                        previous_score = p_score['total_score']
                
                # Set show_results to True for completed competitions
                competition.show_results = True
                competition.save()

        # Make sure at least one competition is COMPLETED with results
        if not Competition.objects.filter(status='COMPLETED').exists():
            # Take the first competition and complete it
            competition = competitions[0]
            competition.status = 'COMPLETED'
            competition.show_results = True
            competition.save()
            
            # Complete all its rounds
            for round in competition.rounds.all():
                round.status = 'COMPLETED'
                round.save()
                
                # Calculate and create results for this round
                participant_scores = []
                for participant in participants:
                    # Calculate average score for each criterion
                    total_score = Decimal('0')
                    for criterion in round.criteria.all():
                        criterion_scores = Score.objects.filter(
                            participant=participant,
                            criterion=criterion,
                            status='VERIFIED'
                        ).values_list('score', flat=True)
                        
                        if criterion_scores:
                            # Average the scores for this criterion
                            avg_criterion_score = sum(criterion_scores) / len(criterion_scores)
                            total_score += Decimal(str(avg_criterion_score))
                    
                    participant_scores.append({
                        'participant': participant,
                        'total_score': total_score
                    })
                
                # Sort participants by score and assign ranks
                ranked_participants = sorted(
                    participant_scores,
                    key=lambda x: x['total_score'],
                    reverse=True
                )
                
                # Create CompetitionResult records with proper rank handling
                current_rank = 1
                previous_score = None
                
                for idx, p_score in enumerate(ranked_participants):
                    if previous_score != p_score['total_score']:
                        current_rank = idx + 1
                    
                    CompetitionResult.objects.create(
                        competition=competition,
                        participant=p_score['participant'],
                        round=round,
                        total_score=p_score['total_score'],
                        rank=current_rank
                    )
                    previous_score = p_score['total_score']

            # Set all scores to VERIFIED for the completed competition
            Score.objects.filter(
                criterion__round__competition=competition
            ).update(status='VERIFIED')

        # Make sure at least one competition is ACTIVE with an ONGOING round
        if not Competition.objects.filter(status='ACTIVE').exists():
            competition = competitions[1]
            competition.status = 'ACTIVE'
            competition.save()
            
            round = competition.rounds.first()
            round.status = 'ONGOING'
            round.save()

        self.stdout.write(self.style.SUCCESS('Successfully populated database with sample data!'))
