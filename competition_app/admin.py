from django.contrib import admin
from .models import (
    Competition, Round, Criterion, Participant, Judge, Score, 
    CompetitionResult, JudgeAssignment, ParticipantCompetition
)

@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'status', 'created_by')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description')
    date_hierarchy = 'start_date'

@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ('competition', 'name', 'order', 'status', 'weight_percentage')
    list_filter = ('status', 'competition')
    search_fields = ('name', 'description')
    ordering = ('competition', 'order')

@admin.register(Criterion)
class CriterionAdmin(admin.ModelAdmin):
    list_display = ('name', 'round', 'max_score',)
    list_filter = ('round',)
    search_fields = ('name', 'description')

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'status', 'registration_date')
    list_filter = ('status',)
    search_fields = ('name', 'email', 'phone')
    date_hierarchy = 'registration_date'

@admin.register(ParticipantCompetition)
class ParticipantCompetitionAdmin(admin.ModelAdmin):
    list_display = ('participant', 'competition', 'number', 'registration_date')
    list_filter = ('competition', 'registration_date')
    search_fields = ('participant__name', 'competition__name')
    date_hierarchy = 'registration_date'

@admin.register(Judge)
class JudgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name',)
    date_hierarchy = 'created_at'

@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('participant', 'criterion', 'judge', 'score', 'status', 'timestamp')
    list_filter = ('status', 'criterion', 'judge')
    search_fields = ('participant__name', 'criterion__name', 'judge__user__username')
    date_hierarchy = 'timestamp'

@admin.register(CompetitionResult)
class CompetitionResultAdmin(admin.ModelAdmin):
    list_display = ('competition', 'participant', 'round', 'total_score', 'rank', 'timestamp')
    list_filter = ('competition', 'round')
    search_fields = ('participant__name',)
    date_hierarchy = 'timestamp'

@admin.register(JudgeAssignment)
class JudgeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('judge', 'competition', 'status', 'assigned_at')
    list_filter = ('status', 'competition', 'judge')
    search_fields = ('judge__user__username', 'competition__name')
    filter_horizontal = ('rounds',)
