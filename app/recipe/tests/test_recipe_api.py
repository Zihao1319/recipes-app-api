"""test for recipe api"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
import tempfile
import os

from PIL import Image

from core.models import (
    Recipe,
    Tag,
    Ingredient,
)
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer
)

from rest_framework.test import APIClient
from rest_framework import status

RECIPES_URL = reverse("recipe:recipe-list")

def image_upload_url(recipe_id):
    return reverse("recipe:recipe-upload-image", args=[recipe_id])

#each detail url is going to be different and hence it is defined as a function
def detail_url (recipe_id):
    """create and return a recipe detail url"""
    return reverse ("recipe:recipe-detail", args=[recipe_id])

def create_recipe(user, **params):
    """create and return sample recipe"""
    defaults = {
        "title": "sample recipe title",
        "time_minutes" : 22,
        "price": Decimal("5.50"),
        "description": "some description",
        "link": "https://example.com/recipe.pdf",
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe

def create_user(**params):
    return get_user_model().objects.create_user(**params)

class PublicRecipeApiTests(TestCase):
    """test authenticated api requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """testing authenticated api requests"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email = "user@example.com",
            password = "test1234"
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipe(self):
        """test retrieving a list of recipes"""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by("-id")
        #many=true here so that all the recipes will be returned, instead of 1
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """test list of recipes is limited to authenticated user"""
        other_user = create_user(
            email = "user2@example.com",
            password = "test1234"
        )

        create_recipe(self.user)
        create_recipe(other_user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """test get recipe detail"""
        recipe = create_recipe(self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """test creating a recipe"""
        payload = {
            "title": "sample recipe title",
            "time_minutes" : 22,
            "price": Decimal("5.50"),
        }
        res = self.client.post(RECIPES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data["id"])

        for k,v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        original_link = "https://example.com/recipe.pdf"
        recipe = create_recipe(
            user = self.user,
            title = "sample recipe title",
            link = original_link,
        )

        payload = {"title": "New recipe title"}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload["title"])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """test full update of recipe"""
        payload = {
            "title": "new recipe title",
            "link" : "https://www.example.com/new_recipe",
            "price": Decimal("5.99"),
            "time_minutes" : 60,
            "description" : "new description"
        }

        recipe = create_recipe(
            user = self.user,
            title="sample title",
            link="https://www.example.com/recipe",
            description = "some description",
        )

        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipe.refresh_from_db()

        for k,v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        new_user = create_user(email="user2@example.com", password="pass123")
        recipe = create_recipe(user=self.user)

        payload = {"user": new_user.id}
        url = detail_url(recipe.id)

        res = self.client.patch(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        """tests trying to delete another users recipe gives error"""
        new_user = create_user(email="user2@example.com", password="pass123")
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        payload = {
            "title": "thai prawn curry",
            "time_minutes": 30,
            "price": Decimal("2.50"),
            "tags" : [{ "name" : "thai"}, { "name": "dinner"}]
        }

        res = self.client.post(RECIPES_URL, payload, format= "json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)

        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload["tags"]:
            exists = recipe.tags.filter(
                name = tag["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        tag_indian = Tag.objects.create(user=self.user, name="Indian")
        payload = {
            "title": "Pongal",
            "time_minutes": 60,
            "price": Decimal("6.50"),
            "tags" : [{ "name" : "Indian"}, { "name": "Breakfast"}]
        }

        res = self.client.post(RECIPES_URL, payload, format = "json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]

        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload["tags"]:
            exists = recipe.tags.filter(
                name = tag["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tags_on_update(self):
        recipe = create_recipe(user=self.user)
        payload = {"tags": [{"name": "lunch"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name="lunch")
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        tag_breakfast = Tag.objects.create(user=self.user, name="Breakfast")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name="Lunch")
        payload = {"tags": [{"name": "Lunch"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        tag = Tag.objects.create(user=self.user, name="dessert")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {"tags": []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """test creating new recipe with ingredients"""
        payload = {
            "title": "thai prawn curry",
            "time_minutes": 30,
            "price": Decimal("2.50"),
            "tags" : [{ "name" : "thai"}, { "name": "dinner"}],
            "ingredients" : [{"name" : "prawns"}, {"name" : "coconut"}]
        }

        res = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for i in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                name=i["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        ingredient = Ingredient.objects.create(user=self.user, name="coconut")

        payload = {
            "title": "thai prawn curry",
            "time_minutes": 30,
            "price": Decimal("2.50"),
            "tags" : [{ "name" : "thai"}, { "name": "dinner"}],
            "ingredients" : [{"name" : "prawns"}, {"name" : "coconut"}]
        }

        res = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())

        for i in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                name=i["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredients_on_update(self):
        recipe = create_recipe(user=self.user)
        payload = {
            "ingredients": [{"name": "salt" }]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name="salt")
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredients(self):
        salt_ingredient = Ingredient.objects.create(user=self.user, name="salt")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(salt_ingredient)

        potato_ingredient = Ingredient.objects.create(user=self.user, name="potato")
        payload = {"ingredients" : [{"name" : "potato"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(potato_ingredient, recipe.ingredients.all())
        self.assertNotIn(salt_ingredient, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        ingredient1 = Ingredient.objects.create(user=self.user, name="salt")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        payload = { "ingredients" : [] }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        r1 = create_recipe(user=self.user, title="thai curry")
        r2 = create_recipe(user=self.user, title="eggplant")
        r3 = create_recipe(user=self.user, title="fish and chips")

        tag1 = Tag.objects.create(user=self.user, name="vegan")
        tag2 = Tag.objects.create(user=self.user, name="vegetarian")

        r1.tags.add(tag1)
        r2.tags.add(tag2)

        params = {"tags": f'{tag1.id}, {tag2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        r1 = create_recipe(user=self.user, title="nasi lemak")
        r2 = create_recipe(user=self.user, title="mee rebus")
        r3 = create_recipe(user=self.user, title="french fries")

        in1 = Ingredient.objects.create(user=self.user, name="chicken")
        in2 = Ingredient.objects.create(user=self.user, name="sambal")

        r1.ingredients.add(in1)
        r2.ingredients.add(in2)

        params = {"ingredients": f'{in1.id}, {in2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@example.com",
            "pass12345"
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)
            payload = {"image": image_file}
            res = self.client.post(url, payload, format="multipart")

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.recipe.id)
        payload = {"image": "notanimage"}
        res = self.client.post(url, payload, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)













