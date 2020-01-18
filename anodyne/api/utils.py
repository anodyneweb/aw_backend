from django.core.mail import get_connection, EmailMultiAlternatives


def send_mail(subject, message, from_email,
              recipient_list, bcc=None, cc=None,
              fail_silently=False, auth_user=None,
              auth_password=None, connection=None, attachments=None,
              headers=None, alternatives=None, reply_to=[],
              html_message=None):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.

    If auth_user is None, use the EMAIL_HOST_USER setting.
    If auth_password is None, use the EMAIL_HOST_PASSWORD setting.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    connection = connection or get_connection(
        username=auth_user,
        password=auth_password,
        fail_silently=fail_silently,
    )
    mail = EmailMultiAlternatives(
        subject=subject, body=message,
        from_email=from_email, to=recipient_list,
        bcc=bcc, connection=connection,
        attachments=attachments, headers=headers,
        alternatives=alternatives, cc=cc,
        reply_to=reply_to
    )
    if html_message:
        mail.attach_alternative(html_message, 'text/html')

    return mail.send()
