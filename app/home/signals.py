from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .tasks import clear_news_cache
from .models import MyNews


@receiver(post_save, sender=MyNews)
@receiver(post_delete, sender=MyNews)
def clear_cache(sender, instance, **kwargs):
    clear_news_cache.delay()
