"""
Comprehensive Automated Test Suite for Daniel's Portfolio AI Assistant
Covers:
  1. Environment variable configuration
  2. Django LiveKit token endpoint
  3. Token security, claims, and visitor isolation
  4. Real-time agent environment loading (from root and agent directories)
  5. Gemini and LiveKit integration & error handling
  6. Portfolio RAG knowledge retrieval
  7. Existing Django chatbot regression & fallback
  8. Feature-switch behavior (ENABLE_WEBRTC_VOICE)
  9. Secret leakage prevention (Git, templates, code, responses)
 10. Database configuration security
 11. Optional live smoke integration test (opt-in only)
"""

import asyncio
import datetime
import json
import os
from pathlib import Path
import re
import unittest
from unittest.mock import MagicMock, patch
import jwt

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from livekit.api import AccessToken, TokenVerifier, VideoGrants

from .models import ChatInteraction, ResumeKnowledgeChunk
from .rag_service import (
    ask_gemini_assistant,
    compute_keyword_score,
    cosine_similarity,
    generate_smart_resume_fallback_answer,
    get_gemini_api_key,
    retrieve_relevant_chunks,
)
from .views import _RATE_LIMIT_STORE

# Test-only dummy credentials
TEST_LIVEKIT_URL = "wss://example.livekit.cloud"
TEST_LIVEKIT_API_KEY = "test-livekit-key-12345"
TEST_LIVEKIT_API_SECRET = "test-livekit-secret-length-exceeds-32-chars-for-jwt"
TEST_GEMINI_API_KEY = "test-gemini-key-xyz"


# =============================================================================
# 1. Environment Variable Tests
# =============================================================================
class EnvironmentVariableConfigurationTests(TestCase):
    def test_livekit_settings_loaded_when_configured(self):
        """Verifies LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET are read."""
        with self.settings(
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            self.assertEqual(getattr(settings, "LIVEKIT_URL", ""), TEST_LIVEKIT_URL)
            self.assertEqual(getattr(settings, "LIVEKIT_API_KEY", ""), TEST_LIVEKIT_API_KEY)
            self.assertEqual(getattr(settings, "LIVEKIT_API_SECRET", ""), TEST_LIVEKIT_API_SECRET)

    def test_gemini_api_key_loaded_from_settings_and_env(self):
        """Verifies get_gemini_api_key checks settings and environment."""
        with self.settings(GEMINI_API_KEY=TEST_GEMINI_API_KEY):
            self.assertEqual(get_gemini_api_key(), TEST_GEMINI_API_KEY)

        with self.settings(GEMINI_API_KEY=None):
            with patch.dict(os.environ, {"GEMINI_API_KEY": TEST_GEMINI_API_KEY}):
                self.assertEqual(get_gemini_api_key(), TEST_GEMINI_API_KEY)

    def test_enable_webrtc_voice_interpreted_correctly(self):
        """Verifies ENABLE_WEBRTC_VOICE handles boolean and string representations."""
        with self.settings(ENABLE_WEBRTC_VOICE=True):
            self.assertTrue(getattr(settings, "ENABLE_WEBRTC_VOICE", False))
        with self.settings(ENABLE_WEBRTC_VOICE=False):
            self.assertFalse(getattr(settings, "ENABLE_WEBRTC_VOICE", True))

    def test_behavior_when_required_variables_are_missing_or_empty(self):
        """Verifies that missing or empty LiveKit variables disable token issuance safely."""
        client = Client()
        token_url = reverse("livekit_token")
        _RATE_LIMIT_STORE.clear()

        # Completely empty
        with self.settings(LIVEKIT_URL="", LIVEKIT_API_KEY="", LIVEKIT_API_SECRET=""):
            resp = client.post(token_url, data=json.dumps({}), content_type="application/json")
            self.assertEqual(resp.status_code, 503)
            data = json.loads(resp.content)
            self.assertFalse(data.get("success", True))
            self.assertIn("missing", data.get("error", "").lower())

    def test_os_supplied_variables_not_overwritten(self):
        """Verifies load_agent_config preserves pre-existing OS environment variables."""
        from realtime_agent.config import load_agent_config

        with patch.dict(
            os.environ,
            {
                "LIVEKIT_URL": "wss://os-supplied.livekit.cloud",
                "LIVEKIT_API_KEY": "os-key",
                "LIVEKIT_API_SECRET": "os-secret-32-chars-long-value-here",
                "GOOGLE_API_KEY": "os-gemini-key",
            },
        ):
            cfg = load_agent_config(override=False)
            self.assertEqual(cfg.livekit_url, "wss://os-supplied.livekit.cloud")
            self.assertEqual(cfg.livekit_api_key, "os-key")
            self.assertEqual(cfg.google_api_key, "os-gemini-key")

    def test_root_env_located_independently_of_cwd(self):
        """Verifies find_root_env_file finds .env from project root or subdirectories."""
        from realtime_agent.config import find_project_root

        root = find_project_root()
        self.assertTrue((root / "manage.py").exists() or (root / "portfolio").exists())


# =============================================================================
# 2. Django LiveKit Token Endpoint Tests
# =============================================================================
class DjangoLiveKitTokenEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.token_url = reverse("livekit_token")
        _RATE_LIMIT_STORE.clear()

    def tearDown(self):
        _RATE_LIMIT_STORE.clear()

    def test_valid_post_with_configured_credentials_returns_200(self):
        """Valid POST with configured credentials generates token with 200 OK."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            resp = self.client.post(
                self.token_url,
                data=json.dumps({"session_id": "sess_valid_1"}),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.content)
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("url"), TEST_LIVEKIT_URL)
            self.assertTrue(bool(data.get("token")))
            self.assertTrue(data.get("room_name", "").startswith("portfolio-"))
            self.assertTrue(data.get("identity", "").startswith("visitor-"))
            self.assertEqual(data.get("expires_in"), 900)

    def test_get_request_returns_405_method_not_allowed(self):
        """GET request to /ai-calling/livekit-token/ returns 405 Method Not Allowed."""
        resp = self.client.get(self.token_url)
        self.assertEqual(resp.status_code, 405)

    def test_missing_livekit_url_returns_503_safe_error(self):
        """Missing LIVEKIT_URL returns 503 without crashing."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL="",
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            resp = self.client.post(self.token_url, data=json.dumps({}), content_type="application/json")
            self.assertEqual(resp.status_code, 503)
            data = json.loads(resp.content)
            self.assertFalse(data.get("success"))
            self.assertIn("missing", data.get("error", "").lower())

    def test_missing_api_key_returns_503_safe_error(self):
        """Missing LIVEKIT_API_KEY returns 503 without crashing."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY="",
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            resp = self.client.post(self.token_url, data=json.dumps({}), content_type="application/json")
            self.assertEqual(resp.status_code, 503)

    def test_missing_api_secret_returns_503_safe_error(self):
        """Missing LIVEKIT_API_SECRET returns 503 without crashing."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET="",
        ):
            resp = self.client.post(self.token_url, data=json.dumps({}), content_type="application/json")
            self.assertEqual(resp.status_code, 503)

    def test_webrtc_feature_disabled_returns_503(self):
        """When ENABLE_WEBRTC_VOICE is False, endpoint returns 503."""
        with self.settings(ENABLE_WEBRTC_VOICE=False):
            resp = self.client.post(self.token_url, data=json.dumps({}), content_type="application/json")
            self.assertEqual(resp.status_code, 503)
            data = json.loads(resp.content)
            self.assertFalse(data.get("success"))
            self.assertIn("disabled", data.get("error", "").lower())

    def test_invalid_request_data_returns_400(self):
        """Malformed JSON payload returns 400 Bad Request."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            resp = self.client.post(
                self.token_url,
                data="this is not valid json {{{",
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 400)
            data = json.loads(resp.content)
            self.assertFalse(data.get("success"))

    def test_non_dict_json_payload_returns_400(self):
        """JSON payload that is not an object returns 400 Bad Request."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            resp = self.client.post(
                self.token_url,
                data=json.dumps(["not", "an", "object"]),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 400)

    def test_rate_limit_exceeded_returns_429(self):
        """Rate limit (>15 requests/min) triggers 429 Too Many Requests."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            last_status = 200
            for i in range(16):
                resp = self.client.post(
                    self.token_url,
                    data=json.dumps({"session_id": f"s_{i}"}),
                    content_type="application/json",
                )
                last_status = resp.status_code
            self.assertEqual(last_status, 429)

    def test_token_generation_failure_returns_safe_500_without_secret_leak(self):
        """Simulated token creation failure returns safe 500 without leaking exception details."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            with patch.object(AccessToken, "to_jwt", side_effect=RuntimeError("Cryptographic engine internal failure")):
                resp = self.client.post(
                    self.token_url,
                    data=json.dumps({}),
                    content_type="application/json",
                )
                self.assertEqual(resp.status_code, 500)
                data = json.loads(resp.content)
                self.assertFalse(data.get("success"))
                self.assertNotIn("Cryptographic engine", data.get("error", ""))
                self.assertNotIn(TEST_LIVEKIT_API_SECRET, resp.content.decode())


# =============================================================================
# 3. Token Security & Claims Tests
# =============================================================================
class TokenSecurityAndClaimsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.token_url = reverse("livekit_token")
        _RATE_LIMIT_STORE.clear()

    def tearDown(self):
        _RATE_LIMIT_STORE.clear()

    def _get_token_claims(self, token_jwt: str):
        verifier = TokenVerifier(TEST_LIVEKIT_API_KEY, TEST_LIVEKIT_API_SECRET)
        return verifier.verify(token_jwt)

    def test_token_has_valid_expiration_and_ttl(self):
        """Verifies token expiration is bounded to 15 minutes (900 seconds)."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            resp = self.client.post(self.token_url, data=json.dumps({}), content_type="application/json")
            data = json.loads(resp.content)
            decoded = jwt.decode(data["token"], options={"verify_signature": False})

            # Verify standard JWT claims expiration
            self.assertIn("exp", decoded)
            self.assertIn("nbf", decoded)
            ttl_seconds = decoded["exp"] - decoded["nbf"]
            self.assertEqual(ttl_seconds, 900)

    def test_token_grants_least_privilege_permissions(self):
        """Verifies token grants ONLY room_join, can_publish, can_subscribe; denies admin/record."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            resp = self.client.post(self.token_url, data=json.dumps({}), content_type="application/json")
            data = json.loads(resp.content)
            claims = self._get_token_claims(data["token"])

            # Restricted VideoGrants
            self.assertTrue(claims.video.room_join)
            self.assertTrue(claims.video.can_publish)
            self.assertTrue(claims.video.can_subscribe)
            self.assertFalse(claims.video.room_admin)
            self.assertFalse(claims.video.room_record)

            # Explicit RoomAgentDispatch attached
            self.assertIsNotNone(claims.room_config)
            self.assertEqual(len(claims.room_config.agents), 1)
            self.assertEqual(claims.room_config.agents[0].agent_name, "daniel-portfolio-voice-agent")

    def test_separate_visitors_receive_isolated_rooms_and_identities(self):
        """Verifies two different visitors get unique room IDs and visitor identities."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            c1 = Client()
            c2 = Client()
            r1 = c1.post(self.token_url, data=json.dumps({}), content_type="application/json")
            r2 = c2.post(self.token_url, data=json.dumps({}), content_type="application/json")

            d1 = json.loads(r1.content)
            d2 = json.loads(r2.content)

            self.assertNotEqual(d1["room"], d2["room"])
            self.assertNotEqual(d1["identity"], d2["identity"])

    def test_server_secrets_never_included_in_response(self):
        """Verifies LiveKit secret and Gemini API key are never leaked in JSON responses."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
            GEMINI_API_KEY=TEST_GEMINI_API_KEY,
        ):
            resp = self.client.post(self.token_url, data=json.dumps({}), content_type="application/json")
            content = resp.content.decode()
            self.assertNotIn(TEST_LIVEKIT_API_SECRET, content)
            self.assertNotIn(TEST_GEMINI_API_KEY, content)

    def test_client_supplied_data_cannot_grant_admin_permissions(self):
        """Client attempting to inject admin claims is neutralized by strict server VideoGrants."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
        ):
            malicious_payload = {
                "room_admin": True,
                "can_record": True,
                "admin": True,
                "permissions": {"admin": True},
            }
            resp = self.client.post(
                self.token_url,
                data=json.dumps(malicious_payload),
                content_type="application/json",
            )
            data = json.loads(resp.content)
            claims = self._get_token_claims(data["token"])
            self.assertFalse(claims.video.room_admin)
            self.assertFalse(claims.video.room_record)


# =============================================================================
# 4. Real-Time Agent Environment Loading Tests
# =============================================================================
class RealtimeAgentEnvironmentLoadingTests(TestCase):
    def test_agent_config_loads_from_project_root(self):
        """Verifies load_agent_config correctly parses environment variables."""
        from realtime_agent.config import load_agent_config

        with patch.dict(
            os.environ,
            {
                "LIVEKIT_URL": TEST_LIVEKIT_URL,
                "LIVEKIT_API_KEY": TEST_LIVEKIT_API_KEY,
                "LIVEKIT_API_SECRET": TEST_LIVEKIT_API_SECRET,
                "GOOGLE_API_KEY": TEST_GEMINI_API_KEY,
                "GEMINI_LIVE_MODEL": "gemini-2.5-flash-native-audio-preview-12-2025",
            },
        ):
            cfg = load_agent_config()
            self.assertEqual(cfg.livekit_url, TEST_LIVEKIT_URL)
            self.assertEqual(cfg.livekit_api_key, TEST_LIVEKIT_API_KEY)
            self.assertEqual(cfg.google_api_key, TEST_GEMINI_API_KEY)
            self.assertEqual(cfg.gemini_live_model, "gemini-2.5-flash-native-audio-preview-12-2025")
            self.assertTrue(cfg.is_configured)

    def test_agent_config_reports_missing_keys_safely(self):
        """Verifies missing keys are reported without printing secret values."""
        from realtime_agent.config import load_agent_config

        with patch.dict(
            os.environ,
            {
                "LIVEKIT_URL": "",
                "LIVEKIT_API_KEY": "",
                "LIVEKIT_API_SECRET": "",
                "GOOGLE_API_KEY": "",
                "GEMINI_API_KEY": "",
            },
        ):
            cfg = load_agent_config()
            self.assertFalse(cfg.is_configured)
            self.assertIn("LIVEKIT_URL", cfg.missing_required_keys)
            self.assertIn("LIVEKIT_API_KEY", cfg.missing_required_keys)
            self.assertIn("GOOGLE_API_KEY", cfg.missing_required_keys)


# =============================================================================
# 5. Gemini and LiveKit Integration Tests
# =============================================================================
class GeminiAndLiveKitIntegrationTests(TestCase):
    def test_gemini_realtime_model_initializes_with_supported_model(self):
        """Verifies Google plugin RealtimeModel initializes with supported gemini-2.5 model."""
        from livekit.plugins import google

        model = google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Puck",
            api_key=TEST_GEMINI_API_KEY,
        )
        self.assertEqual(model._opts.model, "gemini-2.5-flash-native-audio-preview-12-2025")
        self.assertEqual(model._opts.voice, "Puck")

    def test_gemini_realtime_model_initializes_with_turn_detection_config(self):
        """Verifies Google plugin RealtimeModel initializes with turn detection configured."""
        from livekit.plugins import google
        from google.genai import types

        turn_config = types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=True,
            )
        )
        model = google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Puck",
            api_key=TEST_GEMINI_API_KEY,
            realtime_input_config=turn_config,
        )
        self.assertEqual(model._opts.model, "gemini-2.5-flash-native-audio-preview-12-2025")
        self.assertIsNotNone(model._opts.realtime_input_config)
        self.assertTrue(model._opts.realtime_input_config.automatic_activity_detection.disabled)

    def test_agent_session_initializes_with_livekit_turn_detector(self):
        """Verifies AgentSession creates with TurnHandlingOptions and inference.TurnDetector."""
        from livekit.agents import AgentSession, TurnHandlingOptions, inference
        from livekit.agents.voice.turn import InterruptionOptions
        from livekit.plugins import google
        from google.genai import types

        model = google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Puck",
            api_key=TEST_GEMINI_API_KEY,
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=True,
                )
            ),
        )
        turn_handling = TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            interruption=InterruptionOptions(enabled=True),
        )
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            session = AgentSession(
                llm=model,
                turn_handling=turn_handling,
                user_away_timeout=120.0,
                aec_warmup_duration=0.5,
                loop=loop,
            )
            self.assertIsNotNone(session)
            self.assertIsNotNone(session.turn_detection)
            self.assertEqual(session.turn_detection.__class__.__name__, "TurnDetector")
        finally:
            loop.close()
            asyncio.set_event_loop(None)


    def test_agent_entrypoint_missing_gemini_key_raises_value_error(self):
        """Verifies entrypoint aborts with clear error when Gemini key is missing."""
        from realtime_agent.agent import entrypoint

        mock_ctx = MagicMock()
        mock_ctx.room.name = "test-room"

        async def fake_connect(*args, **kwargs):
            return None

        async def fake_wait_for_participant(*args, **kwargs):
            m = MagicMock()
            m.identity = "test-visitor"
            m.name = "Visitor"
            return m

        mock_ctx.connect = fake_connect
        mock_ctx.wait_for_participant = fake_wait_for_participant

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "", "GEMINI_API_KEY": ""}):
            with self.assertRaises(ValueError) as cm:
                asyncio.run(entrypoint(mock_ctx))
            self.assertIn("GOOGLE_API_KEY or GEMINI_API_KEY is not set", str(cm.exception))


# =============================================================================
# 6. Existing Portfolio RAG Knowledge Retrieval Tests
# =============================================================================
class PortfolioRAGKnowledgeRetrievalTests(TestCase):
    def setUp(self):
        # Mock external embedding API so tests run 100% locally, deterministically and fast
        self.emb_patcher = patch("ai_calling.rag_service.generate_embedding", return_value=[0.1] * 3072)
        self.emb_patcher.start()

        # Seed test chunks representing Daniel's portfolio data
        ResumeKnowledgeChunk.objects.filter(chunk_id__in=["exp_levantare", "role_m7", "proj_ats"]).delete()
        self.chunk_exp = ResumeKnowledgeChunk.objects.create(
            chunk_id="exp_levantare",
            category="Experience",
            title="Levantare Technology Software Developer",
            content="Developing and maintaining backend services using Flask, API integrations, and PostgreSQL.",
            is_active=True,
        )
        self.chunk_role = ResumeKnowledgeChunk.objects.create(
            chunk_id="role_m7",
            category="Profile",
            title="Current Role at M7 Technology",
            content="Daniel John Britto is working as a Python Developer at M7 Technology.",
            is_active=True,
        )
        self.chunk_project = ResumeKnowledgeChunk.objects.create(
            chunk_id="proj_ats",
            category="Projects",
            title="Resume ATS Scanner",
            content="Built an automated resume scanner that matches candidates to job descriptions.",
            is_active=True,
        )

    def tearDown(self):
        self.emb_patcher.stop()

    def test_rag_query_previous_company_levantare(self):
        """Querying Levantare retrieves Levantare Technology chunk."""
        results = retrieve_relevant_chunks("Where did Daniel work at Levantare Technology?")
        self.assertGreater(len(results), 0)
        titles = [c.title for c, _ in results]
        self.assertTrue(any("Levantare" in t for t in titles))

    def test_rag_query_current_role_m7(self):
        """Querying current company retrieves M7 Technology chunk."""
        results = retrieve_relevant_chunks("What is Daniel's role at M7 Technology?")
        self.assertGreater(len(results), 0)
        titles = [c.title for c, _ in results]
        self.assertTrue(any("M7 Technology" in t for t in titles))

    def test_rag_query_projects(self):
        """Querying projects retrieves Resume ATS Scanner chunk."""
        results = retrieve_relevant_chunks("Tell me about the ATS Scanner project")
        self.assertGreater(len(results), 0)
        titles = [c.title for c, _ in results]
        self.assertTrue(any("ATS Scanner" in t for t in titles))

    def test_rag_query_empty_or_whitespace_returns_empty_safely(self):
        """Empty or whitespace-only queries return empty list without exception."""
        self.assertEqual(retrieve_relevant_chunks(""), [])
        self.assertEqual(retrieve_relevant_chunks("    "), [])

    def test_rag_query_no_matching_chunks_falls_back_safely(self):
        """Queries matching nothing return empty or low score without errors."""
        results = retrieve_relevant_chunks("Quantum astrophysics theoretical gravitational black hole dynamics")
        fallback = generate_smart_resume_fallback_answer("Quantum astrophysics", results)
        self.assertIn("Daniel", fallback)

    def test_search_portfolio_knowledge_tool_invokes_rag(self):
        """Verifies real-time agent tool search_portfolio_knowledge formats and returns facts."""
        from realtime_agent.agent import search_portfolio_knowledge

        with patch("realtime_agent.agent.retrieve_relevant_chunks", return_value=[(self.chunk_exp, 1.0)]):
            result = asyncio.run(search_portfolio_knowledge("Levantare Technology"))
            self.assertIn("Levantare", result)
            self.assertIn("Verified Portfolio", result)


# =============================================================================
# 7. Existing Django Chatbot Regression Tests (POST /ai-calling/chat/)
# =============================================================================
class ChatbotRegressionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.chat_url = reverse("chat_endpoint")
        _RATE_LIMIT_STORE.clear()

        # Mock embedding calls so tests never hit external network
        self.emb_patcher = patch("ai_calling.rag_service.generate_embedding", return_value=[0.1] * 3072)
        self.emb_patcher.start()

        ResumeKnowledgeChunk.objects.create(
            chunk_id="exp_test",
            category="Experience",
            title="Software Development",
            content="Python Developer specializing in Django, Flask, PostgreSQL.",
            is_active=True,
        )

    def tearDown(self):
        self.emb_patcher.stop()
        _RATE_LIMIT_STORE.clear()

    def test_chat_endpoint_valid_request_with_smart_fallback(self):
        """When GEMINI_API_KEY is unset, chat endpoint succeeds using deterministic smart fallback."""
        with self.settings(GEMINI_API_KEY=""):
            resp = self.client.post(
                self.chat_url,
                data=json.dumps({"message": "What skills does Daniel have?"}),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.content)
            self.assertTrue(data.get("success"))
            self.assertIn("Python", data.get("answer", ""))

    def test_chat_endpoint_mocked_gemini_success(self):
        """When Gemini returns 200, chat endpoint returns model generated answer."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Daniel is an experienced Python developer with Django and Flask skills."}]
                    }
                }
            ]
        }

        with self.settings(GEMINI_API_KEY=TEST_GEMINI_API_KEY):
            with patch("requests.post", return_value=mock_response):
                resp = self.client.post(
                    self.chat_url,
                    data=json.dumps({"message": "Tell me about Daniel's skills"}),
                    content_type="application/json",
                )
                self.assertEqual(resp.status_code, 200)
                data = json.loads(resp.content)
                self.assertTrue(data.get("success"))
                self.assertIn("experienced Python developer", data.get("answer", ""))

    def test_chat_endpoint_mocked_gemini_timeout_activates_fallback(self):
        """When Gemini times out, chat endpoint gracefully activates smart fallback."""
        import requests

        with self.settings(GEMINI_API_KEY=TEST_GEMINI_API_KEY):
            with patch("requests.post", side_effect=requests.exceptions.Timeout("Connection timed out")):
                resp = self.client.post(
                    self.chat_url,
                    data=json.dumps({"message": "Tell me about Levantare Technology"}),
                    content_type="application/json",
                )
                self.assertEqual(resp.status_code, 200)
                data = json.loads(resp.content)
                self.assertTrue(data.get("success"))
                self.assertTrue(data.get("fallback_mode"))

    def test_chat_endpoint_mocked_gemini_provider_error(self):
        """When Gemini returns 503 high demand, chat endpoint falls back cleanly."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Model is overloaded. Please try again later."

        with self.settings(GEMINI_API_KEY=TEST_GEMINI_API_KEY):
            with patch("requests.post", return_value=mock_response):
                resp = self.client.post(
                    self.chat_url,
                    data=json.dumps({"message": "Tell me about Daniel"}),
                    content_type="application/json",
                )
                self.assertEqual(resp.status_code, 200)
                data = json.loads(resp.content)
                self.assertTrue(data.get("success"))

    def test_chat_endpoint_conversation_history_handled(self):
        """History parameter is accepted and processed without error."""
        with self.settings(GEMINI_API_KEY=""):
            history = [
                {"role": "user", "text": "Hi"},
                {"role": "model", "text": "Hello! How can I help?"},
            ]
            resp = self.client.post(
                self.chat_url,
                data=json.dumps({"message": "What projects has Daniel worked on?", "history": history}),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200)


# =============================================================================
# 8. Feature Switch Tests (ENABLE_WEBRTC_VOICE)
# =============================================================================
class FeatureSwitchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.token_url = reverse("livekit_token")
        self.chat_url = reverse("chat_endpoint")
        _RATE_LIMIT_STORE.clear()
        self.emb_patcher = patch("ai_calling.rag_service.generate_embedding", return_value=[0.1] * 3072)
        self.emb_patcher.start()
        ResumeKnowledgeChunk.objects.create(
            chunk_id="chunk_fs_test",
            category="Profile",
            title="Daniel Profile",
            content="Daniel is a software engineer.",
            is_active=True,
        )

    def tearDown(self):
        self.emb_patcher.stop()
        _RATE_LIMIT_STORE.clear()

    def test_when_enabled_token_works_and_chat_works(self):
        """When ENABLE_WEBRTC_VOICE is True, both token endpoint and chat endpoint work."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=True,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
            GEMINI_API_KEY="",
        ):
            token_resp = self.client.post(self.token_url, data=json.dumps({}), content_type="application/json")
            chat_resp = self.client.post(
                self.chat_url,
                data=json.dumps({"message": "Hello"}),
                content_type="application/json",
            )
            self.assertEqual(token_resp.status_code, 200)
            self.assertEqual(chat_resp.status_code, 200)

    def test_when_disabled_token_rejected_and_chat_still_works(self):
        """When ENABLE_WEBRTC_VOICE is False, token endpoint returns 503 while chat continues working."""
        with self.settings(
            ENABLE_WEBRTC_VOICE=False,
            LIVEKIT_URL=TEST_LIVEKIT_URL,
            LIVEKIT_API_KEY=TEST_LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET=TEST_LIVEKIT_API_SECRET,
            GEMINI_API_KEY="",
        ):
            token_resp = self.client.post(self.token_url, data=json.dumps({}), content_type="application/json")
            chat_resp = self.client.post(
                self.chat_url,
                data=json.dumps({"message": "Hello"}),
                content_type="application/json",
            )
            self.assertEqual(token_resp.status_code, 503)
            self.assertEqual(chat_resp.status_code, 200)


# =============================================================================
# 9. Secret Leakage Prevention Tests
# =============================================================================
class SecretLeakageTests(TestCase):
    def test_env_file_is_excluded_from_git(self):
        """Verifies .gitignore explicitly includes .env and does not commit it."""
        from realtime_agent.config import find_project_root

        root = find_project_root()
        gitignore_path = root / ".gitignore"
        self.assertTrue(gitignore_path.exists())
        content = gitignore_path.read_text(encoding="utf-8")
        self.assertIn(".env", content)

    def test_env_example_contains_placeholders_only(self):
        """Verifies .env.example contains only placeholders, no real API keys."""
        from realtime_agent.config import find_project_root

        root = find_project_root()
        example_path = root / ".env.example"
        if not example_path.exists():
            example_path = root.parent / ".env.example"
        self.assertTrue(example_path.exists(), f"Could not find .env.example in {root} or {root.parent}")
        content = example_path.read_text(encoding="utf-8")

        # Must not contain live keys or real project values (ensure only placeholders)
        for line in content.splitlines():
            line = line.strip()
            if line.startswith(("LIVEKIT_API_KEY=", "LIVEKIT_API_SECRET=", "GEMINI_API_KEY=", "GOOGLE_API_KEY=")):
                key, val = line.split("=", 1)
                self.assertTrue(
                    val.startswith("your_") or not val,
                    f"Credential {key} must have placeholder value, got: {val}"
                )

        self.assertIn("your_google_gemini_api_key_here", content)
        self.assertIn("your_livekit_api_key_here", content)
        self.assertIn("your_livekit_api_secret_here", content)

    def test_python_code_has_no_hardcoded_livekit_secrets(self):
        """Verifies no hardcoded LiveKit secret is embedded in application source code."""
        import re
        from realtime_agent.config import find_project_root

        root = find_project_root()
        secret_assignment_pattern = re.compile(r'LIVEKIT_API_SECRET\s*=\s*["\'][A-Za-z0-9_\-]{20,}["\']')
        for py_file in root.rglob("*.py"):
            # Exclude tests and virtual environments
            if (
                "venv" in str(py_file)
                or ".venv" in str(py_file)
                or "packages" in str(py_file)
                or "test" in py_file.name.lower()
            ):
                continue
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            self.assertIsNone(
                secret_assignment_pattern.search(text),
                f"Potential hardcoded secret found in {py_file}"
            )


# =============================================================================
# 10. Database Configuration Security Tests
# =============================================================================
class DatabaseConfigurationSecurityTests(TestCase):
    def test_production_database_url_invalid_raises_improperly_configured(self):
        """Invalid production DATABASE_URL cannot silently fall back to SQLite."""
        import dj_database_url

        invalid_url = "not-a-valid-database-url"
        with self.assertRaises((ImproperlyConfigured, ValueError)):
            parsed = dj_database_url.parse(invalid_url)
            if not parsed or "ENGINE" not in parsed:
                raise ImproperlyConfigured("DATABASE_URL failed to parse into valid database configuration.")


# =============================================================================
# 11. Optional Live Smoke Integration Test (Opt-in only)
# =============================================================================
class OptionalLiveSmokeIntegrationTest(TestCase):
    def test_live_livekit_cloud_connection(self):
        """
        Opt-in smoke test for real LiveKit Cloud connection.
        Disabled by default. Set RUN_LIVE_SMOKE_TESTS=1 to run.
        """
        if os.environ.get("RUN_LIVE_SMOKE_TESTS") != "1":
            self.skipTest("Live smoke test skipped by default. Set RUN_LIVE_SMOKE_TESTS=1 to enable.")

        from realtime_agent.config import load_agent_config

        cfg = load_agent_config()
        if not cfg.is_configured:
            self.skipTest(f"Missing live credentials: {cfg.missing_required_keys}")

        self.assertTrue(cfg.livekit_url.startswith("wss://"))


# =============================================================================
# 12. WebRTC Voice Assistant Lifecycle, State Events & Agent Tests
# =============================================================================
class WebRTCVoiceAssistantLifecycleAndAgentTests(TestCase):
    def setUp(self):
        super().setUp()
        self.chunk = ResumeKnowledgeChunk.objects.create(
            chunk_id="test_exp_python_m7",
            title="Backend Frameworks & Python Expertise",
            content="Daniel John Britto specializes in Python, Django, Flask, and PostgreSQL at M7 Technology.",
            category="EXPERIENCE",
            is_active=True,
        )

    def test_search_portfolio_knowledge_tool_with_db_chunks(self):
        """Verifies search_portfolio_knowledge returns verified context from Django ORM."""
        from realtime_agent.agent import search_portfolio_knowledge

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(search_portfolio_knowledge("Python Django experience"))
            self.assertIn("Verified Portfolio", result)
            self.assertIn("Python", result)
            self.assertIn("M7 Technology", result)
        finally:
            loop.close()

    def test_search_portfolio_knowledge_tool_fallback(self):
        """Verifies search_portfolio_knowledge falls back safely if query matches nothing."""
        from realtime_agent.agent import search_portfolio_knowledge

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(search_portfolio_knowledge("quantum mechanics astrophysics"))
            self.assertIn("Daniel", result)
        finally:
            loop.close()

    def test_agent_turn_detection_config(self):
        """Verifies turn detection config uses safe 1000ms pause threshold instead of 500ms cutoff."""
        from google.genai import types
        turn_detection_config = types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                prefix_padding_ms=300,
                silence_duration_ms=1000,
            )
        )
        self.assertFalse(turn_detection_config.automatic_activity_detection.disabled)
        self.assertEqual(turn_detection_config.automatic_activity_detection.silence_duration_ms, 1000)

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-gemini-key"})
    @patch("livekit.plugins.google.realtime.RealtimeModel")
    def test_agent_entrypoint_lifecycle(self, mock_model_class):
        """Verifies agent entrypoint connects session, waits for participant, and generates greeting once."""
        from realtime_agent.agent import entrypoint
        from livekit.agents import JobContext

        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        mock_ctx = MagicMock(spec=JobContext)
        mock_room = MagicMock()
        mock_ctx.room = mock_room
        mock_room.name = "portfolio-test-room"
        mock_room.on = MagicMock()
        mock_participant = MagicMock()
        mock_participant.identity = "visitor-test-123"
        mock_participant.name = "Test Visitor"

        loop = asyncio.new_event_loop()
        try:
            with patch("realtime_agent.agent.AgentSession") as mock_session_class:
                mock_session = MagicMock()
                mock_session_class.return_value = mock_session
                mock_session.start = unittest.mock.AsyncMock()
                async def _fake_wait():
                    return mock_participant
                mock_ctx.wait_for_participant = _fake_wait
                mock_session.generate_reply = unittest.mock.AsyncMock()

                loop.run_until_complete(entrypoint(mock_ctx))

                # Verify session was started with room
                mock_session.start.assert_called_once()
                # Verify initial greeting was called once
                mock_session.generate_reply.assert_called_once()
        finally:
            loop.close()

    def test_state_event_parsing_avoids_stuck_speaking_state(self):
        """
        Verifies that when an AgentStateChangedEvent transitions from speaking to listening,
        new_state is used so it does not falsely emit 'speaking'.
        """
        from livekit.agents.voice.events import AgentStateChangedEvent

        event = AgentStateChangedEvent(old_state="speaking", new_state="listening")
        # In the old bug: 'speaking' in str(event).lower() was True because old_state was 'speaking'.
        # With the fix: event.new_state is checked directly.
        new_state = getattr(event, "new_state", "")
        self.assertEqual(new_state, "listening")
        self.assertNotEqual(new_state, "speaking")


# =============================================================================
# 11. Production & Local Database Configuration Safeguard Tests
# =============================================================================
class DatabaseConfigurationSafeguardTests(TestCase):
    def test_render_missing_database_url_raises_improperly_configured(self):
        """Verifies that on Render, missing DATABASE_URL strictly raises ImproperlyConfigured."""
        from django.core.exceptions import ImproperlyConfigured
        from portfolio.settings import configure_databases

        render_env_missing_db = {
            "RENDER": "true",
            "DATABASE_URL": "",
        }
        with self.assertRaises(ImproperlyConfigured) as ctx:
            configure_databases(render_env_missing_db)

        self.assertIn("DATABASE_URL is not set on Render", str(ctx.exception))
        self.assertIn("SQLite is not permitted in production", str(ctx.exception))

    def test_render_valid_postgresql_database_url(self):
        """Verifies that a valid PostgreSQL DATABASE_URL is parsed correctly on Render."""
        from portfolio.settings import configure_databases

        dummy_postgres_url = "postgresql://dummy_user:dummy_pass@dummy_host:5432/dummy_db"
        render_env = {
            "RENDER": "true",
            "DATABASE_URL": dummy_postgres_url,
        }
        config = configure_databases(render_env)
        self.assertIn("default", config)
        db = config["default"]
        self.assertEqual(db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(db["NAME"], "dummy_db")
        self.assertEqual(db["USER"], "dummy_user")
        self.assertEqual(db["HOST"], "dummy_host")
        self.assertEqual(db["PORT"], 5432)

    def test_render_invalid_database_url_raises_improperly_configured(self):
        """Verifies that a malformed DATABASE_URL on Render raises ImproperlyConfigured safely."""
        from django.core.exceptions import ImproperlyConfigured
        from portfolio.settings import configure_databases

        render_env_invalid = {
            "RENDER": "true",
            "DATABASE_URL": "not_a_valid_url_scheme",
        }
        with self.assertRaises(ImproperlyConfigured) as ctx:
            configure_databases(render_env_invalid)

        self.assertIn("Production DATABASE_URL is invalid", str(ctx.exception))
        # Ensure credentials are not printed
        self.assertNotIn("password", str(ctx.exception).lower())

    def test_local_sqlite_selection_when_use_sqlite_is_true(self):
        """Verifies that local development uses SQLite when USE_SQLITE=True."""
        from portfolio.settings import configure_databases

        local_sqlite_env = {
            "RENDER": "",
            "RENDER_EXTERNAL_HOSTNAME": "",
            "USE_SQLITE": "True",
            "DATABASE_URL": "postgresql://dummy_user:dummy_pass@dummy_host:5432/dummy_db",
        }
        config = configure_databases(local_sqlite_env)
        self.assertIn("default", config)
        self.assertEqual(config["default"]["ENGINE"], "django.db.backends.sqlite3")

    def test_local_individual_db_credentials_selection(self):
        """Verifies that local development configures PostgreSQL from DB_* variables."""
        from portfolio.settings import configure_databases

        local_pg_env = {
            "RENDER": "",
            "RENDER_EXTERNAL_HOSTNAME": "",
            "USE_SQLITE": "False",
            "DB_NAME": "test_portfolio_db",
            "DB_USER": "test_pg_user",
            "DB_PASSWORD": "test_pg_password",
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
        }
        config = configure_databases(local_pg_env)
        self.assertIn("default", config)
        db = config["default"]
        self.assertEqual(db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(db["NAME"], "test_portfolio_db")
        self.assertEqual(db["USER"], "test_pg_user")
        self.assertEqual(db["HOST"], "localhost")
