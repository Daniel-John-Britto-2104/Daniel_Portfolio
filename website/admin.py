from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Profile,
    SocialLink,
    Skill,
    Experience,
    Project,
    Education,
    Certificate,
    Contact,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "title", "email", "years_of_experience", "projects_completed", "is_active")
    list_editable = ("is_active",)
    fieldsets = (
        ("Personal Information", {
            "fields": ("full_name", "title", "headline", "bio", "profile_image_url")
        }),
        ("Metrics & Details", {
            "fields": ("years_of_experience", "projects_completed", "location", "email", "phone", "resume_url", "is_active")
        }),
    )


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("platform", "url", "icon_name", "order")
    list_editable = ("order",)
    search_fields = ("platform", "url")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "proficiency", "is_featured", "order")
    list_filter = ("category", "is_featured")
    list_editable = ("proficiency", "is_featured", "order")
    search_fields = ("name", "category")


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("role", "company", "start_date", "end_date", "is_current", "order")
    list_filter = ("is_current", "company")
    list_editable = ("order",)
    search_fields = ("role", "company", "tech_stack", "responsibilities_raw")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "tech_stack", "is_featured", "order", "image_preview")
    list_filter = ("is_featured",)
    list_editable = ("is_featured", "order")
    search_fields = ("title", "tech_stack", "summary", "description")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        ("Project Details", {
            "fields": ("title", "slug", "summary", "description", "image_url")
        }),
        ("Technologies & Features", {
            "fields": ("tech_stack", "features_raw")
        }),
        ("Links & Settings", {
            "fields": ("github_url", "live_url", "is_featured", "order")
        }),
    )

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="height: 40px; border-radius: 4px;" />', obj.image_url)
        return "-"
    image_preview.short_description = "Preview"


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ("degree", "institution", "score", "start_year", "end_year", "order")
    list_editable = ("order",)
    search_fields = ("degree", "institution")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("title", "issuer", "issue_date", "order")
    list_editable = ("order",)
    search_fields = ("title", "issuer")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at", "is_read")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email", "subject", "message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    actions = ["mark_as_read", "mark_as_unread"]

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected messages as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Mark selected messages as unread"
