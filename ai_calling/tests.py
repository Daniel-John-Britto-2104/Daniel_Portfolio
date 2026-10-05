import json
from django.test import TestCase, Client
from django.urls import reverse
from .models import ResumeKnowledgeChunk, ChatInteraction
from .rag_service import cosine_similarity, compute_keyword_score, retrieve_relevant_chunks


class ChatbotRAGTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.chat_url = reverse("chat_endpoint")

        # Create sample knowledge chunks
        self.chunk1 = ResumeKnowledgeChunk.objects.create(
            chunk_id="test_levantare",
            category="Experience",
            title="Levantare Technology Backend Developer",
            content="Developing and maintaining backend services using Flask, API integrations, and PostgreSQL.",
            embedding=[0.1] * 3072,
            is_active=True,
        )
        self.chunk2 = ResumeKnowledgeChunk.objects.create(
            chunk_id="test_education",
            category="Education",
            title="Madha Institute of Engineering and Technology",
            content="Bachelor of Engineering in Computer Science and Engineering from Madha Institute (2021-2025).",
            embedding=[0.5] * 3072,
            is_active=True,
        )

    def test_chunk_creation(self):
        """Verifies knowledge chunk persistence."""
        self.assertEqual(ResumeKnowledgeChunk.objects.count(), 2)
        self.assertEqual(str(self.chunk1), "[Experience] Levantare Technology Backend Developer")

    def test_cosine_similarity_math(self):
        """Tests vector cosine similarity math calculations."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(vec1, vec2), 1.0)

        vec3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(vec1, vec3), 0.0)

        # Empty or mismatched vectors
        self.assertEqual(cosine_similarity([], []), 0.0)
        self.assertEqual(cosine_similarity([1.0], [1.0, 2.0]), 0.0)

    def test_keyword_overlap_score(self):
        """Tests lexical scoring for search keywords."""
        score = compute_keyword_score(
            query="Flask Levantare",
            text="Developing Flask services at Levantare Technology",
            title="Levantare Backend"
        )
        self.assertGreater(score, 0.0)

    def test_chat_endpoint_get_not_allowed(self):
        """GET request to /ai-calling/chat/ should return 405 Method Not Allowed."""
        response = self.client.get(self.chat_url)
        self.assertEqual(response.status_code, 405)

    def test_chat_endpoint_empty_message(self):
        """Empty message should return 400 Bad Request."""
        response = self.client.post(
            self.chat_url,
            data=json.dumps({"message": "   "}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])

    def test_chat_endpoint_over_max_length(self):
        """Message exceeding character limit should return 400 Bad Request."""
        long_message = "A" * 700
        response = self.client.post(
            self.chat_url,
            data=json.dumps({"message": long_message}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_chat_endpoint_invalid_json(self):
        """Invalid JSON body should return 400 Bad Request."""
        response = self.client.post(
            self.chat_url,
            data="not a json string",
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_chat_endpoint_successful_interaction(self):
        """Tests successful chat endpoint flow and logging."""
        response = self.client.post(
            self.chat_url,
            data=json.dumps({"message": "Tell me about Levantare Technology"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("answer", data)
        # Verify ChatInteraction logged
        self.assertEqual(ChatInteraction.objects.count(), 1)
        log = ChatInteraction.objects.first()
        self.assertIn("Levantare", log.user_message)
