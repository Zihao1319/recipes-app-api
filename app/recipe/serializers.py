"""serializer for recipe api"""

from rest_framework import serializers
from core.models import (Recipe, Tag, Ingredient)

class IngredientSerializer(serializers.ModelSerializer):
    """serializer for ingredient"""

    class Meta:
        model = Ingredient
        fields = ["id", "name"]
        read_only_fields = ["id"]

class TagSerializer(serializers.ModelSerializer):
    """serializer for tag"""

    class Meta:
        model = Tag
        fields=["id", "name"]
        read_only_fields=["id"]

#for my own implementation
# class RecipeImageSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = RecipeImage
#         fields = ["id", "recipe", "image"]
#         read_only_fields=["id"]
#         extra_kwargs = {"image" : {"required": "True"}}


class RecipeSerializer(serializers.ModelSerializer):

    tags = TagSerializer(many=True, required=False)
    ingredients = IngredientSerializer(many=True, required = False)
    # images = RecipeImageSerializer(many=True, required = False)

    class Meta:
        model = Recipe
        fields = ["id", "title", "time_minutes", "price", "link", "tags", "ingredients", "image"]
        read_only_fields = ["id"]

    def _get_or_create_tags(self, tags, recipe):
        """handle getting or creating tags as needed"""
        auth_user = self.context["request"].user
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(
                user = auth_user,
                **tag,  #instead of putting name = tag["name"], this code futureproofs users to add in other codes related to tags in future (eg: creation time, etc)
            )
            recipe.tags.add(tag_obj)

    def _get_or_create_ingredients(self, ingredients, recipe):
        """handle gettin or creating ingredients as needed"""
        auth_user = self.context["request"].user
        for i in ingredients:
            ingredient_obj, created = Ingredient.objects.get_or_create(
                user=auth_user,
                **i,
            )
            recipe.ingredients.add(ingredient_obj)

    def create(self, validated_data):
        """create a recipe"""
        #remove the tags in the validated__data if any, and assign it to tags, if not, put a [] inside
        tags = validated_data.pop("tags", [])
        ingredients = validated_data.pop("ingredients", [])
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags, recipe)
        self._get_or_create_ingredients(ingredients, recipe)

        return recipe

    def update(self, instance, validated_data):
        """update recipe"""
        tags = validated_data.pop("tags", None)
        ingredients = validated_data.pop("ingredients", None)

        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags, instance)

        if ingredients is not None:
            instance.ingredients.clear()
            self._get_or_create_ingredients(ingredients, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class RecipeDetailSerializer(RecipeSerializer):
    """serializer for recipe detail view"""

    class Meta (RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ["description"]

#we are creating a separate serializer just for image upload from recipe because we only
#want to use a serialzier for a particular data type
class RecipeImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ["id", "image"]
        read_only_fields=["id"]
        extra_kwargs = {"image" : {"required": "True"}}


