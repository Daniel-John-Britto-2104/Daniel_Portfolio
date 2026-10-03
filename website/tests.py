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
