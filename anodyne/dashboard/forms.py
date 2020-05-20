from crispy_forms.helper import FormHelper
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms import ModelForm
from django.urls import reverse

from api.models import Station, Industry, User, Parameter, State, City, \
    StationParameter

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
    password = forms.CharField(min_length=6, max_length=16,
                               widget=forms.PasswordInput(), required=False)
    confirm_password = forms.CharField(min_length=6, max_length=16,
                                       widget=forms.PasswordInput(),
                                       required=False)
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
