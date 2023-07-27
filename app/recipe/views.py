from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)
from django.shortcuts import render
from rest_framework import (
    viewsets,
    mixins,
    status,
)
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import (Recipe, Tag, Ingredient)
from recipe import serializers


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "tags",
                OpenApiTypes.STR,
                description="Comma separated list of IDs to filter",
            ),
            OpenApiParameter(
                "ingredients",
                OpenApiTypes.STR,
                description="Comma separated list of IDs to filter",
            )
        ]
    )
)

# Create your views here.
class RecipeViewSet(viewsets.ModelViewSet):
    """view for managing recipe apis"""
    serializer_class = serializers.RecipeDetailSerializer
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _params_to_ints(self, qs):
        """convert a list of str to int"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """retrieve recipes for authenticated user"""
        tags = self.request.query_params.get("tags")
        ingredients = self.request.query_params.get("ingredients")
        queryset = self.queryset

        if tags:
            tag_ids = self._params_to_ints(tags)
            queryset = queryset.filter(tags__id__in=tag_ids)

        if ingredients:
            ingredient_ids = self._params_to_ints(ingredients)
            queryset = queryset.filter(ingredients__id__in=ingredient_ids)

        return queryset.filter(user=self.request.user).order_by("-id").distinct()

    def get_serializer_class(self):
        """return the serializer class for request"""
        if self.action=="list":
            return serializers.RecipeSerializer

        elif self.action == "upload_image":
            return serializers.RecipeImageSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        """create a new recipe"""
        serializer.save(user=self.request.user)

    #action = allows you to map to specific http method, in this case only post
    #detail = means this is referring to specific detail end point, ie id, isntead of giving a list view if detail = false
    @action(methods=["POST"], detail=True, url_path="upload-image")
    def upload_image(self, request, pk=None):
        """upload an image to a recipe"""
        recipe = self.get_object()
        serializer = self.get_serializer(recipe, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#our API only need list capabilities, because tags and ingredients are added through the recipe endpoint and the tags/ingredients endpoints is only for retrieving a list for the user to select from..
#ModelViewSet provides the full CRUD endpoints, so it's overkill for this endpoint.
#If you look into the code for DRF, the ModelViewSet is actually doing the same thing we are, just with more base classes:
#https://github.com/encode/django-rest-framework/blob/master/rest_framework/viewsets.py#L239

@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "assigned_only",
                OpenApiTypes.INT, enum=[0,1],
                description="Filter by items assigned to recipes",
            ),
        ]
    )
)

#refactoring
class BaseRecipeArrtViewSet(mixins.ListModelMixin,
                mixins.UpdateModelMixin,
                mixins.DestroyModelMixin,
                viewsets.GenericViewSet):

    """base viewset for recipe attributes"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        assigned_only = bool(
            int(self.request.query_params.get("assigned_only", 0))
        )
        queryset = self.queryset

        if assigned_only:
            queryset = queryset.filter(recipe__isnull=False)

        return queryset.filter(user=self.request.user).order_by("-name").distinct()


class TagViewSet(BaseRecipeArrtViewSet):
    """manage tags in db"""
    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()


class IngredientViewSet(BaseRecipeArrtViewSet):
    """manage ingredients in db"""

    serializer_class = serializers.IngredientSerializer
    queryset = Ingredient.objects.all()




