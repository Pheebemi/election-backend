"""Record every change to results in ResultChange.

Saves are always recorded. Deletes are recorded when a person did them (the
admin site sets ``_changed_by``); bulk clean-ups in seed scripts are not.
Views and admin can set ``instance._changed_by`` to name who made the change;
otherwise the result's ``entered_by`` is used.
"""
from django.db.models.signals import post_delete, post_save, pre_save

from .models import ApcElectionResult, ApcWardResult, ElectionResult, ResultChange, WardResult

# Proxy models (the APC admin) send signals under their own class, so list them too.
RESULT_MODELS = (ElectionResult, WardResult, ApcElectionResult, ApcWardResult)


def _place(instance):
    if isinstance(instance, WardResult):
        ward = instance.ward
        return ResultChange.WARD, ward.lga, ward, None, f"{ward.lga.name} · {ward.name} ward (override)"
    pu = instance.polling_unit
    ward = pu.ward
    return ResultChange.POLLING_UNIT, ward.lga, ward, pu, f"{ward.lga.name} · {ward.name} · {pu.name}"


def _record(instance, action, old, new):
    kind, lga, ward, pu, place = _place(instance)
    user = getattr(instance, '_changed_by', None) or instance.entered_by
    ResultChange.objects.create(
        kind=kind, action=action, dataset=instance.dataset,
        lga=lga, ward=ward, polling_unit=pu, party=instance.party,
        place=place[:255], party_abbreviation=instance.party.abbreviation,
        old_votes=old, new_votes=new,
        changed_by=user if user and user.pk else None,
        changed_by_name=user.username if user and user.pk else '',
    )


def remember_old_votes(sender, instance, **kwargs):
    instance._old_votes = (
        type(instance).objects.filter(pk=instance.pk).values_list('votes', flat=True).first()
        if instance.pk else None
    )


def record_save(sender, instance, created, **kwargs):
    old = getattr(instance, '_old_votes', None)
    if created:
        _record(instance, ResultChange.CREATED, None, instance.votes)
    elif old != instance.votes:
        _record(instance, ResultChange.UPDATED, old, instance.votes)


def record_delete(sender, instance, **kwargs):
    if getattr(instance, '_changed_by', None) is not None:
        _record(instance, ResultChange.DELETED, instance.votes, None)


for _model in RESULT_MODELS:
    pre_save.connect(remember_old_votes, sender=_model, dispatch_uid=f'history-pre-{_model.__name__}')
    post_save.connect(record_save, sender=_model, dispatch_uid=f'history-save-{_model.__name__}')
    post_delete.connect(record_delete, sender=_model, dispatch_uid=f'history-delete-{_model.__name__}')
