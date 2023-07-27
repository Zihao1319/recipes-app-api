"""tests for ingredient api"""

from decimal import Decimal


from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (Ingredient, Recipe)
from recipe.serializers import IngredientSerializer

INGREDIENT_URL = reverse("recipe:ingredient-list")

def ingredient_url(ingredient_id):
    return reverse("recipe:ingredient-detail", args=[ingredient_id])

def create_user(email="user@exmaple.com", password="test123"):
    return get_user_model().objects.create_user(email=email, password=password)

class PublicIngredientApiTest(TestCase):
    """tests unauthenticated API req"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateIngredientApiTest(TestCase):
    """tests authenticated API req"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """test retrieving list of ingredients"""
        ingredient_1 = Ingredient.objects.create(user=self.user, name="curry leaves")
        ingredient_2 = Ingredient.objects.create(user=self.user, name="bell pepper")

        res = self.client.get(INGREDIENT_URL)
        ingredients = Ingredient.objects.all().order_by("-name")
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """only curr user can edit their own ingredients"""
        other_user = create_user(email="newuser@gmail.com", password="pass1234")
        other_user_ingredient = Ingredient.objects.create(user=other_user, name="lime")

        ingredient = Ingredient.objects.create(user=self.user, name="curry leaves")
        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], ingredient.name)
        self.assertEqual(res.data[0]["id"], ingredient.id)

    def test_update_ingredients(self):
        ingredient = Ingredient.objects.create(user=self.user, name="curry leaves")
        payload = {
            "name" : "lime"
        }

        url = ingredient_url(ingredient.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload["name"])

    def test_delete_ingredients(self):
        ingredient = Ingredient.objects.create(user=self.user, name="curry leaves")
        url = ingredient_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(user=self.user).exists())


    def test_filter_ingredients_assigned_to_recipes(self):
        """test listing ingredients by those assigned to recipes"""
        in1= Ingredient.objects.create(user=self.user, name="apples")
        in2= Ingredient.objects.create(user=self.user, name="pear")

        recipe = Recipe.objects.create(
            title = "apple crumble",
            time_minutes = 5,
            price = Decimal("4.5"),
            user = self.user,
        )

        recipe.ingredients.add(in1)
        res = self.client.get(INGREDIENT_URL, {"assigned_only" : 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """test filtered ingredients returna unique list"""
        ing = Ingredient.objects.create(user=self.user, name="eggs")
        Ingredient.objects.create(user=self.user, name="lentils")
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

        r1.ingredients.add(ing)
        r2.ingredients.add(ing)

        res = self.client.get(INGREDIENT_URL, {"assigned_only": 1})
        self.assertEqual(len(res.data),1)

