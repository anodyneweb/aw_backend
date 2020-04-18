from crispy_forms.helper import FormHelper
from django import forms
from django.forms import ModelForm
from django.urls import reverse

from api.models import Station, Industry

ATTRS = {'class': 'textinput textInput form-control'}


class StationForm(ModelForm):
    """
    This is related to Staff users only
    """

    class Meta:
        model = Station
        fields = '__all__'
        exclude = ('uuid', 'created', 'country', 'realtime_url',
                   'delayed_url', 'version')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 1}),
            'key': forms.Textarea(attrs={'rows': 1}),
            'pub_key': forms.Textarea(attrs={'rows': 1}),
            'pvt_key': forms.Textarea(attrs={'rows': 1}),
            'user_email': forms.Textarea(attrs={'rows': 1}),
            'user_ph': forms.Textarea(attrs={'rows': 1}),
            'cpcb_email': forms.Textarea(attrs={'rows': 1}),
            'cpcb_ph': forms.Textarea(attrs={'rows': 1}),

        }


class IndustryForm(ModelForm):
    """
    This is related to Staff users only
    """

    class Meta:
        model = Industry
        fields = '__all__'
        exclude = ('uuid',)
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3})
        }
