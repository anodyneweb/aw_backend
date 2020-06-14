from crispy_forms.helper import FormHelper
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.forms import ModelForm
from django.template import loader
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

from api.models import Station, Industry, User, Parameter, State, City, \
    StationParameter, Maintenance, Device, Registration

ATTRS = {'class': 'textinput textInput form-control'}


class StationForm(ModelForm):
    """
    This is related to Staff users only
    """
    state = forms.ModelChoiceField(
        queryset=State.objects.all().order_by('name'),
        to_field_name='name',
        widget=forms.Select(
            attrs={'onchange': "GetCities(this)", })
    )
    city_qst = City.objects.all().select_related('state')
    city = forms.ModelChoiceField(queryset=city_qst, widget=forms.Select(
        attrs={'onchange': "GetLongLat(this)", })
                                  )

    class Meta:
        model = Station
        fields = '__all__'
        exclude = ('uuid', 'created', 'country', 'realtime_url',
                   'delayed_url')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 1}),
            'key': forms.Textarea(attrs={'rows': 1}),
            'pub_key': forms.Textarea(attrs={'rows': 1}),
            'pvt_key': forms.Textarea(attrs={'rows': 1}),
            'user_email': forms.Textarea(attrs={'rows': 1}),
            'user_ph': forms.Textarea(attrs={'rows': 1}),
            'cpcb_email': forms.Textarea(attrs={'rows': 1}),
            'cpcb_ph': forms.Textarea(attrs={'rows': 1}),
            'closure_status': forms.Textarea(attrs={'rows': 1}),
        }


class IndustryForm(ModelForm):
    """
    This is related to Staff users only
    """
    state = forms.ModelChoiceField(
        queryset=State.objects.all().order_by('name'),
        to_field_name='name',
        widget=forms.Select(
            attrs={'onchange': "GetCities(this)", })
    )
    city_qst = City.objects.all().select_related('state')
    city = forms.ModelChoiceField(queryset=city_qst, widget=forms.Select(
        attrs={'onchange': "GetLongLat(this)", })
                                  )

    class Meta:
        model = Industry
        fields = '__all__'
        exclude = ('uuid',)
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3})
        }


class UserForm(ModelForm):
    """
    This is related to Staff users only
    """
    state = forms.ModelChoiceField(
        queryset=State.objects.all().order_by('name'),
        to_field_name='name',
        widget=forms.Select(
            attrs={'onchange': "GetCities(this)", })
    )
    city_qst = City.objects.all().select_related('state')
    city = forms.ModelChoiceField(queryset=city_qst, widget=forms.Select(
        attrs={'onchange': "GetLongLat(this)", })
                                  )

    # station = forms.ModelMultipleChoiceField(required=False,
    #                                       queryset=Station.objects.all(),
    #                                       widget=FilteredSelectMultiple(
    #                                           'Stations', False),
    #                                       label='')
    # class Media:
    #     # for sites
    #     css = {'all': ('admin/css/widgets.css', '/static/css/overrides.css'), }
    #     # Adding this javascript is crucial
    #     js = ['/admin/jsi18n/']

    class Meta:
        model = User
        fields = '__all__'
        exclude = ('id', 'password', 'staff', 'last_login')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
        }


class ParameterForm(ModelForm):
    """
    This is related to Staff users only
    """

    class Meta:
        model = Parameter
        fields = '__all__'


class StationParameterForm(ModelForm):
    """
    This is related to Staff users only
    """

    class Meta:
        model = StationParameter
        fields = '__all__'
        exclude = ('station', 'parameter')


class MaintenanceForm(ModelForm):
    class Meta:
        model = Maintenance
        fields = '__all__'

    start_date = forms.DateField(
        widget=forms.TextInput(
            attrs={'type': 'date'}
        )
    )
    end_date = forms.DateField(
        widget=forms.TextInput(
            attrs={'type': 'date'}
        )
    )
    comments = forms.CharField(
        widget=forms.Textarea(
            attrs={'rows': 2}
        )
    )


class DeviceForm(ModelForm):
    class Meta:
        model = Device
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }


class PasswordResetForm(forms.Form):
    """
    This is a just an update copy of django.contrib.auth.views PasswordResetForm
    """
    email = forms.EmailField(label=_("Email"), max_length=254)

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email,
                  html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email,
                                               [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name,
                                                 context)
            email_message.attach_alternative(html_email, 'text/html')
        email_message.send()

    def get_users(self, email):
        """Given an email, return matching user(s) who should receive a reset.

        This allows subclasses to more easily customize the default policies
        that prevent inactive users and users with unusable passwords from
        resetting their password.
        """
        UserModel = get_user_model()
        active_users = UserModel._default_manager.filter(**{
            '%s__iexact' % UserModel.get_email_field_name(): email,
        })
        # return (u for u in active_users if u.has_usable_password())
        # we are not checking for usable passwords
        return active_users

    def save(self, domain_override=None,
             subject_template_name='registration-links/password_reset_subject.txt',
             email_template_name='registration-links/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """
        Generate a one-use only link for resetting password and send it to the
        user.
        """
        email = self.cleaned_data["email"]
        for user in self.get_users(email):
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            try:
                uid = urlsafe_base64_encode(force_bytes(user.pk)).decode()
            except:
                uid = urlsafe_base64_encode(force_bytes(user.pk)).decode()
            context = {
                'email': email,
                'domain': domain,
                'site_name': site_name,
                'uid': uid,
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
            }
            if extra_email_context is not None:
                context.update(extra_email_context)
            self.send_mail(
                subject_template_name,
                email_template_name, context,
                from_email,
                email,
                html_email_template_name=html_email_template_name,
            )


class RegistrationForm(ModelForm):
    class Meta:
        model = Registration
        fields = '__all__'
        widgets = {
            'query': forms.Textarea(attrs={'rows': 3}),
        }