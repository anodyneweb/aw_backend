from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views

from anodyne import views, settings
from anodyne.public_api import views as public_views
from anodyne.views import logoutview

urlpatterns = [
                  # views with context
                  url(r'^$', views.LoginView.as_view(), name='login'),
                  url(r'^login/$', views.LoginView.as_view(), name='login'),
                  # path('login', views.LoginView.as_view(), name='login'),
                  url(r'^auth/$', views.auth_and_login, name='authenticate'),
                  url(r'^logout/$', logoutview, name='logout'),
                  url(r'^signup/$', public_views.SignUpView.as_view(),
                       name='signup'),

                  path('hello', views.HelloView.as_view(), name='hello'),
                  path('admin/', admin.site.urls),
                  path('api/token/', jwt_views.TokenObtainPairView.as_view(),
                       name='token_obtain_pair'),
                  path('api/token/refresh/',
                       jwt_views.TokenRefreshView.as_view(),
                       name='token_refresh'),


                  url(r'^api/', include('api.urls', namespace='api')),
                  url(r'^dashboard/', include('dashboard.urls', namespace='dashboard')),



              ] + static(settings.STATIC_URL,
                         document_root=settings.STATIC_ROOT)
