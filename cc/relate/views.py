from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.db.models import Q
from django.contrib import messages

from cc.general.util import render
import cc.ripple.api as ripple
from cc.profile.models import Profile
from cc.relate.forms import EndorseForm, AcknowledgementForm
from cc.relate.models import Endorsement
from cc.feed.models import FeedItem


MESSAGES = {
    'endorsement_saved': "Endorsement saved.",
    'endorsement_deleted': "Endorsement deleted.",
}

@login_required
@render()
def endorse_user(request, recipient_username):
    recipient = get_object_or_404(Profile, user__username=recipient_username)
    if recipient == request.profile:
        raise Http404()
    try:
        endorsement = Endorsement.objects.get(
            endorser=request.profile, recipient=recipient)
    except Endorsement.DoesNotExist:
        endorsement = None
    if request.method == 'POST':
        if 'delete' in request.POST and endorsement:
            endorsement.delete()
            messages.info(request, MESSAGES['endorsement_deleted'])
            return HttpResponseRedirect(
                endorsement.recipient.get_absolute_url())
        form = EndorseForm(request.POST, instance=endorsement,
                           endorser=request.profile, recipient=recipient)
        if form.is_valid():
            endorsement = form.save()
            messages.info(request, MESSAGES['endorsement_saved'])
            return HttpResponseRedirect(endorsement.get_absolute_url())
    else:
        form = EndorseForm(instance=endorsement, endorser=request.profile,
                           recipient=recipient)
    profile = recipient  # For profile_base.html.
    return locals()

@login_required
@render()
def endorsement(request, endorsement_id):
    endorsement = get_object_or_404(Endorsement, pk=endorsement_id)
    return locals()
    
@login_required
@render()
def relationships(request):
    accounts = ripple.get_user_accounts(request.profile)
    return locals()

@login_required
@render()
def relationship(request, partner_username):
    partner = get_object_or_404(Profile, user__username=partner_username)
    if partner == request.profile:
        raise Http404  # Can't have relationship with yourself.
    account = request.profile.account(partner)
    if account:
        entries = account.entries 
        balance = account.balance
    else:
        entries = []
        balance = 0
    profile = partner  # For profile_base.html.
    return locals()

@login_required
@render()
def acknowledge_user(request, recipient_username):
    recipient = get_object_or_404(Profile, user__username=recipient_username)
    if recipient == request.profile:
        raise Http404
    # TODO: Don't recompute max_amount on form submit?  Cache, or put in form
    # as hidden field?
    max_amount = ripple.max_payment(request.profile, recipient)
    if request.method == 'POST':
        form = AcknowledgementForm(request.POST, max_ripple=max_amount)
        if form.is_valid():
            acknowledgement = form.send_acknowledgement(
                request.profile, recipient)
            return HttpResponseRedirect(acknowledgement.get_absolute_url())
    else:
        form = AcknowledgementForm(max_ripple=max_amount)
    can_ripple = max_amount > 0
    profile = recipient  # For profile_base.html.
    return locals()

@login_required
@render()
def view_acknowledgement(request, payment_id):
    payment = ripple.get_payment(payment_id)
    entries = payment.entries_for_user(request.profile)
    if not entries:
        raise Http404  # Non-participants don't get to see anything.
    sent_entries = []
    received_entries = []
    for entry in entries:
        if entry.amount < 0:
            sent_entries.append(entry)
        else:
            received_entries.append(entry)
    return locals()
