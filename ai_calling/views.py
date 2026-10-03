from django.http import HttpResponse


def voice_webhook(request):
    response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>
        Hello! You have reached Daniel's AI assistant.
        This is currently a test call.
    </Say>
</Response>
"""
    return HttpResponse(response, content_type="text/xml")