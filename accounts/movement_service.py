"""Server-side movement authority, scoped visibility and state transitions."""
from django.db.models import Q
from django.utils import timezone
from .models import StudentMovement, MovementEvent, StaffAccessGrant, SecurityEvent
from .security_service import eligible_account
from .school_access import grants_for
from .permissions import can_teach
from .connected_school import canonical

CLOSE_REASONS = (("entered_in_error","Entered in error"),
                 ("handover_confirmed","Responsibility handed over outside RollFlow"),
                 ("unresolved_followup","Unresolved — managed outside RollFlow"))


def authority(user):
    if not eligible_account(user):
        return False,False,set(),False
    grants=grants_for(user)
    admin=bool(user.is_staff and user.is_superuser)
    monitor=admin or any(g.scope=="school" and "movement_monitor" in g.capabilities for g in grants)
    reception={int(g.scope_value) for g in grants if g.scope=="destination" and "movement_receive" in g.capabilities}
    return admin,monitor,reception,can_teach(user)


def may_access(user):
    admin,monitor,reception,teacher=authority(user)
    return admin or monitor or bool(reception) or teacher


def visible(user):
    admin,monitor,reception,teacher=authority(user)
    qs=StudentMovement.objects.select_related("student","issuer","destination","publication")
    if monitor:
        return qs
    condition=Q(pk__in=[])
    if reception:
        condition |= Q(destination_id__in=reception,requires_reception=True)
    if teacher:
        condition |= Q(issuer=user)
    return qs.filter(condition)


def identity_matches(movement):
    return movement.publication.snapshot.get("student_identity",{}).get(str(movement.student_id)) == canonical(movement.student.student_id) and bool(canonical(movement.student.student_id))


def actions_for(user,movement):
    if movement.closed_at:
        return []
    admin,monitor,reception,teacher=authority(user)
    issuer=teacher and movement.issuer_id==user.pk
    receiver=movement.requires_reception and (admin or movement.destination_id in reception)
    allowed=[]
    if identity_matches(movement):
        if receiver and movement.state=="outbound":
            allowed.append(("arrive","Confirm arrival"))
        if receiver and movement.state=="arrived":
            allowed.append(("release","Release to classroom"))
        if issuer and (movement.state=="returning" or (movement.state=="outbound" and not movement.requires_reception)):
            allowed.append(("return","Confirm classroom return"))
    if admin:
        allowed.append(("close","Administrative closure"))
    return allowed


def record(movement,actor,action,previous="",reason=""):
    MovementEvent.objects.create(movement=movement,revision=movement.revision,actor=actor,
        action=action,from_state=previous,to_state=movement.state,reason_code=reason)
    SecurityEvent.objects.create(actor=actor,event="movement_"+action,subject=str(movement.pk))


def transition(movement,actor,action,revision,reason=""):
    if str(movement.revision)!=revision:
        raise ValueError("Movement changed. Refresh before recording an event.")
    if action not in dict(actions_for(actor,movement)):
        raise PermissionError("Action not authorised for this movement and state.")
    old=movement.state
    target={"arrive":"arrived","release":"returning","return":"returned","close":"closed"}[action]
    if action=="close" and reason not in dict(CLOSE_REASONS):
        raise ValueError("Select an administrative closure reason.")
    movement.state=target
    movement.revision+=1
    if target in ("returned","closed"):
        movement.closed_at=timezone.now()
    movement.save(update_fields=["state","revision","closed_at"])
    record(movement,actor,action,old,reason if action=="close" else "")
