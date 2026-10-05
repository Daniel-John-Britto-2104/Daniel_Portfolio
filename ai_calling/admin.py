from django.contrib import admin
from .models import ResumeKnowledgeChunk, ChatInteraction


@admin.register(ResumeKnowledgeChunk)
class ResumeKnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("chunk_id", "title", "category", "is_active", "has_embedding", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("chunk_id", "title", "content")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at")

    def has_embedding(self, obj):
        return bool(obj.embedding and len(obj.embedding) > 0)
    has_embedding.boolean = True
    has_embedding.short_description = "Embedded"


@admin.register(ChatInteraction)
class ChatInteractionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "short_user_message", "short_response", "response_time_ms")
    list_filter = ("created_at",)
    search_fields = ("user_message", "assistant_response")
    readonly_fields = ("created_at", "session_id", "user_message", "assistant_response", "retrieved_chunk_ids", "response_time_ms")

    def short_user_message(self, obj):
        return (obj.user_message[:60] + "...") if len(obj.user_message) > 60 else obj.user_message
    short_user_message.short_description = "Question"

    def short_response(self, obj):
        return (obj.assistant_response[:80] + "...") if len(obj.assistant_response) > 80 else obj.assistant_response
    short_response.short_description = "Answer"
