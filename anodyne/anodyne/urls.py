from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views

from anodyne import views, settings
from anodyne.public_api import views as public_views
from anodyne.views import logoutview
from api import utils

urlpatterns = [
                  # views with context
                  url(r'^$', views.LoginView.as_view(), name='login'),
                  url(r'^login/$', views.LoginView.as_view(), name='login'),
                  url(r'^auth/$', views.auth_and_login, name='authenticate'),
                  url(r'^logout/$', logoutview, name='logout'),
                  url(r'^signup/$', public_views.SignUpView.as_view(),
                       name='signup'),
                  url(r'^forgot-password/$', public_views.ForgotPasswrodView.as_view(),
                       name='forgot-password'),
                  url(r'^submit-query/$', public_views.SubmitQueryView.as_view(),
                       name='submit-query'),

                  url(r'^account/password-reset$', utils.reset_password,
                      name='reset-password'),
                  url(
                      r'^account/password-reset/(?P<token>[A-Za-z0-9-]+)/(?P<uidb64>[0-9A-Za-z_\-]+)/$',
                      utils.reset_confirm, name='password_reset_confirm'),

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
