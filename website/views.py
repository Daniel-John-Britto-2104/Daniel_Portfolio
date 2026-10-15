import logging

from django.contrib import messages
from django.db import DatabaseError
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .forms import ContactForm
from .models import (
    Profile,
    SocialLink,
    Skill,
    Experience,
    Project,
    Education,
    Certificate,
)

from .portfolio_defaults import get_fallback_context_data, seed_database_tables

logger = logging.getLogger(__name__)


def home(request):
    # If the database is completely empty (e.g. freshly deployed to production),
    # auto-seed the tables immediately.
    try:
        if not Skill.objects.exists():
            seed_database_tables()
    except Exception as seed_err:
        logger.warning("Could not auto-seed database tables in home view: %s", seed_err)

    # Attempt to retrieve records from the database
    try:
        profile = Profile.objects.filter(is_active=True).first()
        social_links = list(SocialLink.objects.all())
        skills = list(Skill.objects.all())
        experiences = list(Experience.objects.all())
        projects = list(Project.objects.all())
        education_list = list(Education.objects.all())
        certificates = list(Certificate.objects.all())
    except Exception as db_err:
        logger.warning("Error fetching portfolio records from database: %s", db_err)
        profile = None
        social_links = []
        skills = []
        experiences = []
        projects = []
        education_list = []
        certificates = []

    # Fallback to canonical in-memory portfolio data if any section is empty,
    # guaranteeing that production will NEVER display blank skill/project boxes.
    fallback = get_fallback_context_data()

    if not profile:
        profile = fallback["profile"]
    if not social_links:
        social_links = fallback["social_links"]
    if not skills:
        skills = fallback["skills"]
    if not experiences:
        experiences = fallback["experiences"]
    if not projects:
        projects = fallback["projects"]
    if not education_list:
        education_list = fallback["education_list"]
    if not certificates:
        certificates = fallback["certificates"]

    # Group skills by category
    skills_by_category = {
        "Languages": [s for s in skills if s.category == "Languages"],
        "Frameworks": [s for s in skills if s.category == "Frameworks"],
        "Databases": [s for s in skills if s.category == "Databases"],
        "Tools": [s for s in skills if s.category == "Tools"],
    }

    context = {
        "profile": profile,
        "social_links": social_links,
        "skills": skills,
        "skills_by_category": skills_by_category,
        "experiences": experiences,
        "projects": projects,
        "education_list": education_list,
        "certificates": certificates,
    }
    return render(request, "home.html", context)


@require_POST
def contact_submit(request):
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    form = ContactForm(request.POST)

    if not form.is_valid():
        error_msg = " ".join(
            f"{field.replace('_', ' ').capitalize()}: {', '.join(errors)}"
            for field, errors in form.errors.items()
        )
        if is_ajax:
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect("home")

    try:
        contact = form.save()
    except DatabaseError:
        logger.exception("Unable to save a contact form submission.")
        error_msg = "Your message could not be sent right now. Please try again later."
        if is_ajax:
            return JsonResponse({"success": False, "message": error_msg}, status=503)
        messages.error(request, error_msg)
        return redirect("home")

    success_msg = (
        f"Thank you, {contact.name}! Your message has been sent successfully. "
        "I will get back to you soon."
    )
    
    if is_ajax:
        return JsonResponse({"success": True, "message": success_msg})

    messages.success(request, success_msg)
    return redirect("home")


def robots_txt(request):
    content = """User-agent: *
Allow: /
Disallow: /admin/
Sitemap: http://127.0.0.1:8000/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")


def sitemap_xml(request):
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>http://127.0.0.1:8000/</loc>
      <changefreq>weekly</changefreq>
      <priority>1.0</priority>
   </url>
</urlset>
"""
    return HttpResponse(content, content_type="application/xml")