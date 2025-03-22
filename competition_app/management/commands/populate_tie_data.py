from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from competition_app.models import (
    Competition, Round, Criterion, Participant, Judge,
    Score, CompetitionResult, ParticipantCompetition
)
from decimal import Decimal
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Populates the database with tied competition data'

    def handle(self, *args, **kwargs):
        # Create or get test users
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_superuser': True,
                'is_staff': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()

        # Create or get judges
        judge1_user, _ = User.objects.get_or_create(
            username='judge1',
            defaults={'email': 'judge1@example.com'}
        )
        if _:
            judge1_user.set_password('judge123')
            judge1_user.save()

        judge2_user, _ = User.objects.get_or_create(
            username='judge2',
            defaults={'email': 'judge2@example.com'}
        )
        if _:
            judge2_user.set_password('judge123')
            judge2_user.save()

        judge1, _ = Judge.objects.get_or_create(
            user=judge1_user,
            defaults={
                'phone': '1234567890',
                'expertise': 'Technical Skills'
            }
        )

        judge2, _ = Judge.objects.get_or_create(
            user=judge2_user,
            defaults={
                'phone': '0987654321',
                'expertise': 'Performance'
            }
        )

        # Create participants with names that will help demonstrate alphabetical tiebreaker
        participants_data = [
            ('Alice Anderson', 'alice@example.com', '1111111111'),
            ('Bob Brown', 'bob@example.com', '2222222222'),
            ('Charlie Cooper', 'charlie@example.com', '3333333333'),
            ('David Davis', 'david@example.com', '4444444444'),
        ]

        participants = []
        for name, email, phone in participants_data:
            participant, _ = Participant.objects.get_or_create(
                email=email,
                defaults={
                    'name': name,
                    'phone': phone
                }
            )
            participants.append(participant)

        # Create competition
        competition = Competition.objects.create(
            name=f'Tie Breaker Demo Competition {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            description='A competition to demonstrate tie breaker functionality',
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            status='ACTIVE',
            created_by=admin_user,
            show_results=True
        )

        # Create rounds with criteria
        rounds_data = [
            {
                'name': 'First Round',
                'criteria': [
                    ('Technical Skills', 10),
                    ('Innovation', 10),
                    ('Problem Solving', 10),
                ]
            },
            {
                'name': 'Final Round',
                'criteria': [
                    ('Performance', 10),
                    ('Quality', 10),
                    ('Impact', 10),
                ]
            }
        ]

        for round_idx, round_data in enumerate(rounds_data, 1):
            round_obj = Round.objects.create(
                competition=competition,
                name=round_data['name'],
                description=f'Round {round_idx}',
                order=round_idx,
                status='ONGOING',
                weight_percentage=50
            )

            for criterion_name, max_score in round_data['criteria']:
                Criterion.objects.create(
                    round=round_obj,
                    name=criterion_name,
                    description=f'Criterion for {criterion_name}',
                    max_score=max_score
                )

        # Assign participants to competition
        for idx, participant in enumerate(participants, 1):
            ParticipantCompetition.objects.create(
                participant=participant,
                competition=competition,
                number=idx
            )

        # Submit scores to create interesting tie scenarios
        for round_obj in competition.rounds.all():
            for criterion in round_obj.criteria.all():
                for judge in [judge1, judge2]:
                    for participant in participants:
                        # First round: All participants get 9.0
                        if round_obj.name == 'First Round':
                            score_value = 9.0
                        # Final round: Create interesting tie-breaking scenario
                        else:
                            if criterion.name == 'Performance':
                                # Alice and Bob tie with 9.5, Charlie and David tie with 9.0
                                score_value = 9.5 if participant.name in ['Alice Anderson', 'Bob Brown'] else 9.0
                            elif criterion.name == 'Quality':
                                # All get 9.0 to maintain overall tie
                                score_value = 9.0
                            else:  # Impact
                                # Bob and Charlie get 9.5, others 9.0
                                score_value = 9.5 if participant.name in ['Bob Brown', 'Charlie Cooper'] else 9.0

                        Score.objects.create(
                            participant=participant,
                            criterion=criterion,
                            judge=judge,
                            score=score_value,
                            status='SUBMITTED',
                            remarks='Test score'
                        )

        # Calculate results and rankings
        from competition_app.views import calculate_rankings
        for round_obj in competition.rounds.all():
            # Calculate total scores
            for participant in participants:
                total_score = sum(
                    score.score
                    for score in Score.objects.filter(
                        participant=participant,
                        criterion__round=round_obj,
                        status='SUBMITTED'
                    )
                ) / 2  # Average of two judges

                CompetitionResult.objects.create(
                    competition=competition,
                    participant=participant,
                    round=round_obj,
                    total_score=total_score,
                    rank=0  # Will be updated by calculate_rankings
                )

            # Calculate rankings
            calculate_rankings(round_obj)

        self.stdout.write(self.style.SUCCESS(
            'Successfully populated tie competition data with the following scenario:\n'
            '- All participants have the same total score in the First Round\n'
            '- In the Final Round:\n'
            '  * Alice and Bob tie for higher scores in Performance\n'
            '  * Bob and Charlie tie for higher scores in Impact\n'
            '  * All tie in Quality\n'
            'This creates an interesting tie-breaking scenario!'
        ))

