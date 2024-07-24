"""
URL configuration for coral_credits project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from rest_framework_nested import routers

from coral_credits.api import views

router = routers.DefaultRouter()
router.register(r"resource_class", views.ResourceClassViewSet)
router.register(r"resource_provider", views.ResourceProviderViewSet)
router.register(r"resource_provider_account", views.ResourceProviderAccountViewSet)
router.register(r"allocation", views.CreditAllocationViewSet)
router.register(r"account", views.AccountViewSet, basename="creditaccount")
router.register(r"consumer", views.ConsumerViewSet, basename="resource-request")

allocation_router = routers.NestedSimpleRouter(
    router, r"allocation", lookup="allocation"
)
allocation_router.register(
    r"resources", views.CreditAllocationResourceViewSet, basename="allocation-resource"
)


def status(request):
    # Just return 204 No Content
    return HttpResponse(status=204)


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("_status/", status, name="status"),
    path("", include(router.urls)),
    path("", include(allocation_router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("admin/", admin.site.urls),
]
