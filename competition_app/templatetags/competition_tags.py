from django import template
from competition_app.models import Participant

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_participant(competition, participant_id):
    """Get participant object from competition by ID"""
    try:
        return competition.participants.get(id=participant_id)
    except Participant.DoesNotExist:
        return None

@register.filter
def average(value_list):
    """Calculate average of a list of values"""
    try:
        return sum(value_list) / len(value_list)
    except (TypeError, ZeroDivisionError):
        return 0


