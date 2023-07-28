import logging
import httpx
from django.conf import settings
from django.http import JsonResponse, HttpRequest
from django.shortcuts import render, get_object_or_404
from .forms import MessageForm, ContactForm
from .models import Contact, Message, MyNews
from .tasks import send_discord_message, send_contact_email

logger = logging.getLogger('app')


def home_view(request):
    # View: /
    logger.debug('home_view')
    logger.debug('is_secure: %s', request.is_secure())
    # logger.debug('-'*20)
    # logger.debug(request.META)
    # logger.debug('-'*20)
    # logger.debug(request.body)
    # logger.debug('-'*20)
    return render(request, 'home.html')


def news_view(request):
    # View: /news/
    logger.debug('news_view')
    q = MyNews.objects.get_active().order_by('-pk')
    return render(request, 'news.html', {'news': q})


def message_view(request):
    # View: /message/
    logger.debug('message_view')
    if not request.method == 'POST':
        return render(request, 'message.html')

    try:
        logger.debug(request.POST)
        form = MessageForm(request.POST)
        if not form.is_valid():
            return JsonResponse(form.errors, status=400)

        if not request.user.is_authenticated and not google_verify(request):
            data = {'error_message': 'Google CAPTCHA not verified.'}
            return JsonResponse(data, status=400)

        message = Message.objects.create(
            name=form.cleaned_data['name'],
            message=form.cleaned_data['message'],
        )
        send_discord_message.delay(message.pk)
        return JsonResponse({}, status=204)

    except Exception as error:
        logger.exception(error)
        return JsonResponse({'error_message': str(error)}, status=400)


def contact_view(request):
    # View: /contact/
    logger.debug('contact_view')
    if not request.method == 'POST':
        return render(request, 'contact.html')

    try:
        logger.debug(request.POST)
        form = ContactForm(request.POST)
        if not form.is_valid():
            return JsonResponse(form.errors, status=400)

        if not request.user.is_authenticated and not google_verify(request):
            data = {'error_message': 'Google CAPTCHA not verified.'}
            return JsonResponse(data, status=400)

        contact = Contact.objects.create(
            email=form.cleaned_data['email'],
            subject=form.cleaned_data['subject'],
            message=form.cleaned_data['message'],
            send_copy=form.cleaned_data['send_copy'],
        )
        logger.debug(contact.pk)
        send_contact_email.delay(contact.pk)
        return JsonResponse({}, status=204)

    except Exception as error:
        logger.exception(error)
        return JsonResponse({'error_message': str(error)}, status=400)


def contact_html_view(request, view, uuid):
    # View: /contact/{view}/{uuid}/
    logger.debug('contact_html_view: (view, uuid): (%s, %s)', view, uuid)
    if view == 'browser':
        template = 'email/contact.html'
    else:
        template = 'contact/browser-view.html'

    q = get_object_or_404(Contact, uuid=uuid)
    context = {'contact': q, 'browser': True}
    return render(request, template, context)


def google_verify(request: HttpRequest) -> bool:
    if 'g_verified' in request.session and request.session['g_verified']:
        return True
    try:
        url = 'https://www.google.com/recaptcha/api/siteverify'
        data = {
            'secret': settings.GOOGLE_SITE_SECRET,
            'response': request.POST['g-recaptcha-response']
        }
        r = httpx.post(url, data=data, timeout=10)
        if r.is_success:
            if r.json()['success']:
                request.session['g_verified'] = True
                return True
        return False
    except Exception as error:
        logger.exception(error)
        return False
