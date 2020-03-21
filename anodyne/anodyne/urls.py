from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from rest_framework_simplejwt import views as jwt_views

from anodyne import views

urlpatterns = [
                  # views with context
                  path('hello/', views.HelloView.as_view(), name='hello'),
                  path('admin/', admin.site.urls),
                  path('api/token/', jwt_views.TokenObtainPairView.as_view(),
                       name='token_obtain_pair'),
                  path('api/token/refresh/',
                       jwt_views.TokenRefreshView.as_view(),
                       name='token_refresh'),
                  # including API app urls.py, serializer responses
                  path('api/', include('api.urls')),

              ] + static(settings.STATIC_URL,
                         document_root=settings.STATIC_ROOT)
