from rest_framework.routers import DefaultRouter

from documents.views import ( DocumentCategoryViewSet, DocumentViewSet,)

router = DefaultRouter()

router.register("categories", DocumentCategoryViewSet,basename="document-category",)
router.register("documents", DocumentViewSet, basename="document",)

urlpatterns = router.urls