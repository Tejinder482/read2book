from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.library.models import Book, Page
from apps.reader.models import Note

User = get_user_model()


class AuthApiTests(APITestCase):
    def test_register_and_me(self):
        res = self.client.post(
            "/api/auth/register/",
            {"email": "reader@example.com", "password": "secret12345", "first_name": "Ada"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", res.data)
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        me = self.client.get("/api/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["email"], "reader@example.com")
        self.assertFalse(me.data["profile"]["onboarding_completed"])

    def test_login(self):
        User.objects.create_user(email="a@b.com", password="secret12345")
        res = self.client.post(
            "/api/auth/login/",
            {"email": "a@b.com", "password": "secret12345"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)


class BookOwnershipTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@ex.com", password="secret12345")
        self.other = User.objects.create_user(email="other@ex.com", password="secret12345")
        self.book = Book.objects.create(
            owner=self.owner,
            title="Owned Book",
            status=Book.Status.READY,
            page_count=2,
        )
        Page.objects.create(book=self.book, number=1, text="Hello attention world")
        Page.objects.create(book=self.book, number=2, text="More text")

    def test_other_user_cannot_access_book(self):
        self.client.force_authenticate(user=self.other)
        res = self.client.get(f"/api/books/{self.book.id}/")
        self.assertEqual(res.status_code, 404)

    def test_note_anchor(self):
        self.client.force_authenticate(user=self.owner)
        res = self.client.post(
            "/api/notes/",
            {
                "book": self.book.id,
                "page_number": 1,
                "selected_text": "attention",
                "body": "Revise for exam",
                "tags": ["Exam"],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        note = Note.objects.get(pk=res.data["id"])
        self.assertEqual(note.page.number, 1)
        self.assertEqual(note.book_id, self.book.id)
        self.assertEqual(note.selected_text, "attention")

    def test_search(self):
        self.client.force_authenticate(user=self.owner)
        res = self.client.get(f"/api/books/{self.book.id}/search/", {"q": "attention"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.data["results"]) >= 1)


class AIKeyTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="ai@ex.com", password="secret12345")
        self.client.force_authenticate(user=self.user)

    def test_create_key_hides_secret(self):
        res = self.client.post(
            "/api/ai-keys/",
            {"provider": "openai", "api_key": "sk-test-secret-key-123456", "label": "main"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertNotIn("api_key", res.data)
        self.assertNotIn("encrypted_key", res.data)
        self.assertEqual(res.data["key_last4"], "3456")
