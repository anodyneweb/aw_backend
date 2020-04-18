import random
from datetime import datetime, timedelta

import pandas as pd
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from markupsafe import Markup
from plotly.offline import plot
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from anodyne.views import get_rgb
from api.GLOBAL import UNIT
from dashboard.forms import StationForm, IndustryForm
from api.models import Station, Industry, User, Parameter, StationParameter
from api.serializers import StationSerializer, IndustrySerializer

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


def make_clickable(key, name):
    return '<a href="/dashboard/station/{}">{}</a>'.format(key, name)


class DashboardView(APIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = [TemplateHTMLRenderer]
    template_name = 'dashboard.html'

    def get(self, request):
        industries = Industry.objects.all().select_related('station').values(
            'name',
            'station__name',
            'station__pcb',
            'industry_code',
            'station__ganga',
            'station__is_cpcb',
            'station__active',
            'station__city__name',
            'address',
            'uuid',
            'station__uuid',
        )
        df = pd.DataFrame(industries)
        # BUG: can't format here have to concatenate only
        # generating hyperlinks
        df['station__name'] = "<a href='/dashboard/stationinfo/" + \
                              df['station__uuid'].astype(str) + "'>" + df[
                                  'station__name'].astype(str) + "</a>"
        df['name'] = "<a href='/dashboard/industryinfo/" + \
                     df['uuid'].astype(str) + "'>" + df['name'].astype(
            str) + "</a>"
        df = df.drop(columns=['uuid', 'station__uuid'])
        # df.to_csv('testme.csv')
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center', escape=False),
        }
        return Response(content)


class StationView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, uuid=None):
        if uuid:
            return self._get_station(request, uuid)

        stations = Station.objects.all().values('industry__name', 'name',
                                                'city__name', 'pcb', 'ganga',
                                                'address')
        df = pd.DataFrame(stations)
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center'),
            'form': StationForm()
        }
        info_template = get_template('station.html')
        # TODO: this render guy takes time
        html = info_template.render(content, request)
        return HttpResponse(html)

    def post(self, request, uuid=None):
        if uuid:
            return self._update_station(request, uuid)

        serializer = StationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            message, status = 'Added Successfully', 'success'
        else:
            message, status = serializer.error_messages, 'danger'
        messages.success(request, message,
                         extra_tags="alert alert-%s" % status)
        return redirect(reverse('dashboard:stations'))

    def _get_object(self, uuid):
        try:
            return Station.objects.get(uuid=uuid)
        except Station.DoesNotExist:
            raise Http404

    def _get_station(self, request, uuid):
        station = self._get_object(uuid)
        content = {
            'station': station,
            'form': StationForm(instance=station)
        }
        content.update(**render_chart2(request, site=station))
        info_template = get_template('station-info.html')
        # TODO: this render guy takes time
        html = info_template.render(content, request)
        return HttpResponse(html)

    def _update_station(self, request, uuid):
        station = self._get_object(uuid)
        form = StationForm(request.POST, request.FILES, instance=station)
        if form.is_valid():
            form.save()
            message = 'Successfully Updated'
            status = 'success'
        else:
            message = 'Failed to update due to %s' % form.errors
            status = 'danger'
        print(message)
        messages.warning(request, message,
                         extra_tags="alert alert-%s" % status)
        url = reverse('dashboard:station-info', kwargs={'uuid': uuid})
        return redirect(url)

    def delete(self, request, uuid, format=None):
        station = self._get_object(uuid)
        station.delete()
        message = 'Successfully Deleted'
        messages.success(request, message,
                         extra_tags="alert alert-danger")
        url = reverse('stations')
        return redirect(url)


class IndustryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, uuid=None):
        if uuid:
            return self._get_industry(request, uuid)

        industries = Industry.objects.all().values('name', 'status', 'type',
                                                   'state',
                                                   'address')
        df = pd.DataFrame(industries)
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center'),
            'form': IndustryForm()
        }

        info_template = get_template('industry.html')
        html = info_template.render(content, request)
        return HttpResponse(html)

    def post(self, request, uuid=None):
        if uuid:
            return self._update_industry(request, uuid)

        serializer = IndustrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            message, status = 'Added Successfully', 'success'
        else:
            message, status = serializer.error_messages, 'danger'
        messages.success(request, message,
                         extra_tags="alert alert-%s" % status)
        return redirect(reverse('dashboard:industries'))

    def _get_object(self, uuid):
        try:
            return Industry.objects.get(uuid=uuid)
        except Industry.DoesNotExist:
            raise Http404

    def _get_industry(self, request, uuid):
        industry = self._get_object(uuid)
        content = {
            'industry': industry,
            'form': Industry(instance=industry)
        }
        info_template = get_template('industry-info.html')
        # TODO: this render guy takes time
        html = info_template.render(content, request)
        return HttpResponse(html)

    def _update_industry(self, request, uuid):
        station = self._get_object(uuid)
        form = IndustryForm(request.POST, request.FILES, instance=station)
        if form.is_valid():
            form.save()
            message = 'Successfully Updated'
            status = 'success'
        else:
            message = 'Failed to update due to %s' % form.errors
            status = 'danger'
        messages.warning(request, message,
                         extra_tags="alert alert-%s" % status)
        url = reverse('dashboard:industry-info', kwargs={'uuid': uuid})
        return redirect(url)

    def delete(self, request, uuid, format=None):
        industry = self._get_object(uuid)
        industry.delete()
        message = 'Successfully Deleted'
        messages.success(request, message,
                         extra_tags="alert alert-danger")
        url = reverse('industries')
        return redirect(url)


class UserView(APIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = [TemplateHTMLRenderer]
    template_name = 'users.html'

    def get(self, request):
        stations = User.objects.all().values('name', 'city__name', 'email',
                                             'last_login'
                                             )
        df = pd.DataFrame(stations)
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center')
        }

        return Response(content)


class ParameterView(APIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = [TemplateHTMLRenderer]
    template_name = 'parameter.html'

    def get(self, request):
        stations = Parameter.objects.all().values('name', 'unit__name',
                                                  'alias',
                                                  'color_code')
        df = pd.DataFrame(stations)
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center'),

        }

        return Response(content)


def render_chart2(request, **kwargs):
    import plotly.graph_objects as go
    from api.models import Reading
    site = kwargs.get('site')
    from_date = kwargs.get('from_date')
    to_date = kwargs.get('to_date')
    if not (from_date and to_date):
        from_date = datetime.now() - timedelta(days=13, hours=10)
        to_date = datetime.now()
    else:
        from_date = datetime.strptime(from_date, "%m/%d/%Y %H:%M %p")
        to_date = datetime.strptime(to_date, "%m/%d/%Y %H:%M %p")

    # status = site.site_status
    # if status.lower() == 'live':
    status = 'success', 'Live'
    # elif status.lower() == 'delay':
    #     status = 'warning', 'Delay',
    # else:
    #     status = 'danger', 'Offline'
    details = {
        'uuid': site.uuid,
        'name': site.name.replace('_', ' ').title(),
        'status': status,
        'industry': site.industry.name.replace('_', ' ').title(),
        'industry_type': site.industry.type,
        'industry_uuid': site.industry.uuid,
        'industry_status': site.industry.status,
        # 'last_seen': site,
        # 'cam_url': site.cam_url,
        'from': from_date.strftime("%m/%d/%Y %H:%M %p"),
        'to': to_date.strftime("%m/%d/%Y %H:%M %p"),
    }
    archival_date = datetime(2020, 4, 7)  # 07/03/2020 till archived
    q = {
        'reading__timestamp__gte': from_date,
        'reading__timestamp__lte': to_date,
    }
    # stations = Reading.objects.all().distinct('station')
    # print(stations)
    readings = Reading.objects.filter(station__name='stations_0MSO', **q).values_list('reading', flat=True)
    # Join both database
    df = pd.DataFrame(readings)
    df = df.fillna(0)
    print(df.head())
    xaxis = dict(showgrid=True, title_text='Time', linecolor='grey')
    yaxis = dict(showgrid=True, title_text='Param Value', linecolor='grey')
    layout = dict(autosize=True,
                  paper_bgcolor='white', plot_bgcolor='white',
                  xaxis=xaxis, yaxis=yaxis, title=site.name,
                  title_x=0.5,
                  xaxis_showgrid=True,
                  yaxis_showgrid=True
                  )

    obj_layout = go.Figure(layout=layout)
    js_layout = layout
    cards = {}
    # threshld_shapes = []
    param_meta = StationParameter.objects.filter(station=site,
                                                 # allowed=True,
                                                 parameter__name__in=list(
                                                     df.columns),
                                                 ).prefetch_related('parameter')
    print(param_meta)
    parameters = {}
    for s in param_meta:
        parameters[s.parameter.name] = {
            'unit': s.parameter.unit,
            'color': s.parameter.color_code,
            # 'alias': s.parameter_name.alias,
            'max_allowed': s.maximum,
            'min_allowed': s.minimum,
        }
    traces = []  # parameter lines
    for param in list(df.columns):
        # param should be in parameters list else its blocked
        if param != 'timestamp':
            # clr = parameters.get(param).get('color') or utils2.get_rgb()
            clr = get_rgb()
            # unit = parameters.get(param).get('unit', '')
            unit = random.choice(UNIT)[0]
            # Clean values

            df[param] = df[param].apply(lambda x: 0 if x in ['', ' '] else x)
            df[param] = df[param].astype(float)
            cards[param] = {
                'color': clr,
                'unit': unit,
                'min': "{:.2f}".format(df[param].min()),
                'max': "{:.2f}".format(df[param].max()),
                'avg': "{:.2f}".format(df[param].mean()),
                'last_received': df.timestamp.iloc[-1],
                'last_value': df[param].iloc[-1]
            }
            trace = dict(type='scatter', mode='lines', x=list(df.timestamp),
                         y=list(df[param]), name=param.upper(),
                         text=list(df[param]),
                         textposition='bottom center', line_color=clr,
                         opacity=0.8,
                         textfont=dict(family='sans serif',
                                       size=15, color=clr)
                         )
            traces.append(trace)
            obj_layout.add_trace(trace)
    # threshold scenario
    # if threshold:
    #     obj_layout.update_layout(shapes=threshld_shapes)
    #     js_layout.update(dict(shapes=threshld_shapes))
    plot_div = Markup(plot(obj_layout, output_type='div'))

    # format for tabular view
    if not df.empty:
        # sorting latest first
        df.sort_values(by='timestamp', ascending=False, inplace=True)
        df.columns = [a.upper() for a in list(df.columns.values)]
        df.set_index('timestamp'.upper(), inplace=True)
    else:
        layout.update(
            {
                "layout": {
                    "xaxis": {
                        "visible": False
                    },
                    "yaxis": {
                        "visible": False
                    },
                }
            }
        )
    tabl = df.to_html(classes='table_scroll')
    # cards = generate_html_cards(cards)
    context = {
        'chart': plot_div,
        'details': details,
        'data': traces,
        'tabular': tabl,
        # 'cards': cards,
        # 'layout': js_layout
    }
    return context
