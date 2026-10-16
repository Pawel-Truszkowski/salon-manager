"""Inviting a specialist to the panel: create her account without a password and e-mail a "set your password" link.

The link uses Django's password-reset token (`default_token_generator`). The token hashes the user's password, so it
stops working as soon as she sets one; otherwise it expires after `PASSWORD_RESET_TIMEOUT` (3 days by default).
The built-in "forgot password" form skips accounts without a usable password, hence this separate flow.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


def create_invited_account(employee, email):
    """Create a password-less account for `employee` (login = e-mail) and link it. Send the e-mail separately.

    The names are copied once as a starting point; the account's names may later differ from the public ones.
    """
    User = get_user_model()
    with transaction.atomic():
        user = User(
            username=email,
            email=email,
            first_name=employee.first_name,
            last_name=employee.last_name,
        )
        user.set_unusable_password()
        user.save()
        employee.user = user
        employee.save(update_fields=['user'])
    return user


def is_pending_invitation(user):
    """Invited but hasn't set a password yet."""
    return user is not None and not user.has_usable_password()


def invitation_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return settings.SITE_URL + reverse('panel:invitation_accept', kwargs={'uidb64': uid, 'token': token})


def send_invitation(user):
    """E-mail the "set your password" link. Raises on failure so the owner sees that it didn't go out."""
    context = {
        'user': user,
        'url': invitation_url(user),
        'valid_days': max(1, settings.PASSWORD_RESET_TIMEOUT // (24 * 60 * 60)),
    }
    send_mail(
        subject='Zaproszenie do panelu Royal Beauty',
        message=render_to_string('panel/emails/invitation.txt', context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=render_to_string('panel/emails/invitation.html', context),
    )
    logger.info(f"Sent panel invitation to user({user.pk})")
