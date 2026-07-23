from allauth.account.models import EmailAddress

from talentleads.utils import get_talentleads_logger

logger = get_talentleads_logger(__name__)


def add_users_context(context, user):
    try:
        context["email_verified"] = EmailAddress.objects.get_for_user(user, user.email).verified
    except EmailAddress.DoesNotExist:
        logger.warning("User doesn't have a Verfiied Email")

    return context
