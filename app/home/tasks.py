import logging
import httpx
from celery import shared_task
from django.conf import settings
from django.core import management
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import Contact, Message

logger = logging.getLogger('celery')


@shared_task()
def clear_sessions():
    # Cleanup session data for supported backends
    logger.info('clear_sessions')
    return management.call_command('clearsessions')


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 10})
def flush_template_cache():
    # Flush template cache on request
    logger.info('flush_template_cache')
    return cache.delete_pattern('template.cache.*')


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 30})
def clear_news_cache():
    # Clear News cache on model update
    logger.info('clear_news_cache')
    return cache.delete(make_template_fragment_key('news_body'))


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 60}, rate_limit='10/m')
def send_discord_message(pk):
    logger.info('send_discord_message: pk: %s', pk)
    message = Message.objects.get(pk=pk)
    context = {'name': message.name, 'message': message.message}
    discord_message = render_to_string('message/discord-message.html', context)
    logger.info(discord_message)
    data = {'content': discord_message}
    r = httpx.post(settings.DISCORD_WEBHOOK, json=data, timeout=10)
    logger.debug(r.status_code)
    if not r.is_success:
        logger.warning(r.content)
        r.raise_for_status()
    return r.status_code


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 60}, rate_limit='10/m')
def send_contact_email(pk):
    logger.info('send_contact_email: pk: %s', pk)
    contact = Contact.objects.get(pk=pk)
    context = {'contact': contact, 'browser': False}
    msg_html = render_to_string('email/contact.html', context)
    msg_plain = render_to_string('email/contact.plain', context)
    subject = f'Contact Form: {contact.subject}'
    send_mail_wrapper([settings.CONTACT_FORM_TO_EMAIL], subject, msg_plain, msg_html)
    if contact.send_copy:
        send_mail_wrapper([contact.email], subject, msg_plain, msg_html)


def send_mail_wrapper(recipient_list, subject, message, html_message):
    """
    :param recipient_list: list
    :param subject: str
    :param message: str
    :param html_message: str
    :return: django.core.mail.send_mail
    """
    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
        html_message=html_message,
    )
