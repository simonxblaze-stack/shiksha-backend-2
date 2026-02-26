from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from livekit.api import WebhookReceiver


@csrf_exempt
def livekit_webhook(request):
    receiver = WebhookReceiver(settings.LIVEKIT_WEBHOOK_SECRET)

    try:
        event = receiver.receive(
            request.body,
            request.headers.get("Authorization"),
        )
    except Exception as e:
        print("Webhook error:", e)
        return HttpResponse(status=400)

    print("LiveKit Event:", event.event)

    return HttpResponse(status=200)