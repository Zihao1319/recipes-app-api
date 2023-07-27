"""url mappings for the recipe app"""

from django.urls import (
    path, include
)

from rest_framework.routers import DefaultRouter
from recipe import views

router = DefaultRouter()
# so all the endpoints will become api/recipe/recipes/Xx
router.register("recipes", views.RecipeViewSet)
router.register("ingredients", views.IngredientViewSet)
router.register("tags", views.TagViewSet)

#for reverse look up in testings
app_name = "recipe"

urlpatterns = [
    path("", include(router.urls))
]