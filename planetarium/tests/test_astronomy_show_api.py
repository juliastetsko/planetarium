import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from planetarium.models import AstronomyShow, ShowTheme, PlanetariumDome, ShowSession
from planetarium.serializers import (
    AstronomyShowListSerializer,
    AstronomyShowDetailSerializer,
)

ASTRONOMY_SHOW_URL = reverse("planetarium:astronomyshow-list")
SHOW_SESSION_URL = reverse("planetarium:showsession-list")


def sample_astronomy_show(**params):
    defaults = {
        "title": "Sample show",
        "description": "Sample description",
    }
    defaults.update(params)

    return AstronomyShow.objects.create(**defaults)


def sample_show_theme(**params):
    defaults = {
        "name": "Stars",
    }
    defaults.update(params)

    return ShowTheme.objects.create(**defaults)


def sample_show_session(**params):
    planetarium_dome = PlanetariumDome.objects.create(
        name="The best", rows=10, seats_in_row=5
    )

    defaults = {
        "astronomy_show": None,
        "planetarium_dome": planetarium_dome,
        "show_time": "2024-04-02 17:00:00",
    }
    defaults.update(params)

    return ShowSession.objects.create(**defaults)


def image_upload_url(astronomy_show_id):
    """Return URL for recipe image upload"""
    return reverse("planetarium:astronomyshow-upload-image", args=[astronomy_show_id])


def detail_url(astronomy_show_id):
    return reverse("planetarium:astronomyshow-detail", args=[astronomy_show_id])


class AstronomyShowImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@example.com", "difficult_password"
        )
        self.client.force_authenticate(self.user)
        self.astronomy_show = sample_astronomy_show()
        self.show_theme = sample_show_theme()
        self.show_session = sample_show_session(astronomy_show=self.astronomy_show)

    def tearDown(self):
        self.astronomy_show.image.delete()

    def test_upload_image_to_astronomy_show(self):
        """Test uploading an image to astronomy show"""
        url = image_upload_url(self.astronomy_show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            result = self.client.post(url, {"image": ntf}, format="multipart")
        self.astronomy_show.refresh_from_db()

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertIn("image", result.data)
        self.assertTrue(os.path.exists(self.astronomy_show.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.astronomy_show.id)
        result = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_astronomy_show_list(self):
        url = ASTRONOMY_SHOW_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            result = self.client.post(
                url,
                {
                    "title": "Sky",
                    "description": "Very interesting",
                    "show_themes": [],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
        astronomy_show = AstronomyShow.objects.get(title="Sky")
        self.assertFalse(astronomy_show.image)

    def test_image_url_is_shown_on_astronomy_show_detail(self):
        url = image_upload_url(self.astronomy_show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        result = self.client.get(detail_url(self.astronomy_show.id))

        self.assertIn("image", result.data)

    def test_image_url_is_shown_on_astronomy_show_list(self):
        url = image_upload_url(self.astronomy_show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        result = self.client.get(ASTRONOMY_SHOW_URL)

        self.assertIn("image", result.data[0].keys())

    def test_image_url_is_shown_on_show_session_detail(self):
        url = image_upload_url(self.astronomy_show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        result = self.client.get(SHOW_SESSION_URL)

        self.assertIn("astronomy_show_image", result.data[0].keys())


class UnauthenticatedAstronomyShowApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(ASTRONOMY_SHOW_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAstronomyShowApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="julia@test.test", password="difficult_password12345"
        )
        self.client.force_authenticate(self.user)

    def test_astronomy_shows_list(self):
        sample_astronomy_show()
        astronomy_show_with_theme = sample_astronomy_show()

        astronomy_show_with_theme.show_themes.add(sample_show_theme())

        result = self.client.get(ASTRONOMY_SHOW_URL)
        astronomy_shows = AstronomyShow.objects.all()
        serializer = AstronomyShowListSerializer(astronomy_shows, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_filter_astronomy_show_by_title(self):
        astronomy_show_1 = sample_astronomy_show(title="Stars")
        astronomy_show_2 = sample_astronomy_show(title="Planets")

        result = self.client.get(ASTRONOMY_SHOW_URL, {"title": "Stars"})

        serializer_1 = AstronomyShowListSerializer(astronomy_show_1)
        serializer_2 = AstronomyShowListSerializer(astronomy_show_2)

        self.assertIn(serializer_1.data, result.data)
        self.assertNotIn(serializer_2.data, result.data)

    def test_filter_astronomy_show_by_show_themes(self):
        show_themes_1 = ShowTheme.objects.create(name="Stars")
        show_themes_2 = ShowTheme.objects.create(name="Planets")

        astronomy_show_1 = sample_astronomy_show(title="Theory of Supernova")
        astronomy_show_2 = sample_astronomy_show(title="Solar system guide")

        astronomy_show_1.show_themes.add(show_themes_1)
        astronomy_show_2.show_themes.add(show_themes_2)

        astronomy_show_3 = sample_astronomy_show(
            title="Astronomy show without show theme"
        )

        result = self.client.get(ASTRONOMY_SHOW_URL, {"show_themes": "Stars, Planets"})

        serializer1 = AstronomyShowListSerializer(astronomy_show_1)
        serializer2 = AstronomyShowListSerializer(astronomy_show_2)
        serializer3 = AstronomyShowListSerializer(astronomy_show_3)

        self.assertIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertNotIn(serializer3.data, result.data)


def test_retrieve_astronomy_show_detail(self):
    astronomy_show = sample_astronomy_show()

    astronomy_show.show_themes.add(sample_show_theme())

    url = detail_url(astronomy_show.id)

    result = self.client.get(url)

    serializer = AstronomyShowDetailSerializer(astronomy_show)

    self.assertEqual(result.status_code, status.HTTP_200_OK)
    self.assertEqual(result.data, serializer.data)


def test_create_astronomy_show_forbidden(self):
    payload = {
        "title": "Stars",
        "description": "Something interesting",
    }

    result = self.client.post(ASTRONOMY_SHOW_URL, payload)

    self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminAstronomyShowTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="superadmin@test.test", password="super_password54321", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_astronomy_show(self):
        payload = {
            "title": "Planets",
            "description": "Very interesting show",
        }

        result = self.client.post(ASTRONOMY_SHOW_URL, payload)

        astronomy_show = AstronomyShow.objects.get(id=result.data["id"])

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(astronomy_show, key))

    def test_delete_astronomy_show_not_allowed(self):
        astronomy_show = sample_astronomy_show()

        url = detail_url(astronomy_show.id)

        result = self.client.delete(url)

        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
