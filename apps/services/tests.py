import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.services.catalog import CATALOG_SERVICE_NAMES
from apps.services.models import Service


class ServiceCatalogViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="service-admin",
            password="strong-pass-123",
        )
        self.client.force_login(self.user)

    def test_service_list_bootstraps_the_catalog(self):
        response = self.client.get(reverse("services:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Service.objects.filter(name__in=CATALOG_SERVICE_NAMES).count(),
            len(CATALOG_SERVICE_NAMES),
        )
        self.assertContains(response, "Hair Services")
        self.assertContains(response, "Add Service")

    def test_create_route_accepts_custom_service_with_photo(self):
        response = self.client.get(reverse("services:create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create a custom service")

        photo = SimpleUploadedFile("beard.jpg", b"fake-image-content", content_type="image/jpeg")
        response = self.client.post(
            reverse("services:create"),
            {
                "name": "Executive Beard Sculpt",
                "price": "30000",
                "is_active": "on",
                "photo": photo,
            },
        )

        self.assertRedirects(response, reverse("services:list"))
        service = Service.objects.get(name="Executive Beard Sculpt")
        self.assertEqual(service.price, Decimal("30000"))
        self.assertTrue(service.is_active)
        self.assertTrue(service.photo.name.startswith("services/photos/"))

    def test_catalog_service_can_update_price_status_and_photo(self):
        service = Service.objects.create(name="Manicure", price=Decimal("0"))
        photo = SimpleUploadedFile("manicure.png", b"fake-image-content", content_type="image/png")

        response = self.client.post(
            reverse("services:edit", args=[service.pk]),
            {"price": "15000", "photo": photo},
        )

        self.assertRedirects(response, reverse("services:list"))
        service.refresh_from_db()
        self.assertEqual(service.price, Decimal("15000"))
        self.assertFalse(service.is_active)
        self.assertTrue(service.photo.name.startswith("services/photos/"))
