from django import template

register = template.Library()

@register.filter
def get_score(score_lookup, ids):
    """Gets score from lookup dictionary using participant and criterion IDs"""
    participant_id, criterion_id = ids.split(',')
    return score_lookup.get((int(participant_id), int(criterion_id)), '')

@register.filter
def get_remarks(score_lookup, key_pair):
    """Get remarks value from lookup dictionary"""
    participant_id, criterion_id = key_pair
    key = f"{participant_id}_{criterion_id}"
    score = score_lookup.get(key)
    return score.remarks if score else ''

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get item from dictionary with nested lookup support"""
    if dictionary is None:
        return 0
    
    # Handle nested dictionary lookups
    if isinstance(key, str) and '.' in key:
        keys = key.split('.')
        value = dictionary
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, {})
            else:
                return 0
        return value if value != {} else 0
    
    # Handle direct dictionary lookup
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    
    # Handle attribute lookup
    try:
        return getattr(dictionary, str(key), 0)
    except (TypeError, AttributeError):
        return 0