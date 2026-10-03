from django.test import TestCase, Client
from django.urls import reverse
from website.models import Profile, ContactMessage


class PortfolioTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.profile = Profile.objects.create(
            full_name="Daniel John Britto",
            title="Python Backend Developer",
            email="danielamalraj309@gmail.com"
        )

    def test_home_view(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Daniel John Britto")

    def test_contact_submission_standard(self):
        response = self.client.post(reverse("contact_submit"), {
            "name": "Jane Tester",
            "email": "jane@example.com",
            "subject": "Job Offer",
            "message": "We would love to hire you as a Backend Developer."
        })
        self.assertEqual(response.status_code, 302)  # redirect to home
        self.assertEqual(ContactMessage.objects.count(), 1)
        msg = ContactMessage.objects.first()
        self.assertEqual(msg.name, "Jane Tester")

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
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_seo_endpoints(self):
        robots_res = self.client.get(reverse("robots_txt"))
        self.assertEqual(robots_res.status_code, 200)
        self.assertIn("User-agent: *", robots_res.content.decode())

        sitemap_res = self.client.get(reverse("sitemap_xml"))
        self.assertEqual(sitemap_res.status_code, 200)
        self.assertIn("urlset", sitemap_res.content.decode())
