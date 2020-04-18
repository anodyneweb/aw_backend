from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views

from anodyne import views, settings
from anodyne.public_api import views as public_views

urlpatterns = [
                  # views with context
                  path('', views.LoginView.as_view(), name='login'),
                  path('hello', views.HelloView.as_view(), name='hello'),
                  path('auth', views.AuthenticateView.as_view(), name='authenticate'),
                  path('admin/', admin.site.urls),

                  path('api/token/', jwt_views.TokenObtainPairView.as_view(),
                       name='token_obtain_pair'),
                  path('api/token/refresh/',
                       jwt_views.TokenRefreshView.as_view(),
                       name='token_refresh'),
                  # including API app urls.py, serializer responses

                  path('signup/', public_views.SignUpView.as_view(),
                       name='signup'),
                  path('api/', include('api.urls', namespace='api')),
                  path('dashboard/', include('dashboard.urls', namespace='dashboard')),



              ] + static(settings.STATIC_URL,
                         document_root=settings.STATIC_ROOT)
