"""tests for tags api"""
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (Tag, Recipe)
from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')

def detail_url(tag_id):
    return reverse("recipe:tag-detail", args=[tag_id])

def create_user(email="user@exmaple.com", password="test123"):
    return get_user_model().objects.create_user(email=email, password=password)

class PublicTagApiTests(TestCase):
    """test unauthenticated API req"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """test auth is required for retrieving tags"""
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateTagsAPITests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """test retrieiving a list of tags"""
        Tag.objects.create(user=self.user, name="Vegan")
        Tag.objects.create(user=self.user, name="Dessert")

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by("-name")
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """test list of tags limited to authenticated user"""
        user2 = create_user(email="user2@example.com")
        Tag.objects.create(user = user2, name = "Asian")

        #for authenticated user
        tag = Tag.objects.create(user = self.user, name = "Comfort food")
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], tag.name)
        self.assertEqual(res.data[0]["id"], tag.id)

    def test_update_tag(self):
        tag = Tag.objects.create(user=self.user, name="dessert")

        payload = {"name": "dinner"}

        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        tag.refresh_from_db()

        self.assertEqual(tag.name, payload["name"])

    def test_delete_tag(self):
        tag = Tag.objects.create(user=self.user, name="dessert")
        url = detail_url(tag.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(user=self.user).exists())

    def test_filter_tags_assigned_to_recipes(self):
        """test listing tags by those assigned to recipes"""
        t1= Tag.objects.create(user=self.user, name="breakfast")
        t2= Tag.objects.create(user=self.user, name="dinner")

        recipe = Recipe.objects.create(
            title = "apple crumble",
            time_minutes = 5,
            price = Decimal("4.5"),
            user = self.user,
        )

        recipe.tags.add(t1)
        res = self.client.get(TAGS_URL, {"assigned_only" : 1})

        s1 = TagSerializer(t1)
        s2 = TagSerializer(t2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        """test filtered tags returna unique list"""
        tag = Tag.objects.create(user=self.user, name="breakfast")
        Tag.objects.create(user=self.user, name="dinner")
        r1 = Recipe.objects.create(
            title = "egg tarts",
            time_minutes = 5,
            price = Decimal("4.5"),
            user = self.user,
        )
        r2 = Recipe.objects.create(
            title = "apple pie",
            time_minutes = 56,
            price = Decimal("4.5"),
            user = self.user,
        )

        r1.tags.add(tag)
        r2.tags.add(tag)

        res = self.client.get(TAGS_URL, {"assigned_only": 1})
        self.assertEqual(len(res.data),1)





