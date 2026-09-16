from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.email.split("@")[0]


class Profile(models.Model):
    class Theme(models.TextChoices):
        LIGHT = "light", "Light"
        SEPIA = "sepia", "Sepia"
        DARK = "dark", "Dark"

    class LineSpacing(models.TextChoices):
        NORMAL = "normal", "Normal"
        RELAXED = "relaxed", "Relaxed"
        WIDE = "wide", "Wide"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    onboarding_completed = models.BooleanField(default=False)
    use_cases = models.JSONField(default=list, blank=True)
    help_goals = models.JSONField(default=list, blank=True)
    font_size = models.PositiveSmallIntegerField(default=18)
    line_spacing = models.CharField(
        max_length=20, choices=LineSpacing.choices, default=LineSpacing.RELAXED
    )
    theme = models.CharField(max_length=20, choices=Theme.choices, default=Theme.LIGHT)
    font_family = models.CharField(max_length=60, default="Source Serif 4")
    reading_width = models.CharField(max_length=20, default="medium")
    preferred_ai_provider = models.CharField(max_length=40, blank=True, default="")
    explanation_level = models.CharField(max_length=40, default="balanced")
    preferred_language = models.CharField(max_length=40, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile<{self.user.email}>"


class AIProviderKey(models.Model):
    class Provider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        GEMINI = "gemini", "Google Gemini"
        ANTHROPIC = "anthropic", "Anthropic"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_keys")
    provider = models.CharField(max_length=40, choices=Provider.choices)
    label = models.CharField(max_length=100, blank=True, default="")
    encrypted_key = models.TextField()
    key_last4 = models.CharField(max_length=4, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "provider", "label")
        ordering = ["provider", "-updated_at"]

    def __str__(self):
        return f"{self.provider} ····{self.key_last4}"
