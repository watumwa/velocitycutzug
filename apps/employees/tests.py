import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Employee


class EmployeeFormTests(TestCase):
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
            username="employee-admin",
            password="strong-pass-123",
        )
        self.client.force_login(self.user)

    def test_employee_create_normalizes_national_id_and_saves_photo(self):
        photo = SimpleUploadedFile("staff.jpg", b"fake-image-content", content_type="image/jpeg")

        response = self.client.post(
            reverse("employees:create"),
            {
                "name": "Grace",
                "phone": "256700000001",
                "national_id": " cm-1234-567890ab ",
                "photo": photo,
                "commission_type": Employee.CommissionType.PERCENTAGE,
                "commission_value": "35.00",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("employees:list"))
        employee = Employee.objects.get(name="Grace")
        self.assertEqual(employee.national_id, "CM1234567890AB")
        self.assertTrue(employee.photo.name.startswith("employees/photos/"))

    def test_employee_create_rejects_invalid_national_id(self):
        response = self.client.post(
            reverse("employees:create"),
            {
                "name": "Paul",
                "phone": "256700000002",
                "national_id": "12345",
                "commission_type": Employee.CommissionType.FIXED,
                "commission_value": "15000.00",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "National ID must be exactly 14 characters.")

    def test_employee_create_rejects_duplicate_national_id(self):
        Employee.objects.create(
            name="Sarah",
            national_id="CM1234567890AB",
            commission_type=Employee.CommissionType.PERCENTAGE,
            commission_value=Decimal("40.00"),
        )

        response = self.client.post(
            reverse("employees:create"),
            {
                "name": "Martha",
                "phone": "256700000003",
                "national_id": "cm1234567890ab",
                "commission_type": Employee.CommissionType.FIXED,
                "commission_value": "20000.00",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This National ID is already assigned to another employee.")
