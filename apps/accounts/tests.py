from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="owner",
            password="strong-pass-123",
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Velocity Cutz")
        self.assertContains(response, "Email or username")
        self.assertNotContains(response, "Salon Management")
        self.assertNotContains(response, "Welcome back")

    def test_protected_home_redirects_to_login(self):
        response = self.client.get(reverse("home"))

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('home')}")

    def test_valid_login_redirects_to_home(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "owner",
                "password": "strong-pass-123",
                "remember_me": "on",
            },
        )

        self.assertRedirects(response, reverse("home"))

    def test_logout_ends_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("accounts:login"))
