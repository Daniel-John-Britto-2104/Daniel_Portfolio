from unittest.mock import patch, MagicMock
import requests

from django.conf import settings
from django.contrib import admin
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from website.models import Profile, Contact
from website.views import send_contact_notification_email


class PortfolioTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.profile = Profile.objects.create(
            full_name="Daniel John Britto",
            title="Python Backend Developer",
            email="danieljohnbrittoaj@gmail.com"
        )

    # -------------------------------------------------------------------------
    # Core View & Form Validation Tests
    # -------------------------------------------------------------------------
    def test_home_view(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Daniel John Britto")
        self.assertContains(response, "danieljohnbrittoaj@gmail.com")
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="subject"')
        self.assertContains(response, 'name="message"')
        self.assertContains(response, "csrfmiddlewaretoken")

    @patch("website.views.requests.post")
    def test_contact_submission_standard(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "resend_test_ok"}
        mock_post.return_value = mock_resp

        response = self.client.post(reverse("contact_submit"), {
            "name": "Jane Tester",
            "email": "jane@example.com",
            "subject": "Job Offer",
            "message": "We would love to hire you as a Backend Developer."
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), 1)
        msg = Contact.objects.first()
        self.assertEqual(msg.name, "Jane Tester")
        self.assertContains(response, "Your message has been sent successfully")
        # No SMTP backend called
        self.assertEqual(len(mail.outbox), 0)

    @patch("website.views.requests.post")
    def test_contact_submission_ajax(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "resend_ajax_ok"}
        mock_post.return_value = mock_resp

        response = self.client.post(
            reverse("contact_submit"),
            {
                "name": "Alex AJAX",
                "email": "alex@example.com",
                "subject": "API Integration",
                "message": "Interested in your Flask microservices work."
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))
        self.assertEqual(Contact.objects.count(), 1)

    @patch("website.views.requests.post")
    def test_hire_submission_endpoint(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "resend_hire_ok"}
        mock_post.return_value = mock_resp

        response = self.client.post(
            reverse("hire_submit"),
            {
                "name": "Recruiter Rob",
                "email": "rob@techcompany.com",
                "subject": "Python Developer Opening",
                "message": "We have an open Python/Django role in our team."
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    @patch("website.views.requests.post")
    def test_hire_me_alias_endpoint(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "resend_hire_me_ok"}
        mock_post.return_value = mock_resp

        response = self.client.post(
            reverse("hire_me_submit"),
            {
                "name": "CTO Claire",
                "email": "claire@startup.io",
                "subject": "Backend Contract",
                "message": "Can you consult on our database schema?"
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))
        self.assertEqual(Contact.objects.count(), 1)

    def test_contact_submission_allows_an_empty_optional_subject(self):
        with patch("website.views.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"id": "ok"}
            mock_post.return_value = mock_resp

            response = self.client.post(reverse("contact_submit"), {
                "name": "Jane Tester",
                "email": "jane@example.com",
                "subject": "",
                "message": "Hello!",
            })
            self.assertEqual(response.status_code, 302)
            contact = Contact.objects.get()
            self.assertEqual(contact.subject, "")

    def test_contact_submission_rejects_empty_required_fields(self):
        response = self.client.post(
            reverse("contact_submit"),
            {"name": "", "email": "", "subject": "", "message": ""},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertEqual(Contact.objects.count(), 0)

    def test_contact_submission_rejects_invalid_email(self):
        response = self.client.post(
            reverse("contact_submit"),
            {
                "name": "Jane Tester",
                "email": "not-an-email",
                "subject": "",
                "message": "Hello!",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["message"].lower())
        self.assertEqual(Contact.objects.count(), 0)

    def test_contact_submission_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("contact_submit"),
            {
                "name": "Jane Tester",
                "email": "jane@example.com",
                "subject": "",
                "message": "Hello!",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Contact.objects.count(), 0)

    def test_contact_is_registered_in_admin(self):
        self.assertTrue(admin.site.is_registered(Contact))

    def test_seo_endpoints(self):
        robots_res = self.client.get(reverse("robots_txt"))
        self.assertEqual(robots_res.status_code, 200)
        self.assertIn("User-agent: *", robots_res.content.decode())

        sitemap_res = self.client.get(reverse("sitemap_xml"))
        self.assertEqual(sitemap_res.status_code, 200)
        self.assertIn("urlset", sitemap_res.content.decode())

    # -------------------------------------------------------------------------
    # Required Resend HTTPS API Tests (Scenarios 1 to 10)
    # -------------------------------------------------------------------------

    # 1. Resend API accepts the email request
    @patch("website.views.requests.post")
    def test_1_resend_api_accepts_email_request(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "resend_123"}
        mock_post.return_value = mock_resp

        contact = Contact.objects.create(
            name="Alice Success",
            email="alice@example.com",
            subject="Collaboration",
            message="Looking forward to working with you.",
        )

        with override_settings(RESEND_API_KEY="re_valid_api_key"):
            result = send_contact_notification_email(contact)

        self.assertTrue(result)
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args[0][0], "https://api.resend.com/emails")

    # 2. Resend returns HTTP 403 (e.g. unverified domain or sandbox restriction)
    @patch("website.views.requests.post")
    def test_2_resend_api_returns_http_403(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = '{"statusCode": 403, "message": "You can only send testing emails to your own email address"}'
        mock_post.return_value = mock_resp

        contact = Contact.objects.create(
            name="Bob Restricted",
            email="bob@restricted.com",
            subject="Restricted Inquiry",
            message="Testing 403 error response.",
        )

        with override_settings(RESEND_API_KEY="re_test_key"):
            result = send_contact_notification_email(contact)

        # Must return False safely and not raise an exception
        self.assertFalse(result)
        # No SMTP fallback should have happened
        self.assertEqual(len(mail.outbox), 0)

    # 3. Resend returns another HTTP error (e.g. 500, 422, 429)
    @patch("website.views.requests.post")
    def test_3_resend_api_returns_another_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        contact = Contact.objects.create(
            name="Charlie Error",
            email="charlie@error.com",
            subject="Server Issue",
            message="Testing 500 server error response.",
        )

        with override_settings(RESEND_API_KEY="re_test_key"):
            result = send_contact_notification_email(contact)

        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    # 4. API key is missing
    @patch("website.views.requests.post")
    def test_4_resend_api_key_missing(self, mock_post):
        contact = Contact.objects.create(
            name="Diana NoKey",
            email="diana@nokey.com",
            subject="No Key",
            message="Testing behavior when API key is missing.",
        )

        with override_settings(RESEND_API_KEY=""):
            result = send_contact_notification_email(contact)

        self.assertFalse(result)
        mock_post.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)

    # 5. API request times out
    @patch("website.views.requests.post")
    def test_5_resend_api_request_times_out(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out after 10s")

        contact = Contact.objects.create(
            name="Evan Timeout",
            email="evan@timeout.com",
            subject="Timeout Test",
            message="Testing timeout handling.",
        )

        with override_settings(RESEND_API_KEY="re_test_key"):
            result = send_contact_notification_email(contact)

        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    # 6. Contact form submission still preserves the inquiry when email fails
    @patch("website.views.requests.post")
    def test_6_contact_submission_preserves_inquiry_when_email_fails(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = '{"statusCode": 403, "message": "Domain not verified"}'
        mock_post.return_value = mock_resp

        response = self.client.post(
            reverse("contact_submit"),
            {
                "name": "Fiona Preserved",
                "email": "fiona@preserved.com",
                "subject": "Preserve My Inquiry",
                "message": "Even if email fails, database must store my message.",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Must return HTTP 200 with clear non-crash status
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("inquiry was received", response.json()["message"])
        self.assertIn("email notification could not be sent", response.json()["message"])

        # Inquiry MUST remain preserved in the database
        self.assertEqual(Contact.objects.filter(email="fiona@preserved.com").count(), 1)
        saved = Contact.objects.get(email="fiona@preserved.com")
        self.assertEqual(saved.name, "Fiona Preserved")
        self.assertEqual(saved.message, "Even if email fails, database must store my message.")

    # 7. Contact and Hire Me forms display the appropriate success or failure message
    @patch("website.views.requests.post")
    def test_7_contact_and_hire_forms_display_appropriate_messages(self, mock_post):
        endpoints = [
            ("contact_submit", "Contact Form"),
            ("hire_submit", "Hire Form"),
            ("hire_me_submit", "Hire Me Alias"),
        ]

        # Case A: Success
        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.json.return_value = {"id": "resend_test_ok"}
        mock_post.return_value = mock_resp_ok

        for url_name, label in endpoints:
            response = self.client.post(
                reverse(url_name),
                {
                    "name": f"Success Visitor {label}",
                    "email": "visitor@example.com",
                    "subject": f"Inquiry for {label}",
                    "message": "Testing success response.",
                },
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["success"])
            self.assertIn("sent successfully", response.json()["message"].lower())

        # Case B: Failure (e.g. 403 or network issue)
        mock_resp_err = MagicMock()
        mock_resp_err.status_code = 403
        mock_resp_err.text = "Forbidden"
        mock_post.return_value = mock_resp_err

        for url_name, label in endpoints:
            response = self.client.post(
                reverse(url_name),
                {
                    "name": f"Failure Visitor {label}",
                    "email": "visitor2@example.com",
                    "subject": f"Inquiry for {label}",
                    "message": "Testing failure response.",
                },
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()["success"])
            self.assertIn("inquiry was received", response.json()["message"].lower())
            self.assertIn("could not be sent", response.json()["message"].lower())

    # 8. No Gmail SMTP fallback is attempted
    @patch("website.views.requests.post")
    @patch.object(EmailMultiAlternatives, "send")
    def test_8_no_gmail_smtp_fallback_attempted(self, mock_smtp_send, mock_post):
        # Even when Resend throws an error or fails
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        mock_post.return_value = mock_resp

        contact = Contact.objects.create(
            name="George NoSMTP",
            email="george@nosmtp.com",
            subject="No SMTP",
            message="Ensure SMTP is never invoked on failure.",
        )

        with override_settings(RESEND_API_KEY="re_test_key"):
            send_contact_notification_email(contact)

        # Verification: SMTP send was NEVER invoked
        mock_smtp_send.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)

    # 9. Visitor email and message details are included correctly
    @patch("website.views.requests.post")
    def test_9_visitor_email_and_message_details_included_correctly(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "resend_check_payload"}
        mock_post.return_value = mock_resp

        contact = Contact.objects.create(
            name="Bruce Wayne",
            email="bruce@wayneenterprises.com",
            subject="Confidential Project",
            message="Need advanced Python architecture for our security cluster.",
        )

        with override_settings(
            RESEND_API_KEY="re_valid_api_key_123",
            DEFAULT_FROM_EMAIL="Portfolio <onboarding@resend.dev>",
            CONTACT_RECIPIENT_EMAIL="danieljohnbrittoaj@gmail.com",
        ):
            send_contact_notification_email(contact)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://api.resend.com/emails")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer re_valid_api_key_123")

        payload = kwargs["json"]
        self.assertEqual(payload["to"], ["danieljohnbrittoaj@gmail.com"])
        self.assertEqual(payload["reply_to"], "bruce@wayneenterprises.com")
        self.assertEqual(payload["from"], "Portfolio <onboarding@resend.dev>")
        self.assertIn("Confidential Project", payload["subject"])
        self.assertIn("Bruce Wayne", payload["text"])
        self.assertIn("bruce@wayneenterprises.com", payload["text"])
        self.assertIn("Need advanced Python architecture", payload["text"])
        self.assertIn("Bruce Wayne", payload["html"])
        self.assertIn("bruce@wayneenterprises.com", payload["html"])

    # 10. Existing functionality remains unaffected
    def test_10_existing_functionality_remains_unaffected(self):
        # Check active profile in DB
        self.assertEqual(Profile.objects.filter(is_active=True).first().full_name, "Daniel John Britto")

        # Check contact model can be created and queried directly
        c = Contact.objects.create(
            name="Model Tester",
            email="tester@example.com",
            subject="Model Test",
            message="Direct DB test",
        )
        self.assertIsNotNone(c.pk)
        self.assertEqual(str(c), f"Message from {c.name} - {c.subject}")
