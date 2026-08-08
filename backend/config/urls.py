from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root(request):
    return JsonResponse(
        {
            "message": "Enterprise Knowledge RAG API",
            "admin": "/admin/",
            "auth": "/api/auth/",
            "chats": "/api/chats/",
            "categories": "/api/categories/",
            "documents": "/api/documents/",
        }
    )


urlpatterns = [
    path("", api_root, name="api-root"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/chats/", include("chats.urls")),
    path("api/", include("documents.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
