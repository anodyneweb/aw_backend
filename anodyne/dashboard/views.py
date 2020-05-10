import json
import random
from datetime import datetime, timedelta

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db.models import F, Value, CharField
from django.db.models.functions import Concat
from django.http import Http404, HttpResponse, JsonResponse, \
    HttpResponseBadRequest
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from markupsafe import Markup
from plotly.offline import plot
import numpy as np
from anodyne.connectors import connector
from anodyne.settings import DATE_FMT
from anodyne.views import get_rgb
from api.GLOBAL import UNIT
from api.models import Station, Industry, User, Parameter, StationParameter, \
    Reading
from dashboard.forms import StationForm, IndustryForm, UserForm, ParameterForm

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


def get_error(err):
    err = json.loads(err.as_json())
    message = []
    for field, msg in err.items():

        if msg:
            msg = msg[0].get('message', 'code')
        else:
            msg = 'incorrect input'
        message.append('%s: %s' % (field, msg))
    return message

def yes_no(flag):
    if flag:
        return 'Yes'
    return 'No'


class AuthorizedView(View):
    template_name = 'login.html'

    """ A class-based view that requires a login. """

    @method_decorator(
        login_required(redirect_field_name='next', login_url='login'))
    def dispatch(self, request, *args, **kwargs):
        return super(AuthorizedView, self).dispatch(request, *args, **kwargs)


def make_clickable(html, **kwargs):
    return html.format(**kwargs)


apply_func = np.vectorize(make_clickable)


class DashboardView(AuthorizedView):

    def get(self, request):
        # # dir_list = os.listdir('z-dust')
        # # print(dir_list)
        # import os
        # for idx, f in enumerate(os.listdir('z-dust')):
        # fname = os.path.join('z-dust', f)
        # start = connector.ReadCSV(fname)
        # start.process()

        info_template = get_template('dashboard.html')
        # MyModel.objects.annotate(renamed_value=F('cryptic_value_name')).values('renamed_value')
        stations = Station.objects.filter().select_related(
            'industry').values(
            'uuid',
            'industry__uuid',
            Station=F('name'),
            Industry=F('industry__name'),
            Status=F('status'),
            Industry_Code=F('industry__industry_code'),
            CPCB=F('is_cpcb'),
            Active=F('active'),
            City=F('city__name'),
            Address=F('address'),
            Added_On=F('created__date'),
            Camera = F('camera'),
        )
        df = pd.DataFrame(stations)
        # BUG: can't format here have to concatenate only
        # generating hyperlinks

        station_href = "<a href='/dashboard/station-info/{uuid}'>{station}</a>"
        industry_href = "<a href='/dashboard/industry-info/{uuid}'>{industry}</a>"
        df['Station'] = apply_func(station_href, uuid=df['uuid'],
                                   station=df['Station'])
        df['Industry'] = apply_func(industry_href, uuid=df['industry__uuid'],
                                    industry=df['Industry'])
        df['Added_On'] = df['Added_On'].dt.strftime('%d-%B-%Y')

        df = df.drop(columns=['uuid', 'industry__uuid'])
        details = {
            'total': df.shape[0],
            'live': df[df['Status'] == 'Live'].shape[0],
            'delay': df[df['Status'] == 'Delay'].shape[0],
            'offline': df[df['Status'] == 'Offline'].shape[0],

        }
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center', escape=False),
            'details': details
        }
        html = info_template.render(content, request)
        return HttpResponse(html)


class StationView(AuthorizedView):

    def get(self, request, uuid=None):
        if uuid:
            return self._get_station(request, uuid)

        stations = Station.objects.all().values(
            'uuid',
            'industry__uuid',
            Name=F('name'),
            Industry=F('industry__name'),
            Ganga=F('ganga'),
            # City=F('city__name'),


            # Address=F('address'),
        )
        df = pd.DataFrame(stations)
        station_href = "<a href='/dashboard/station-info/{uuid}'>{station}</a>"
        industry_href = "<a href='/dashboard/industry-info/{uuid}'>{industry}</a>"
        df['Name'] = apply_func(station_href, uuid=df['uuid'],
                                station=df['Name'])
        df['Industry'] = apply_func(industry_href, uuid=df['industry__uuid'],
                                    industry=df['Industry'])
        apply_yes_no = np.vectorize(yes_no)
        df['Ganga'] = apply_yes_no(df['Ganga'])
        df = df.drop(columns=['uuid', 'industry__uuid'])
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center', escape=False),
            'form': StationForm()
        }
        info_template = get_template('station.html')
        # TODO: this render guy takes time
        html = info_template.render(content, request)
        return HttpResponse(html)

    def post(self, request, uuid=None):
        if uuid:
            return self._update_station(request, uuid)

        form = StationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Added Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')
        return redirect(reverse('dashboard:stations'))

    def _get_object(self, uuid):
        try:
            return Station.objects.get(pk=uuid)
        except Station.DoesNotExist:
            raise Http404

    def _get_station(self, request, uuid):
        station = self._get_object(uuid)

        station_row = [dict(Industry=station.industry.name,
                            Name=station.name,
                            City=station.city,
                            PCB=station.pcb,
                            Ganga=station.ganga,
                            Address=station.address,
                            Parameters=','.join(station.parameters)
                            )
                       ]
        df = pd.DataFrame(station_row)
        content = {
            'station': station,
            'form': StationForm(instance=station),
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center'),
        }
        graph_details = render_chart2(site=station)
        content.update(**graph_details)
        # content.update(**render_chart2(request, site=station))
        info_template = get_template('station-info.html')
        # TODO: this render guy takes time
        html = info_template.render(content, request)
        return HttpResponse(html)

    def _update_station(self, request, uuid):
        station = self._get_object(uuid)
        form = StationForm(request.POST, instance=station)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')

        url = reverse('dashboard:station-info', kwargs={'uuid': uuid})
        return redirect(url)

    def delete(self, request, uuid, format=None):
        if request.user.is_admin:
            station = self._get_object(uuid)
            station.delete()
            message = 'Successfully Deleted'
            messages.success(request, message, extra_tags="success")
        else:
            message = 'Only Admin Can Delete'
            messages.info(request, message, extra_tags="warning")
        return HttpResponse(request, message)


class IndustryView(AuthorizedView):
    def _get_object(self, uuid):
        try:
            return Industry.objects.get(uuid=uuid)
        except Industry.DoesNotExist:
            raise Http404

    def _get_industry(self, request, uuid):
        content = {}
        industry = self._get_object(uuid)
        stations = industry.station_set.all()
        stations = stations.values('uuid',
                                   'industry__uuid',
                                   Name=F('name'),
                                   Status=F('status'),
                                   PCB=F('pcb'),
                                   # Ganga=F('ganga'),
                                   City=F('city__name'),
                                   Address=F('address'),
                                   )
        if stations:
            df_station = pd.DataFrame(stations)
            station_href = "<a href='/dashboard/station-info/{uuid}'>{station}</a>"
            df_station['Name'] = apply_func(station_href,
                                            uuid=df_station['uuid'],
                                            station=df_station['Name'])
            df_station = df_station.drop(columns=['uuid', 'industry__uuid'])
            content.update({
                'tabular_stations': df_station.to_html(
                    classes="table table-bordered",
                    table_id="dataTable", index=False,
                    justify='center', escape=False),
            })
        industry_row = [dict(
            Name=industry.name,
            Industry_Code=industry.industry_id,
            Status=industry.status,
            Category=industry.type,
            City=industry.city,
            Address=industry.address,
            Ganga=industry.ganga
        )]
        df = pd.DataFrame(industry_row)
        apply_yes_no = np.vectorize(yes_no)
        df['Ganga'] = apply_yes_no(df['Ganga'])
        content.update({
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center'),

            'industry': industry,
            'form': IndustryForm(instance=industry),
            'stationform': StationForm()
        })
        info_template = get_template('industry-info.html')
        html = info_template.render(content, request)
        return HttpResponse(html)

    def get(self, request, uuid=None):
        if uuid:
            return self._get_industry(request, uuid)

        industries = Industry.objects.all().values(
            'uuid',
            Name=F('name'),
            Status=F('status'),
            Category=F('type'),
            State=F('state'),
            Address=F('address')
        )

        df = pd.DataFrame(industries)
        industry_href = "<a href='/dashboard/industry-info/{uuid}'>{industry}</a>"
        df['Name'] = apply_func(industry_href, uuid=df['uuid'],
                                industry=df['Name'])
        df = df.drop(columns=['uuid'])
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center', escape=False),
            'form': IndustryForm()
        }

        info_template = get_template('industry.html')
        html = info_template.render(content, request)
        return HttpResponse(html)

    def post(self, request, uuid=None):
        if uuid:
            return self._update_industry(request, uuid)

        form = IndustryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.info(request, 'Added Successfully', extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')

        return redirect(reverse('dashboard:industries'))

    def _update_industry(self, request, uuid):
        industry = self._get_object(uuid)
        form = IndustryForm(request.POST, instance=industry)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')

        url = reverse('dashboard:industry-info', kwargs={'uuid': uuid})
        return redirect(url)

    def delete(self, request, uuid, format=None):
        if request.user.is_admin:
            industry = self._get_object(uuid)
            industry.delete()
            message = 'Successfully Deleted'
            messages.success(request, message, extra_tags="success")
        else:
            message = 'Only Admin Can Delete'
            messages.info(request, message, extra_tags="warning")
        return HttpResponse(request, message)


class UserView(AuthorizedView):

    def _get_object(self, uuid):
        try:
            return User.objects.get(id=uuid)
        except User.DoesNotExist:
            raise Http404

    def _get_user(self, request, uuid):
        user = self._get_object(uuid)

        user_row = [dict(
            Name=user.name,
            Email=user.email,
            Admin=user.admin,
            Active=user.active,
            Last_Login=user.last_login.strftime(DATE_FMT),
            Phone=user.phone or '-',
            City=user.city or '-',
            State=user.state or '-',
            Address=user.address or '-',
            Zipcode=user.zipcode or '-',
        )]
        df = pd.DataFrame(user_row)
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center'),
            'user': user,
            'form': UserForm(instance=user)
        }
        info_template = get_template('user-info.html')
        # TODO: this render guy takes time
        html = info_template.render(content, request)
        return HttpResponse(html)

    def get(self, request, uuid=None):
        if uuid:
            return self._get_user(request, uuid)

        users = User.objects.extra(select={
            'last_login': "YYYY-MM-DD hh:mi AM)"}).values(
            'id',
            Name=F('name'),
            City=F('city__name'),
            Email=F('email'),
            Login=F('last_login')
        )
        df = pd.DataFrame(users)
        user_href = "<a href='/dashboard/user-info/{id}'>{name}</a>"
        df['Name'] = apply_func(user_href, id=df['id'],
                                name=df['Name'])
        df = df.drop(columns=['id'])
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center', escape=False),
            'form': UserForm(),

        }
        info_template = get_template('users.html')
        html = info_template.render(content, request)
        return HttpResponse(html)

    def post(self, request, uuid=None):
        if uuid:
            return self._update_user(request, uuid)
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.info(request, 'Added Successfully', extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')

        return redirect(reverse('dashboard:users'))

    def _update_user(self, request, uuid):
        station = self._get_object(uuid)
        form = UserForm(request.POST, request.FILES, instance=station)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')

        url = reverse('dashboard:user-info', kwargs={'uuid': uuid})
        return redirect(url)

    def delete(self, request, uuid, format=None):
        user = self._get_object(uuid)
        if str(user.email).lower().strip() == str(
                request.user).lower().strip():
            message = 'Cannot delete own account, ask other admin.'
            messages.info(request, message, extra_tags="warning")
        elif not request.user.is_admin and user.is_admin:
            message = 'Only admins can delete an admin(s) account.'
            messages.info(request, message, extra_tags="warning")
        else:
            message = 'Successfully Deleted'
            user.delete()
            messages.success(request, message, extra_tags="success")

        return HttpResponse(request, message)


class ParameterView(AuthorizedView):

    def _get_object(self, pk):
        try:
            return Parameter.objects.get(id=pk)
        except Parameter.DoesNotExist:
            raise Http404

    def _get_parameter(self, request, pk):
        parameter = self._get_object(pk)

        parameter_row = [dict(
            Name=parameter.name,
            Unit=parameter.unit,
            Alias=parameter.alias,
            Color_Code=parameter.color_code,
        )]

        df = pd.DataFrame(parameter_row)
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center'),
            'parameter': parameter,
            'form': ParameterForm(instance=parameter)
        }
        info_template = get_template('parameter-info.html')
        # TODO: this render guy takes time
        html = info_template.render(content, request)
        return HttpResponse(html)

    def get(self, request, pk=None):
        if pk:
            return self._get_parameter(request, pk)

        parameters = Parameter.objects.all().values(
            'id',
            Name=F('name'),
            Unit=F('unit__name'),
            Alias=F('alias'),
            Color=F('color_code')
        )
        df = pd.DataFrame(parameters)
        param_href = "<a href='/dashboard/parameter-info/{id}'>{name}</a>"
        df['Name'] = apply_func(param_href, id=df['id'], name=df['Name'])
        df = df.drop(columns=['id'])
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center', escape=False),

        }
        info_template = get_template('parameter.html')
        html = info_template.render(content, request)
        return HttpResponse(html)

    def post(self, request, pk=None):
        if pk:
            return self._update_parameter(request, pk)

        form = ParameterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')

        return redirect(reverse('dashboard:users'))

    def _update_parameter(self, request, pk):
        parameter = self._get_object(pk)
        form = ParameterForm(request.POST, instance=parameter)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')

        url = reverse('dashboard:parameter-info', kwargs={'slug': pk})
        return redirect(url)

    def delete(self, request, pk, format=None):
        if request.user.is_admin:
            parameter = self._get_object(id)
            parameter.delete()
            message = 'Successfully Deleted'
            messages.success(request, message, extra_tags="success")
        else:
            message = 'Only Admin Can Delete'
            messages.info(request, message, extra_tags="warning")
        return HttpResponse(request, message)


class CameraView(AuthorizedView):

    def get(self, request):
        # records = Industry.objects.filter(station__camera__isnull=False).values(
        records = Industry.objects.all().values(
            'name', 'station__name', 'station__camera')
        df = pd.DataFrame(list(records))
        df['site_n_cam'] = list(zip(df.station__name, df.station__camera))
        data_dict = df.groupby('name').site_n_cam.apply(list).to_dict()
        context = dict(industries=data_dict)
        info_template = get_template('camera.html')
        html = info_template.render(context, request)
        return HttpResponse(html)


class GeographicalView(AuthorizedView):

    def get(self, request):
        # Setup detailed view for each site
        industries = Industry.objects.all().select_related()
        industries_info = industries.values('name', 'type', 'uuid',
                                            'industry_code', 'status',
                                            'city', 'state'
                                            )
        context = dict(industries=industries)
        tmplt = '<div class="card bg-primary shadow">' \
                '<div class="card-body">  ' \
                '<h3 class="text-white">{name}&nbsp;<sup>({type})</sup> ' \
                '</h3><hr style="border-top: 1px solid black;">' \
                ' <h4>{industry_code}&nbsp; | {status}</h4> ' \
                '<h5>{state}</h5></div> ' \
                '</div><a target="_blank" href="/dashboard/industry/{uuid}/site/{uuid}">More info...</a>'
        tmplt = """ %s """ % tmplt
        details = {
            industry.get('uuid'): tmplt.format(**industry) for industry in
            industries_info
        }
        context.update({
            'details': details
        })
        info_template = get_template('geographical.html')
        html = info_template.render(context, request)
        return HttpResponse(html)


class ManagementView(AuthorizedView):

    def get(self, request):
        context = {}
        info_template = get_template('management.html')
        html = info_template.render(context, request)
        return HttpResponse(html)


class ReportView(AuthorizedView):
    def get(self, request, from_date=None, to_date=None):

        q = {
            'Category': F('industry__type'),
            'Industry Code': F('industry__industry_code'),
            'Name of Industry': F('industry__name'),
            'Name of Station': F('name'),
            'Address': F('industry__address'),
            'State': F('industry__state__name'),
            'Status': F('industry__status'),
            'In Ganga Indusrty': F('industry__ganga'),
        }
        if from_date and to_date:
            from_date = datetime.strptime(from_date, "%m/%d/%Y")
            to_date = datetime.strptime(to_date, "%m/%d/%Y")
        else:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=100)
        reading_q = {
            'reading__timestamp__gte': from_date,
            'reading__timestamp__lte': to_date,
        }

        stations = Reading.objects.filter(**reading_q).values_list('station__prefix',
                                                       flat=True).distinct('station')

        stations = Station.objects.filter(prefix__in=stations).select_related('industry').values(
            **q)
        df = pd.DataFrame(stations)
        # BUG: can't format here have to concatenate only
        # generating hyperlinks
        context = {
            'csv_name': from_date.strftime('%B_%Y'),
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='center', escape=False),
        }
        info_template = get_template('reports.html')
        html = info_template.render(context, request)
        return HttpResponse(html)


def industry_sites(request):
    i_uuid = request.GET.get('industry') or None
    if i_uuid:
        sites = Station.objects.filter(industry__uuid=i_uuid).values('uuid',
                                                                     'name')
        return JsonResponse(dict(sites=list(sites)))
    return JsonResponse(dict(details=list()))


def site_details(request=None, pk=None):
    """
    This will be used at many places show as much info as possible
    :param request:
    :return:
    """
    details = dict()
    if pk:
        s_uuid = pk
    else:
        s_uuid = request.GET.get('site') or None
    if s_uuid:
        site = Station.objects.filter(pk=s_uuid).values(
            **{
                'Uuid': F('uuid'),
                'Name': F('name'),
                'Pcb': F('pcb'),
                'Created': F('created'),
                'Longitude': F('longitude'),
                'Latitude': F('latitude'),
                'State_City': Concat(F('state'), Value(': '),
                                     F('city__name'),
                                     output_field=CharField()),
                'Status': F('status'),
                'Industry': F('industry__name'),
                'Industry_code': F('industry__industry_code'),
                'Category': F('industry__type')
            }
        )
        return JsonResponse(dict(site[0]), safe=False)
    return HttpResponseBadRequest()


def render_chart2(**kwargs):
    import plotly.graph_objects as go
    from api.models import Reading
    site = kwargs.get('site')
    from_date = kwargs.get('from_date')
    to_date = kwargs.get('to_date')
    if not (from_date and to_date):
        to_date = datetime.now()
        try:
            last_seen = Reading.objects.filter(
                station=site).latest('reading__timestamp').reading.get(
                'timestamp')
            last_seen = datetime.strptime(last_seen, '%Y-%m-%d %H:%M:%S')
            from_date = last_seen - timedelta(hours=10)
        except Reading.DoesNotExist:
            from_date = datetime.now() - timedelta(days=13, hours=10)
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
        # 'last_seen': site,
        # 'cam_url': site.cam_url,
        'from': from_date.strftime(DATE_FMT),
        'to': to_date.strftime(DATE_FMT),
    }
    q = {
        'reading__timestamp__gte': from_date,
        'reading__timestamp__lte': to_date,
    }
    readings = Reading.objects.filter(
        station=site, **q).values_list(
        'reading', flat=True).order_by('-reading__timestamp')
    # Join both database
    df = pd.DataFrame(readings)
    df = df.fillna(0)
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
                                                 ).prefetch_related(
        'parameter')
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
            trace = dict(type='scatter', mode='markers+lines',
                         x=list(df.timestamp),
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
        'layout': js_layout
    }
    return context


def generate_html_cards(details):
    html_tx = ''
    for param, meta in details.items():
        param_meta = dict(param=param.upper(),
                          unit=meta.get('unit'),
                          color=meta.get('color', 'orange'),
                          min=meta.get('min'),
                          max=meta.get('max'),
                          avg=meta.get('avg'),
                          last_received=meta.get('last_received'),
                          last_value=str(meta.get('last_value'))[:5])
        rec = """
        <div class="col-lg-3 mb-3 small-size-card">
        <div class="card bg-info text-white shadow">
            <div class="card-body">
                <div class="head">
                    <b>{param}</b>
                    <b class="fa-pull-right">{unit}</b>
                    <br>
                </div>
                <hr style="border-top: 3px solid {color};">
                <div class="col-12 col-xs-12">
                    <div><h3><strong>Last Received:</strong></h3></div>
                    <div><h3 style="font-size: 20px; color:black">{last_value}
                    <a style="font-size: 18px;"> {unit}</a></h3></div>
                    <div><h3 style="font-size: 17px;">{last_received}</h3></div>
                </div>
            </div>
        </div>
    </div>
        """.format(**param_meta)
        html_tx += '\n%s' % rec
    return html_tx


@login_required
def plot_chart(request):
    uuid = request.GET.get('site')
    site = Station.objects.get(uuid=uuid)
    kwargs = {
        'from_date': request.GET.get('from_date'),
        'to_date': request.GET.get('to_date'),
        'site': site
    }
    context = render_chart2(**kwargs)
    return JsonResponse(context)
