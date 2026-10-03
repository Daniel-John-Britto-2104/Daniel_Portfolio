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

logger = logging.getLogger(__name__)


def home(request):
    profile = Profile.objects.filter(is_active=True).first()
    if not profile:
        # Fallback default profile if table is empty
        profile = Profile(
            full_name="Daniel John Britto",
            title="Python Developer | Django & Full Stack Developer",
            headline="Python Developer at Thaagam Foundation | Specializing in Django Backend & Angular Full Stack Development",
            bio="Passionate Python Developer currently working at Thaagam Foundation with 6 months of hands-on software development experience. Experienced in building robust Django backend applications, RESTful APIs, and full stack web solutions using Angular and Python.",
            years_of_experience=1,
            projects_completed=8,
            location="Chennai, India",
            email="danieljohnbrittoaj@gmail.com",
            phone="+91 98765 43210",
        )

    social_links = SocialLink.objects.all()
    skills = Skill.objects.all()
    
    # Group skills by category
    skills_by_category = {
        "Languages": [s for s in skills if s.category == "Languages"],
        "Frameworks": [s for s in skills if s.category == "Frameworks"],
        "Databases": [s for s in skills if s.category == "Databases"],
        "Tools": [s for s in skills if s.category == "Tools"],
    }

    experiences = Experience.objects.all()
    projects = Project.objects.all()
    education_list = Education.objects.all()
    certificates = Certificate.objects.all()

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