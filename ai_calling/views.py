import datetime
import json
import logging
import os
import re
import time
import uuid
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

try:
    from livekit.api import AccessToken, VideoGrants, RoomConfiguration, RoomAgentDispatch
    LIVEKIT_API_AVAILABLE = True
except ImportError:
    LIVEKIT_API_AVAILABLE = False

from .models import ResumeKnowledgeChunk, ChatInteraction
from .rag_service import ask_gemini_assistant, generate_smart_resume_fallback_answer

logger = logging.getLogger(__name__)


def voice_webhook(request):
    """
    Preserved pre-existing telephony/voice webhook endpoint.
    """
    response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>
        Hello! You have reached Daniel's AI assistant.
        This is currently a test call.
    </Say>
</Response>
"""
    return HttpResponse(response, content_type="text/xml")


@ensure_csrf_cookie
@require_POST
def livekit_token_endpoint(request):
    """
    Secure REST API endpoint to generate short-lived LiveKit access tokens
    for WebRTC voice assistant sessions.

    Guarantees:
    - Minimum least-privilege room permissions (no admin rights).
    - Unique room identifier per visitor to prevent crosstalk.
    - Sliding window rate limiting.
    - Server secrets (LIVEKIT_API_SECRET, GEMINI_API_KEY) are never exposed.
    """
    try:
        # Rate limit by client IP
        client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR", "unknown")
        )
        if is_rate_limited(client_ip):
            logger.warning("[AI Calling] Token rate limit exceeded for IP: %s", client_ip)
            return JsonResponse(
                {
                    "success": False,
                    "error": "You are requesting voice connections too quickly. Please pause a moment.",
                },
                status=429
            )

        webrtc_enabled = getattr(settings, "ENABLE_WEBRTC_VOICE", True)
        if not webrtc_enabled:
            return JsonResponse(
                {
                    "success": False,
                    "error": "WebRTC voice mode is currently disabled in configuration.",
                    "fallback_available": True,
                },
                status=503
            )

        if not LIVEKIT_API_AVAILABLE:
            logger.error("[AI Calling] livekit-api package is not installed.")
            return JsonResponse(
                {
                    "success": False,
                    "error": "LiveKit API package is not available on server.",
                    "fallback_available": True,
                },
                status=503
            )

        livekit_url = getattr(settings, "LIVEKIT_URL", None)
        if livekit_url is None:
            livekit_url = os.environ.get("LIVEKIT_URL", "")

        api_key = getattr(settings, "LIVEKIT_API_KEY", None)
        if api_key is None:
            api_key = os.environ.get("LIVEKIT_API_KEY", "")

        api_secret = getattr(settings, "LIVEKIT_API_SECRET", None)
        if api_secret is None:
            api_secret = os.environ.get("LIVEKIT_API_SECRET", "")

        if not livekit_url or not api_key or not api_secret:
            logger.warning("[AI Calling] LiveKit configuration missing (URL, API key, or secret).")
            return JsonResponse(
                {
                    "success": False,
                    "error": "LiveKit voice server configuration is missing on the server.",
                    "fallback_available": True,
                },
                status=503
            )

        # Parse request body if JSON sent
        room_name = ""
        if request.body:
            try:
                data = json.loads(request.body.decode("utf-8"))
                if not isinstance(data, dict):
                    return JsonResponse(
                        {"success": False, "error": "Invalid JSON payload: expected a JSON object."},
                        status=400
                    )
                requested_room = (data.get("room") or "").strip()
                if requested_room and re.match(r"^[a-zA-Z0-9_\-]{6,64}$", requested_room):
                    room_name = requested_room
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse(
                    {"success": False, "error": "Malformed JSON body provided."},
                    status=400
                )

        if not room_name:
            room_name = f"portfolio-{uuid.uuid4().hex[:12]}"

        session = getattr(request, "session", None)
        session_id = getattr(session, "session_key", None)
        visitor_id = session_id[:8] if session_id else uuid.uuid4().hex[:8]
        identity = f"visitor-{visitor_id}"
        participant_name = "Portfolio Visitor"

        # Determine configured real-time voice agent name for explicit dispatch
        agent_name = (
            getattr(settings, "LIVEKIT_AGENT_NAME", None)
            or os.environ.get("LIVEKIT_AGENT_NAME", "daniel-portfolio-voice-agent")
        )

        # Generate short-lived token (15 minutes) with least-privilege grants
        token = (
            AccessToken(api_key, api_secret)
            .with_identity(identity)
            .with_name(participant_name)
            .with_ttl(datetime.timedelta(minutes=15))
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                    can_update_own_metadata=True,
                    room_admin=False,
                    room_record=False,
                )
            )
        )

        # Attach explicit RoomAgentDispatch to guarantee LiveKit Cloud launches the Python worker
        if agent_name:
            try:
                room_config = RoomConfiguration(
                    name=room_name,
                    agents=[RoomAgentDispatch(agent_name=agent_name)],
                )
                token = token.with_room_config(room_config)
            except Exception as rc_err:
                logger.warning("[AI Calling] Unable to attach room_config dispatch: %s", rc_err)

        jwt_token = token.to_jwt()

        return JsonResponse(
            {
                "success": True,
                "url": livekit_url,
                "token": jwt_token,
                "room": room_name,
                "room_name": room_name,
                "identity": identity,
                "expires_in": 900,
            },
            status=200
        )

    except Exception as exc:
        logger.exception("[AI Calling] Failed to generate LiveKit token: %s", exc)
        return JsonResponse(
            {
                "success": False,
                "error": "Failed to generate voice session credentials. Please try again.",
                "fallback_available": True,
            },
            status=500
        )



# In-memory sliding window rate limiter for the chat endpoint
# Format: {ip_or_session: [timestamp1, timestamp2, ...]}
_RATE_LIMIT_STORE = {}
RATE_LIMIT_MAX_REQUESTS = 15
RATE_LIMIT_WINDOW_SECONDS = 60


def is_rate_limited(identifier: str) -> bool:
    """Returns True if the identifier exceeds RATE_LIMIT_MAX_REQUESTS per window."""
    now = time.time()
    timestamps = _RATE_LIMIT_STORE.get(identifier, [])
    # Filter timestamps within current window
    valid_timestamps = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW_SECONDS]
    
    if len(valid_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        _RATE_LIMIT_STORE[identifier] = valid_timestamps
        return True
    
    valid_timestamps.append(now)
    _RATE_LIMIT_STORE[identifier] = valid_timestamps
    return False


@ensure_csrf_cookie
@require_POST
def chat_endpoint(request):
    """
    Secure REST API endpoint for Daniel's floating portfolio AI chatbot.
    Receives JSON: {"message": str, "history": list}
    Returns JSON: {"success": bool, "answer": str, ...}
    Guaranteed to NEVER return an unhandled 500.
    """
    try:
        # Rate limit by client IP or session key
        client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR", "unknown")
        )
        if is_rate_limited(client_ip):
            logger.warning("Rate limit exceeded for IP: %s", client_ip)
            return JsonResponse(
                {
                    "success": False,
                    "error": "You are asking questions a bit too quickly. Please pause for a moment before trying again.",
                    "answer": "You are sending messages quickly! Please wait a few seconds before asking your next question.",
                },
                status=429
            )

        try:
            data = json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return JsonResponse(
                {"success": False, "error": "Invalid JSON payload sent to chat endpoint."},
                status=400
            )

        user_message = (data.get("message") or "").strip()
        chat_history = data.get("history") or []

        # Input validation
        if not user_message:
            return JsonResponse(
                {"success": False, "error": "Message text cannot be empty."},
                status=400
            )

        if len(user_message) > 600:
            return JsonResponse(
                {"success": False, "error": "Message is too long. Please keep your question under 600 characters."},
                status=400
            )

        # Ensure knowledge chunks exist; if empty, import default chunks automatically
        try:
            if ResumeKnowledgeChunk.objects.filter(is_active=True).count() == 0:
                from django.core.management import call_command
                try:
                    call_command("load_resume_knowledge")
                except Exception as seed_err:
                    logger.error("[AI Calling] Auto-seeding resume knowledge failed: %s", seed_err)
        except Exception as db_check_err:
            logger.warning("[AI Calling] Knowledge chunk database check failed: %s", db_check_err)

        # Call Gemini RAG pipeline safely
        session = getattr(request, "session", None)
        session_id = getattr(session, "session_key", None) or client_ip[:32]

        try:
            result = ask_gemini_assistant(user_message, chat_history=chat_history)
        except Exception as gemini_err:
            logger.exception("[AI Calling] Uncaught exception calling ask_gemini_assistant: %s", gemini_err)
            safe_ans = generate_smart_resume_fallback_answer(user_message)
            result = {
                "success": True,
                "answer": safe_ans,
                "chunk_ids": [],
                "latency_ms": 1,
                "fallback_mode": True,
            }

        # Attach clean speech text and audio URL for AI voice generation
        raw_answer = result.get("answer", "")
        try:
            clean_speech = clean_text_for_speech(raw_answer)
            result["speech_text"] = clean_speech
            if clean_speech:
                import urllib.parse
                result["audio_url"] = f"/ai-calling/tts/?text={urllib.parse.quote(clean_speech)}"
            else:
                result["audio_url"] = ""
        except Exception as speech_err:
            logger.warning("[AI Calling] Speech text conversion failed: %s", speech_err)
            result["speech_text"] = ""
            result["audio_url"] = ""

        # Record lightweight interaction for auditing
        try:
            ChatInteraction.objects.create(
                session_id=session_id,
                user_message=user_message,
                assistant_response=raw_answer,
                retrieved_chunk_ids=result.get("chunk_ids", []),
                response_time_ms=result.get("latency_ms", 0),
            )
        except Exception as log_err:
            logger.warning("[AI Calling] Failed to save ChatInteraction log: %s", log_err)

        return JsonResponse(result, status=200)

    except Exception as fatal_err:
        logger.exception("[AI Calling] Fatal uncaught exception in chat_endpoint: %s", fatal_err)
        extracted_msg = user_message if 'user_message' in locals() else ""
        fallback_ans = generate_smart_resume_fallback_answer(extracted_msg)
        clean_speech = clean_text_for_speech(fallback_ans)
        import urllib.parse
        return JsonResponse({
            "success": True,
            "answer": fallback_ans,
            "speech_text": clean_speech,
            "audio_url": f"/ai-calling/tts/?text={urllib.parse.quote(clean_speech)}" if clean_speech else "",
            "chunk_ids": [],
            "latency_ms": 1,
            "fallback_mode": True,
        }, status=200)



def clean_text_for_speech(text: str) -> str:
    """Removes Markdown, HTML, URLs, bullet points, and code formatting for speech generation."""
    import re
    if not text:
        return ""
    # Strip markdown headers, bold, italics, links, backticks
    text = re.sub(r"```[\s\S]*?```", "code block", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"[`#_~*•—]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tts_endpoint(request):
    """
    High-quality Text-to-Speech audio streaming endpoint.
    Converts assistant answers into natural voice audio (MP3).
    Supports chunking and caching.
    """
    import urllib.parse
    import re
    import requests

    text = request.GET.get("text", "").strip()
    if not text and request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8"))
            text = body.get("text", "").strip()
        except Exception:
            pass

    clean_text = clean_text_for_speech(text)
    if not clean_text:
        return HttpResponse("Missing or empty text parameter", status=400)

    # Cap text length to prevent abuse (up to 600 characters)
    clean_text = clean_text[:600]

    # Chunk text by sentences/phrases into chunks <= 160 characters
    sentences = re.split(r"(?<=[.!?])\s+", clean_text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) + 1 <= 160:
            current = (current + " " + s).strip()
        else:
            if current:
                chunks.append(current)
            if len(s) > 160:
                words = s.split(" ")
                sub = ""
                for w in words:
                    if len(sub) + len(w) + 1 <= 160:
                        sub = (sub + " " + w).strip()
                    else:
                        if sub:
                            chunks.append(sub)
                        sub = w
                if sub:
                    chunks.append(sub)
                current = ""
            else:
                current = s
    if current:
        chunks.append(current)

    audio_bytes = bytearray()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        for chunk in chunks:
            chunk_url = (
                f"https://translate.google.com/translate_tts?ie=UTF-8&q="
                f"{urllib.parse.quote(chunk)}&tl=en&client=tw-ob"
            )
            res = requests.get(chunk_url, headers=headers, timeout=8)
            if res.status_code == 200:
                audio_bytes.extend(res.content)
            else:
                logger.warning("TTS audio chunk returned status %s", res.status_code)
                break

        if audio_bytes:
            response = HttpResponse(bytes(audio_bytes), content_type="audio/mpeg")
            response["Cache-Control"] = "public, max-age=86400"
            return response
    except Exception as e:
        logger.error("TTS generation error: %s", e)

    return HttpResponse("TTS audio synthesis failed", status=502)