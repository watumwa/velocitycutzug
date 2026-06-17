from io import BytesIO

from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.db import models
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.core.models import TimeStampedModel


class Service(TimeStampedModel):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=0)
    support_commission_enabled = models.BooleanField(
        default=False,
        help_text="Enable a fixed support commission for a second employee on this service.",
    )
    support_commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text="Fixed amount paid to the support employee when this service is approved.",
    )
    is_active = models.BooleanField(default=True)
    photo = models.FileField(
        upload_to="services/photos/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])],
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} - {self.price}"

    def save(self, *args, **kwargs):
        self._resize_photo_safely()
        super().save(*args, **kwargs)

    def _resize_photo_safely(self):
        """Resize uploaded photos without allowing image issues to crash production."""
        if not self.photo or not hasattr(self.photo, "file"):
            return
        try:
            self.photo.file.seek(0)
            img = Image.open(self.photo)
            img = ImageOps.exif_transpose(img)
        except (UnidentifiedImageError, OSError, ValueError):
            return

        if img.height <= 800 and img.width <= 800:
            try:
                self.photo.file.seek(0)
            except Exception:
                pass
            return

        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        image_format = (img.format or "JPEG").upper()
        if image_format == "JPG":
            image_format = "JPEG"
        if image_format not in {"JPEG", "PNG", "WEBP"}:
            image_format = "JPEG"
        if image_format == "JPEG" and img.mode not in {"RGB", "L"}:
            img = img.convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format=image_format, quality=85, optimize=True)
        self.photo.save(self.photo.name, ContentFile(buffer.getvalue()), save=False)
