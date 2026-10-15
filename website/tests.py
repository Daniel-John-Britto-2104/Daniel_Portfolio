from unittest.mock import patch
from django.core import mail
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import admin

from website.models import Profile, Contact


class PortfolioTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.profile = Profile.objects.create(
            full_name="Daniel John Britto",
            title="Python Backend Developer",
            email="danieljohnbrittoaj@gmail.com"
        )

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

    def test_contact_submission_standard(self):
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

        # Verify email notification sent to Daniel
        self.assertEqual(len(mail.outbox), 1)
        sent_mail = mail.outbox[0]
        self.assertEqual(sent_mail.to, ["danieljohnbrittoaj@gmail.com"])
        self.assertEqual(sent_mail.reply_to, ["jane@example.com"])
        self.assertIn("Job Offer", sent_mail.subject)
        self.assertIn("Jane Tester", sent_mail.body)
        self.assertIn("We would love to hire you as a Backend Developer.", sent_mail.body)

    def test_contact_submission_ajax(self):
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

    def test_hire_submission_endpoint(self):
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
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["danieljohnbrittoaj@gmail.com"])
        self.assertEqual(sent.reply_to, ["rob@techcompany.com"])
        self.assertIn("Python Developer Opening", sent.subject)
        self.assertIn("Recruiter Rob", sent.body)

    def test_hire_me_alias_endpoint(self):
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

    @patch("website.views.send_contact_notification_email")
    def test_contact_submission_handles_email_failure_gracefully(self, mock_send):
        mock_send.side_effect = Exception("SMTP Connection Failed")
        response = self.client.post(
            reverse("contact_submit"),
            {
                "name": "Jane Tester",
                "email": "jane@example.com",
                "subject": "Inquiry",
                "message": "Testing SMTP error handling."
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        # Should return error status and NOT a success status
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json()["success"])
        self.assertIn("danieljohnbrittoaj@gmail.com", response.json()["message"])
        # The contact should still be saved in the database
        self.assertEqual(Contact.objects.count(), 1)

    def test_contact_submission_allows_an_empty_optional_subject(self):
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

    @patch("website.views.requests.post")
    def test_send_contact_email_resend_success(self, mock_post):
        from website.views import send_contact_notification_email
        from django.test import override_settings
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "resend_test_123"}
        mock_post.return_value = mock_resp

        contact = Contact.objects.create(
            name="Alice Wonder",
            email="alice@wonderland.com",
            subject="Project Inquiry",
            message="Let's build something amazing together.",
        )

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
            RESEND_API_KEY="re_test_key_123",
            RESEND_FROM_EMAIL="Portfolio <onboarding@resend.dev>",
            CONTACT_RECIPIENT_EMAIL="danieljohnbrittoaj@gmail.com",
        ):
            send_contact_notification_email(contact)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://api.resend.com/emails")
        self.assertEqual(kwargs["json"]["to"], ["danieljohnbrittoaj@gmail.com"])
        self.assertEqual(kwargs["json"]["reply_to"], "alice@wonderland.com")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer re_test_key_123")
        self.assertIn("Project Inquiry", kwargs["json"]["subject"])
        # Standard email backend should not have been called
        self.assertEqual(len(mail.outbox), 0)

    @patch("website.views.requests.post")
    def test_send_contact_email_resend_fallback(self, mock_post):
        from website.views import send_contact_notification_email
        from django.test import override_settings
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        contact = Contact.objects.create(
            name="Bob Fallback",
            email="bob@fallback.com",
            subject="Fallback Subject",
            message="Testing automatic fallback.",
        )

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            RESEND_API_KEY="re_test_key_123",
            CONTACT_RECIPIENT_EMAIL="danieljohnbrittoaj@gmail.com",
        ):
            # In locmem (testing) or when Resend returns non-200, it falls back cleanly to Django outbox
            send_contact_notification_email(contact)

        # Django locmem backend caught the fallback
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["danieljohnbrittoaj@gmail.com"])
        self.assertEqual(mail.outbox[0].reply_to, ["bob@fallback.com"])
