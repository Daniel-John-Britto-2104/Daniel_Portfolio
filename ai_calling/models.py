from django.db import models


class ResumeKnowledgeChunk(models.Model):
    """
    Stores verified chunks of Daniel John Britto's resume and portfolio knowledge,
    along with their semantic vector embeddings for RAG retrieval.
    """
    chunk_id = models.CharField(max_length=100, unique=True, help_text="Unique identifier e.g. profile_summary, edu_degree")
    category = models.CharField(max_length=100, db_index=True, help_text="e.g. Profile, Education, Experience, Skills, Projects, Certifications, Contact")
    title = models.CharField(max_length=255, help_text="Brief headline for the chunk")
    content = models.TextField(help_text="The verified factual information grounded in Daniel's resume")
    embedding = models.JSONField(default=list, blank=True, help_text="Vector embedding list of floats")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "title"]
        verbose_name = "Resume Knowledge Chunk"
        verbose_name_plural = "Resume Knowledge Chunks"

    def __str__(self):
        return f"[{self.category}] {self.title}"


class ChatInteraction(models.Model):
    """
    Lightweight, privacy-focused log of assistant questions and responses.
    Does not collect any personal visitor information.
    """
    session_id = models.CharField(max_length=100, blank=True, db_index=True)
    user_message = models.TextField()
    assistant_response = models.TextField()
    retrieved_chunk_ids = models.JSONField(default=list, blank=True)
    response_time_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chat Interaction"
        verbose_name_plural = "Chat Interactions"

    def __str__(self):
        return f"Interaction at {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
