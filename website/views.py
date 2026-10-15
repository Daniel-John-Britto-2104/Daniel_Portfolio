import logging
import re
import requests

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.db import DatabaseError
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.utils.html import escape
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


def send_contact_notification_email(contact) -> bool:
    """
    Sends an email notification via Resend HTTPS API (port 443)
    when someone contacts Daniel or submits the Hire Me form.
    Includes sender name, email, subject, message, and a direct Reply-To header.
    Does NOT depend on or fall back to Gmail SMTP on Render Free.
    Returns True if email was successfully accepted by Resend, False otherwise.
    Never raises an unhandled exception or logs sensitive credentials.
    """
    resend_api_key = getattr(settings, "RESEND_API_KEY", "").strip()
    if not resend_api_key:
        logger.warning("RESEND_API_KEY is not configured. Email notification cannot be sent.")
        return False

    recipient = getattr(settings, "CONTACT_RECIPIENT_EMAIL", "danieljohnbrittoaj@gmail.com").strip()
    if not recipient:
        logger.warning("CONTACT_RECIPIENT_EMAIL is not configured. Email notification cannot be sent.")
        return False

    from_email = (
        getattr(settings, "RESEND_FROM_EMAIL", None)
        or getattr(settings, "DEFAULT_FROM_EMAIL", None)
        or "Portfolio <onboarding@resend.dev>"
    ).strip()
    # Resend strictly rejects public webmail domains (e.g. @gmail.com) as the sender address.
    # If DEFAULT_FROM_EMAIL is set to a Gmail address, safely fallback to onboarding@resend.dev.
    if any(domain in from_email.lower() for domain in ("@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com")):
        from_email = "Portfolio <onboarding@resend.dev>"

    subject_prefix = getattr(settings, "EMAIL_SUBJECT_PREFIX", "[Portfolio Contact] ").strip()
    clean_subject = (contact.subject or "").strip()
    email_subject = f"{subject_prefix} {clean_subject}" if clean_subject else f"{subject_prefix} New message from {contact.name}"

    timestamp_str = (
        contact.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        if hasattr(contact, 'created_at') and contact.created_at
        else "Just now"
    )

    plain_body = f"""Hello Daniel,

You have received a new contact / hire inquiry from your portfolio website:

----------------------------------------------------------------------
Sender Name:    {contact.name}
Sender Email:   {contact.email}
Subject:        {contact.subject or 'Not specified'}
Submitted At:   {timestamp_str}
----------------------------------------------------------------------

Message:
{contact.message}

----------------------------------------------------------------------
Reply-To: You can directly reply to this email to reach {contact.name} at {contact.email}.
"""

    safe_name = escape(contact.name)
    safe_email = escape(contact.email)
    safe_subject = escape(contact.subject or 'Not specified')
    safe_message = escape(contact.message)

    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b1120; color: #e2e8f0; margin: 0; padding: 24px; }}
  .card {{ max-width: 600px; margin: 0 auto; background: #131c31; border: 1px solid #1e293b; border-radius: 12px; padding: 28px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
  .header {{ border-bottom: 2px solid #00c6ff; padding-bottom: 16px; margin-bottom: 24px; }}
  .header h2 {{ margin: 0; color: #38bdf8; font-size: 20px; }}
  .field {{ margin-bottom: 14px; }}
  .label {{ color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }}
  .value {{ color: #f8fafc; font-size: 15px; font-weight: 500; }}
  .msg-box {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 18px; margin: 20px 0; color: #f1f5f9; white-space: pre-wrap; font-size: 14px; line-height: 1.6; }}
  .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #1e293b; font-size: 12px; color: #64748b; }}
  .reply-btn {{ display: inline-block; background: #0284c7; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; margin-top: 12px; }}
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h2>New Portfolio Inquiry</h2>
    </div>
    <div class="field">
      <div class="label">Sender Name</div>
      <div class="value">{safe_name}</div>
    </div>
    <div class="field">
      <div class="label">Sender Email</div>
      <div class="value"><a href="mailto:{safe_email}" style="color: #38bdf8;">{safe_email}</a></div>
    </div>
    <div class="field">
      <div class="label">Subject</div>
      <div class="value">{safe_subject}</div>
    </div>
    <div class="field">
      <div class="label">Message</div>
      <div class="msg-box">{safe_message}</div>
    </div>
    <a href="mailto:{safe_email}?subject=Re:%20{safe_subject}" class="reply-btn">Reply to {safe_name}</a>
    <div class="footer">
      Sent from your Developer Portfolio contact form at {timestamp_str}.
    </div>
  </div>
</body>
</html>"""

    payload = {
        "from": from_email,
        "to": [recipient],
        "reply_to": contact.email,
        "subject": email_subject,
        "text": plain_body,
        "html": html_body,
    }
    headers = {
        "Authorization": f"Bearer {resend_api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            json=payload,
            headers=headers,
            timeout=10,
        )
    except requests.exceptions.Timeout:
        logger.warning(
            "Resend API request timed out for contact ID %s.",
            getattr(contact, "id", None),
        )
        return False
    except requests.exceptions.RequestException as req_err:
        logger.warning(
            "Resend API network/request error for contact ID %s: %s",
            getattr(contact, "id", None),
            type(req_err).__name__,
        )
        return False
    except Exception as err:
        logger.warning(
            "Unexpected error sending email via Resend API for contact ID %s: %s",
            getattr(contact, "id", None),
            type(err).__name__,
        )
        return False

    if resp.status_code in (200, 201):
        try:
            resend_id = resp.json().get("id", "unknown")
        except Exception:
            resend_id = "unknown"
        logger.info(
            "Contact notification email successfully delivered via Resend API for contact ID %s (ID: %s)",
            getattr(contact, "id", None),
            resend_id,
        )
        return True

    # If Resend rejected with HTTP 403 due to testing restrictions (unverified domain),
    # Resend specifies the allowed account owner address, e.g.:
    # "You can only send testing emails to your own email address (danielamalraj21@gmail.com)..."
    # Auto-retry to the verified account owner so Daniel receives the notification immediately!
    if resp.status_code == 403 and "own email address" in resp.text:
        match = re.search(r'\(([^)]+@[^)]+)\)', resp.text)
        if match:
            fallback_recipient = match.group(1).strip()
            if fallback_recipient and fallback_recipient != recipient:
                logger.info(
                    "Resend account in testing mode. Delivering inquiry to registered account owner: %s",
                    fallback_recipient,
                )
                payload["to"] = [fallback_recipient]
                try:
                    resp_retry = requests.post(
                        "https://api.resend.com/emails",
                        json=payload,
                        headers=headers,
                        timeout=10,
                    )
                    if resp_retry.status_code in (200, 201):
                        logger.info(
                            "Contact notification email successfully delivered to Resend account owner %s (ID: %s)",
                            fallback_recipient,
                            resp_retry.json().get("id", "unknown"),
                        )
                        return True
                    resp = resp_retry
                except Exception as retry_err:
                    logger.warning("Retry to Resend account owner failed: %s", type(retry_err).__name__)

    # Resend API rejected with HTTP error (e.g. 403 testing restriction without account match, 400 validation, 429 rate limit, 500 error)
    # Log safely without exposing API keys or authorization headers:
    err_body = resp.text[:300] if resp.text else ""
    logger.warning(
        "Resend API rejected email for contact ID %s with status %s: %s",
        getattr(contact, "id", None),
        resp.status_code,
        err_body,
    )
    return False


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

    # Send email notification via Resend HTTPS API (without SMTP fallback)
    try:
        email_sent = send_contact_notification_email(contact)
    except Exception as email_err:
        logger.warning(
            "Unexpected error during contact email notification for ID %s: %s",
            getattr(contact, "id", None),
            type(email_err).__name__,
        )
        email_sent = False

    if email_sent:
        success_msg = (
            f"Thank you, {contact.name}! Your message has been sent successfully. "
            "I will get back to you soon."
        )
        if is_ajax:
            return JsonResponse({"success": True, "message": success_msg})
        messages.success(request, success_msg)
        return redirect("home")
    else:
        # Inquiry was saved in database, but email notification failed (e.g. Resend 403, timeout, etc.)
        warning_msg = (
            "Your inquiry was received, but email notification could not be sent. Please try again later."
        )
        if is_ajax:
            return JsonResponse({"success": False, "message": warning_msg}, status=200)
        messages.warning(request, warning_msg)
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