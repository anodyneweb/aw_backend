import json
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Value, CharField, Count
from django.db.models.functions import Concat
from django.http import Http404, HttpResponse, JsonResponse, \
    HttpResponseBadRequest, FileResponse
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from markupsafe import Markup
from pandas import ExcelWriter
from plotly.offline import plot

from anodyne.settings import DATE_FMT, TMP_PATH
from anodyne.views import get_rgb
from api.models import Station, Industry, User, Parameter, StationParameter, \
    Reading, Category, StationInfo, Exceedance, Maintenance, Device
from dashboard.forms import StationForm, IndustryForm, UserForm, ParameterForm, \
    StationParameterForm, MaintenanceForm, DeviceForm

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


def get_status_label(status):
    if status == 'Live':
        label = 'success'
    elif status == 'Delay':
        label = 'warning'
    else:
        label = 'danger'
    tmplt = '<a href="  # " class="btn btn-sm btn-%s">%s</a>' % (label,
                                                                 status)
    return tmplt


class AuthorizedView(View):
    template_name = 'login.html'

    """ A class-based view that requires a login. """

    @method_decorator(
        login_required(redirect_field_name='next', login_url='login'))
    def dispatch(self, request, *args, **kwargs):
        return super(AuthorizedView, self).dispatch(request, *args, **kwargs)


def make_clickable(html, **kwargs):
    to_check = kwargs.get('to_check')
    if to_check:
        if kwargs.get(to_check):
            return html.format(**kwargs)
        else:
            return kwargs.get('else_return')
    return html.format(**kwargs)


apply_func = np.vectorize(make_clickable)


class DashboardView(AuthorizedView):

    def get(self, request):
        info_template = get_template('dashboard.html')
        stations = Station.objects.all()
        stations = stations.select_related(
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
            Camera=F('camera'),
        )
        df = pd.DataFrame(stations)
        # BUG: can't format here have to concatenate only
        # generating hyperlinks

        station_href = "<a href='/dashboard/station-info/{uuid}'>{station}</a>"
        industry_href = "<a href='/dashboard/industry-info/{uuid}'>{industry}</a>"
        cam_templt = '<a href="{cam_url}" class="fa fa-camera fa-success" aria-hidden="true"></a>'
        df['Camera'] = apply_func(cam_templt, cam_url=df['Camera'],
                                  to_check='cam_url', else_return='')
        df['Station'] = apply_func(station_href, uuid=df['uuid'],
                                   station=df['Station'])
        df['Industry'] = apply_func(industry_href, uuid=df['industry__uuid'],
                                    industry=df['Industry'])
        df['Added_On'] = df['Added_On'].dt.strftime('%d-%B-%Y')
        total_industries = len(set(list(df['industry__uuid'])))
        seen_on = []
        for uuid in df['industry__uuid']:
            records = StationInfo.objects.filter(
                station__industry__uuid=uuid).distinct(
                'station__industry').values_list('last_seen', flat=True)
            if records:
                seen_on.append(records[0])
            else:
                seen_on.append(' ')
        df['Last Data Update'] = seen_on
        df = df.drop(columns=['uuid', 'industry__uuid'])

        details = {
            'total_industries': total_industries,
            'total': df.shape[0],
            'live': df[df['Status'] == 'Live'].shape[0],
            'delay': df[df['Status'] == 'Delay'].shape[0],
            'offline': df[df['Status'] == 'Offline'].shape[0],

        }
        apply_status_label = np.vectorize(get_status_label)
        df['Status'] = apply_status_label(df['Status'])
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='left', escape=False),
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
                                  justify='left', escape=False),
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

        }
        content.update(**site_tabular_readings(station=station))
        graph_details = make_chart(site=station)
        content.update(**graph_details)

        parameters = StationParameter.objects.filter(
            station=station).values(
            pid=F('id'),
            Name=F('parameter__name'),
            Minimum=F('minimum'),
            Maximum=F('maximum'),
            Process_name=F('process_name'),
            Monitoring_type=F('monitoring_type'),
            Monitoring_id=F('monitoring_id'),
            Analyser_id=F('analyser_id'),
            Allowed=F('allowed'),
        )

        df = pd.DataFrame(parameters)
        if not df.empty:
            param_href = "<a href='/dashboard/station-parameter-info/{id}'>{name}</a>"
            df['Name'] = apply_func(param_href,
                                    id=df['pid'],
                                    name=df['Name'])

            df = df.drop(columns=['pid'])
            content.update({
                'param_table': df.to_html(classes="table table-bordered",
                                          table_id="dataTable", index=False,
                                          justify='left', escape=False),

            })

        # content.update(**make_chart(request, site=station))
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
            apply_status_label = np.vectorize(get_status_label)
            df_station['Status'] = apply_status_label(df_station['Status'])
            df_station = df_station.drop(columns=['uuid', 'industry__uuid'])
            content.update({
                'tabular_stations': df_station.to_html(
                    classes="table table-bordered",
                    table_id="dataTable", index=False,
                    justify='left', escape=False),
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
        parameters = StationParameter.objects.filter(
            station__industry=industry).distinct('parameter__name')
        last_seen = StationInfo.objects.filter(
            station__industry__uuid=industry.uuid).distinct(
            'station__industry').values_list('last_seen', flat=True)
        if not last_seen:
            last_seen = 'Never'
        else:
            last_seen = last_seen[0].strftime('%d/%m/%Y %H:%M %p')

        if industry.status == 'Live':
            label = 'success'
        elif industry.status == 'Delay':
            label = 'warning'
        else:
            label = 'danger'
        details = {
            'parameters': parameters.count(),
            'last_seen': last_seen,
            'exceedance': 20,
            'stations': len(stations),
            'label': label

        }
        content.update({
            'details': details,

            # 'tabular': df.to_html(classes="table table-bordered",
            #                       table_id="dataTable", index=False,
            #                                       justify='left'),

            'industry': industry,
            'form': IndustryForm(instance=industry),
            'stationform': StationForm()
        })
        info_template = get_template('industry-info.html')
        html = info_template.render(content, request)
        return HttpResponse(html)

    def get(self, request, uuid=None):
        # Sr. No, industry name, industry code, STATUS, industry address, city, state,
        # industry category, PCB, Ganga Basin, Added on date, Last Data Received date.
        context = {}
        if uuid:
            return self._get_industry(request, uuid)
        #
        industries = Industry.objects.all().values(
            **{
                'S No.': F('uuid'),
                'Industry Name': F('name'),
                'Industry Code': F('industry_id'),
                'Address': F('address'),
                'City': F('city__name'),
                'State': F('state'),
                'Category': F('type'),
                # 'PCB': F('pcb'),
                'Status': F('status'),
                'Ganga Basin': F('ganga'),
                'Added On': F('created'),
            }
        )
        df = pd.DataFrame(industries)
        if not df.empty:
            seen_on = []
            for uuid in df['S No.']:
                records = StationInfo.objects.filter(
                    station__industry__uuid=uuid).distinct(
                    'station__industry').values_list('last_seen', flat=True)
                if records:
                    seen_on.append(records[0])
                else:
                    seen_on.append('Never')

            industry_href = "<a href='/dashboard/industry-info/{uuid}'>{industry}</a>"
            df['Industry Name'] = apply_func(industry_href,
                                             uuid=df['S No.'],
                                             industry=df['Industry Name'])
            df['S No.'] = [idx + 1 for idx, _ in enumerate(df['S No.'])]
            df['Added On'] = df['Added On'].dt.strftime('%m-%d-%Y')
            df['Last Data Fetched'] = seen_on
            apply_yes_no = np.vectorize(yes_no)
            df['Ganga Basin'] = apply_yes_no(df['Ganga Basin'])
            df = df[[
                'S No.',
                'Industry Name',
                'Industry Code',
                'Address',
                'City',
                'State',
                'Category',
                # 'PCB'
                'Status',
                'Ganga Basin',
                'Added On',
                'Last Data Fetched'
            ]]
            content = {
                'tabular': df.to_html(classes="table table-bordered",
                                      table_id="dataTable", index=False,
                                      justify='left', escape=False),
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
                                  justify='left'),
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
                                  justify='left', escape=False),
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
                                  justify='left'),
            'parameter': parameter,
            'pk': pk,
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
                                  justify='left', escape=False),

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

        url = reverse('dashboard:parameter-info', kwargs={'pk': pk})
        return redirect(url)

    def delete(self, request, pk, format=None):
        if request.user.is_admin:
            parameter = self._get_object(pk)
            parameter.delete()
            message = 'Successfully Deleted'
            messages.success(request, message, extra_tags="success")
        else:
            message = 'Only Admin Can Delete'
            messages.info(request, message, extra_tags="warning")
        return HttpResponse(request, message)


class StationParameterView(AuthorizedView):

    def _get_object(self, pk):
        try:
            return StationParameter.objects.get(id=pk)
        except Parameter.DoesNotExist:
            raise Http404

    def _get_siteparameter(self, request, pk):
        stationp = self._get_object(pk)
        content = {
            'parameter': stationp,
            'pk': pk,
            'station': stationp.station,
            'form': StationParameterForm(instance=stationp)
        }
        info_template = get_template('station-parameter-info.html')
        # TODO: this render guy takes time
        html = info_template.render(content, request)
        return HttpResponse(html)

    def get(self, request, pk=None):
        if pk:
            return self._get_siteparameter(request, pk)

    def post(self, request, pk):
        if pk:
            return self._update_parameter(request, pk)

    def _update_parameter(self, request, pk):
        parameter = self._get_object(pk)
        form = StationParameterForm(request.POST, instance=parameter)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')

        url = reverse('dashboard:sparameter-info', kwargs={'pk': pk})
        return redirect(url)

    def delete(self, request, pk, format=None):
        if request.user.is_admin:
            parameter = self._get_object(pk)
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


def make_chart(**kwargs):
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
    status = site.status
    if status.lower() == 'live':
        status = 'success', 'Live'
    elif status.lower() == 'delay':
        status = 'warning', 'Delay',
    else:
        status = 'danger', 'Offline'
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
    xaxis = dict(showgrid=True, title_text='Time', linecolor='grey')
    yaxis = dict(showgrid=True, title_text='Param Value', linecolor='grey')
    layout = dict(autosize=True,
                  paper_bgcolor='white',
                  plot_bgcolor='white',
                  xaxis=xaxis,
                  yaxis=yaxis,
                  title=site.name,
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

            parameter = Parameter.objects.get(name__icontains=param)
            clr = parameter.color_code or get_rgb()
            df[param] = df[param].apply(pd.to_numeric, args=('coerce',))
            last_received_df = df[['timestamp', param]]
            last_received_df = last_received_df.dropna(axis=0, how='all',
                                                       thresh=None,
                                                       subset=[param])
            cards[param] = {
                'color': clr,
                'unit': parameter.unit,
                'min': "{:.2f}".format(df[param].min()),
                'max': "{:.2f}".format(df[param].max()),
                'avg': "{:.2f}".format(df[param].mean()),
                "last_received": last_received_df.timestamp.iloc[0],
                "last_value": "{0:.2f}".format(
                    last_received_df[param].iloc[0])
            }
            df[param] = df[param].fillna(0)
            df[param] = df[param].astype(float)
            trace = dict(type='scatter', mode='markers+lines',
                         x=list(df.timestamp),
                         y=list(df[param]),
                         name=param.upper(),
                         text=param,
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
    plot_div = Markup(plot(obj_layout, output_type='div', config={
        'displaylogo': False,
        'modeBarButtonsToRemove': [
            # 'toggleSpikelines',
            # 'hoverCompareCartesian',
            'sendDataToCloud',
            'toImage',
            # 'autoScale2d',
            # 'resetScale2d',
            # 'hoverClosestCartesian',
            # 'hoverCompareCartesian'
        ]
    }))

    # format for tabular view
    if df.empty:
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
    cards = generate_html_cards(cards)
    if kwargs.get('update'):
        context = {
            'layout': js_layout,  # for api req
            'data': traces,  # for api req
            'cards': cards,
        }
    else:
        context = {
            'chart': plot_div,
            'details': details,
            'cards': cards,
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
        <div class="col-sm-3 mb-3 small-size-card">
        <div class="card bg-custom text-white shadow">
            <div class="card-body">
                <div class="head">
                    <b>{param}</b>
                    <b class="fa-pull-right">{unit}</b>
                    <br>
                </div>
                <hr style="border-top: 3px solid {color};">
                <div class="col-12 col-xs-12">
                    <div><b><strong>Last Received:</strong></b></div>
                    <div><h5 style="font-size: 15px; color:black">{last_value}
                    <a style="font-size: 13px;"> {unit}</a></h5></div>
                    <div><h3 style="font-size: 12px;">{last_received}</h3></div>
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
        'site': site,
        'update': True
    }
    context = make_chart(**kwargs)
    return JsonResponse(context)


def plot_table(request):
    uuid = request.GET.get('site')

    station = Station.objects.get(uuid=uuid)
    kwargs = {
        'from_date': request.GET.get('from_date'),
        'to_date': request.GET.get('to_date'),
        'station': station
    }
    context = site_tabular_readings(**kwargs)
    return JsonResponse(context)


def site_tabular_readings(**kwargs):
    site = kwargs.get('station')
    # TODO: this is causing trouble on server
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

    q = {
        'reading__timestamp__gte': from_date,
        'reading__timestamp__lte': to_date,
    }
    # if from_date > archival_date and to_date > archival_date:
    current_readings = Reading.objects.filter(
        station=site, **q).values_list('reading', flat=True)

    readings = list(current_readings)
    if readings:
        df = pd.DataFrame(readings)
        if not df.empty:
            df = df[df['timestamp'].notna()]
            df = df.fillna(0)
            # sorting latest first
            df.sort_values(by='timestamp', ascending=False, inplace=True)
            df.columns = [a.upper() for a in list(df.columns.values)]
            df.set_index('timestamp'.upper(), inplace=True)
            df = df.loc[~df.index.duplicated(keep='first')]
        tabl = df.to_html(
            classes="table table-bordered",
            justify='left'
        )
    else:
        tabl = '<h3> No Records found from: %s to %s</h3><br>' \
               'Please change date range' % (from_date, to_date)
    context = {
        'tabular': tabl,
    }
    return context


class StationDataReportView(AuthorizedView):
    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        freq = kwargs.get('freq')
        from_date = kwargs.get('from_date')
        to_date = kwargs.get('to_date')
        dwld = kwargs.get('dwld')

        stations = request.user.assigned_stations.order_by(
            'name').values(**{
            "uid": F('uuid'),
            "sname": Concat(F('name'), Value(': '),
                            F('industry__name'),
                            output_field=CharField())

        })

        df = pd.DataFrame(stations)
        station_options = list(zip(df.uid, df.sname))
        # we will give time frame for month wise and all
        categories = Category.objects.all().values_list('name', flat=True)
        context = {
            'station_options': station_options,
        }
        if not (from_date and to_date):  # '%d/%m/%Y'
            from_date = datetime.now() - timedelta(days=90)
            to_date = datetime.now()
        else:
            from_date = datetime.strptime(from_date, "%m/%d/%Y")
            to_date = datetime.strptime(to_date, "%m/%d/%Y")
        if pk:
            station = Station.objects.get(uuid=pk)
            context.update({
                'station_name': station.name,
                'industry_name': station.industry.name,
                'current_station': pk
            })

            q = {
                'reading__timestamp__gte': from_date,
                'reading__timestamp__lte': to_date,
                'station': station,
                'freq': freq,
                'dwld': dwld  # this will come via ajax,
            }
            if dwld:
                report = self.get_station_data(**q)
                fl = open(report, 'rb')
                response = FileResponse(fl,
                                        filename=os.path.basename(report))
                return response
            else:
                context.update(self.get_station_data(**q))

            context.update({
                'from_date': from_date.date(),
                'to_date': to_date.date(),
                # 'tabular': tabular,
                'station_name': station.name,
                'industry_name': station.industry.name,
                'industry_type': station.industry.type,
                'current_station': pk,
                'current_freq': freq,
            })
        else:
            context.update({
                'current_station': station_options[0][0],
                'from_date': from_date.date(),
                'to_date': to_date.date(),
                'current_freq': freq,
            })

        info_template = get_template('station-data-report.html')
        html = info_template.render(context, request)
        return HttpResponse(html)

    def get_station_data(self, **q):
        freq = q.pop('freq')
        station = q.pop('station')
        dwld = q.pop('dwld')
        from_date = q.get('reading__timestamp__gte')
        to_date = q.get('reading__timestamp__lte')
        current_readings = Reading.objects.filter(station=station,
                                                  **q).values_list('reading',
                                                                   flat=True)
        readings = list(current_readings)
        rdate = datetime.now().strftime('%d_%m_%Y')
        fname = '%s_%s.xlsx' % (str(station.name).replace(' ', '_'), rdate)
        df = pd.DataFrame(readings)
        if not df.empty:
            columns = list(df.columns)
            df.rename(columns={col: col.upper() for col in columns},
                      inplace=True)

            df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])
            cols = df.columns.drop('TIMESTAMP')
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
            if freq == 'monthly':
                df = df.resample('M', on='TIMESTAMP').mean()
            elif freq == 'weekly':
                df = df.resample('7D', on='TIMESTAMP').mean()
            elif freq == 'daily':
                df = df.resample('D', on='TIMESTAMP').mean()
            elif freq == 'hourly':
                df = df.resample('h', on='TIMESTAMP').mean()
            elif freq == '15Min':
                df = df.resample('15Min', on='TIMESTAMP').mean()
            elif freq == 'yearly':
                df = df.resample('A', on='TIMESTAMP').mean()
            else:
                df = df.set_index('TIMESTAMP')
            df = df.round(2)
            df = df.dropna(axis=0, how='all', thresh=None,
                           subset=list(df.columns), inplace=False)
            df.sort_values(by='TIMESTAMP', ascending=False, inplace=True)
            columns = list(df.columns)
            new_col = {}
            for param in columns:
                try:
                    p = Parameter.objects.get(name__iexact=param)
                    new_col[param] = '%s (%s)' % (p.name, p.unit)
                except Parameter.DoesNotExist:
                    new_col[param] = param

            df.rename(columns=new_col, inplace=True)

            if dwld:
                fpath = os.path.join(TMP_PATH, fname)
                writer = ExcelWriter(fpath, engine='xlsxwriter',
                                     datetime_format='mm-dd-yyyy hh:mm:ss',
                                     date_format='mm-dd-yyyy')
                df.to_excel(writer)
                writer.save()
                return fpath

            records2html = df.to_html(
                classes="table table-bordered",
                max_rows=50,
                justify='left'
            )
            can_download = True
        else:

            records2html = '<br><h3> No Records in range: %s - %s</h1>' % (
                from_date.date(), to_date.date())
            can_download = False
        context = {
            'can_download': can_download,
            'tabular': records2html,
            'reportname': fname
        }
        return context


class ExceedanceDataReportView(AuthorizedView):
    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        from_date = kwargs.get('from_date')
        to_date = kwargs.get('to_date')
        dwld = kwargs.get('dwld')

        industries = request.user.assigned_industries.order_by(
            'name').values(**{
            "uid": F('uuid'),
            "sname": F('name'),
        })
        df = pd.DataFrame(industries)
        industry_options = list(zip(df.uid, df.sname))
        # we will give time frame for month wise and all
        context = {
            'industry_options': industry_options,
        }
        if not (from_date and to_date):  # '%d/%m/%Y'
            from_date = datetime.now() - timedelta(days=90)
            to_date = datetime.now()
        else:
            from_date = datetime.strptime(from_date, "%m/%d/%Y")
            to_date = datetime.strptime(to_date, "%m/%d/%Y")
        if pk:
            industry = Industry.objects.get(uuid=pk)
            context.update({
                'industry_name': industry.name,
                'current_industry': pk
            })

            q = {
                'reading__timestamp__gte': from_date,
                'reading__timestamp__lte': to_date,
                'industry': industry,
                'dwld': dwld  # this will come via ajax,
            }
            if dwld:
                report = self.get_exceedance_data(**q)
                fl = open(report, 'rb')
                response = FileResponse(fl,
                                        filename=os.path.basename(report))
                return response
            else:
                context.update(self.get_exceedance_data(**q))

            context.update({
                'from_date': from_date.date(),
                'to_date': to_date.date(),
                # 'tabular': tabular,
                'industry_name': industry.name,
                'industry_type': industry.type,
                'current_industry': pk,
            })
        else:
            context.update({
                'current_industry': industry_options[0][0],
                'from_date': from_date.date(),
                'to_date': to_date.date(),
            })

        info_template = get_template('exceedance-data-report.html')
        html = info_template.render(context, request)
        return HttpResponse(html)

    def get_exceedance_data(self, **q):
        industry = q.pop('industry')
        dwld = q.pop('dwld')
        from_date = q.get('reading__timestamp__gte')
        to_date = q.get('reading__timestamp__lte')
        current_readings = Reading.objects.filter(station__industry=industry,
                                                  **q).values_list('reading',
                                                                   flat=True)
        readings = list(current_readings)

        rdate = datetime.now().strftime('%d_%m_%Y')
        fname = '%s_%s.xlsx' % (str(industry.name).replace(' ', '_'), rdate)
        df = pd.DataFrame(readings)

        cols = df.columns.drop('timestamp')

        adict = {'Between Date': '%s to %s' % (from_date.strftime('%d-%B-%Y'),
                                               to_date.strftime('%d-%B-%Y'))
                 }
        if not df.empty:
            spmeta = StationParameter.objects.filter(
                station__industry=industry).distinct('parameter__name').values(
                **{
                    'name': F('parameter__name'),
                    'max': F('maximum'),
                    'min': F('minimum'),
                }
            )
            pmeta = {}
            for p in spmeta:
                pmeta[p.get('name')] = p.get('min'), p.get('max')

            for col in cols:
                param_val = pmeta.get(col) or (0, 0)
                col_min, col_max = param_val
                df[col] = df[col].apply(pd.to_numeric, errors='coerce')
                df = df[(df[col] > col_min) & (df[col] < col_max)]
                adict[col] = df[col].count()

            newdf = pd.DataFrame([adict])
            if dwld:
                fpath = os.path.join(TMP_PATH, fname)
                writer = ExcelWriter(fpath, engine='xlsxwriter',
                                     datetime_format='mm-dd-yyyy hh:mm:ss',
                                     date_format='mm-dd-yyyy')
                newdf.to_excel(writer)
                writer.save()
                return fpath

            records2html = newdf.to_html(
                classes="table table-bordered",
                index=False,
                max_rows=50,
                justify='left'
            )
            can_download = True
        else:

            records2html = '<br><h3> No Records in range: %s - %s</h1>' % (
                from_date.date(), to_date.date())
            can_download = False
        context = {
            'can_download': can_download,
            'tabular': records2html,
            'reportname': fname
        }
        return context


class ReportView(AuthorizedView):

    def get(self, request, **kwargs):
        from_date = kwargs.get('from_date')
        to_date = kwargs.get('to_date')
        rtype = kwargs.get('rtype')
        dwld = kwargs.get('dwld')
        stations = request.user.assigned_stations.order_by(
            'name').values(**{
            "uid": F('uuid'),
            "sname": Concat(F('name'), Value(': '),
                            F('industry__name'),
                            output_field=CharField())

        })
        industries = request.user.assigned_industries.order_by(
            'name').values(**{
            "uid": F('uuid'),
            "iname": Concat(F('name'), Value(': '),
                            F('type'),
                            output_field=CharField())

        })
        idf = pd.DataFrame(industries)
        industry_options = list(zip(idf.uid, idf.iname))
        df = pd.DataFrame(stations)
        station_options = list(zip(df.uid, df.sname))
        # we will give time frame for month wise and all
        reports = (
            ('lodr', 'Live Offline Delay'),
            ('mor', 'Monthly Offline Report'),
            # ('indr', 'Industry Report'),
            # ('mbr', 'Monthly Backup Report'),
            # later ('cpcbar', 'Alarm Report'),
            # later ('shr', 'Station Halt Report'),
            # later ('dr', 'Distillery Report'),
            # ('crpr', 'CRP Report'),
        )
        categories = Category.objects.all().values_list('name', flat=True)
        context = {
            'reports': reports,
            'categories': categories,
            'station_options': station_options,
            'industry_options': industry_options
        }

        if not (from_date and to_date):  # '%d/%m/%Y'
            from_date = datetime.now() - timedelta(days=90)
            to_date = datetime.now()
        else:
            from_date = datetime.strptime(from_date, "%m/%d/%Y")
            to_date = datetime.strptime(to_date, "%m/%d/%Y").replace(hour=23,
                                                                     minute=59)

        q = {
            'reading__timestamp__gte': from_date,
            'reading__timestamp__lte': to_date,
            'dwld': dwld  # this will come via ajax,
        }
        if dwld:
            response = JsonResponse(dict(status=False))
            if rtype == 'lodr':
                report = self.get_live_offline_delay(**q)
                fl = open(report, 'rb')
                response = FileResponse(fl,
                                        filename=os.path.basename(report))
            elif rtype == 'mor':
                report = self.get_monthly_offline(**q)
                fl = open(report, 'rb')
                response = FileResponse(fl,
                                        filename=os.path.basename(report))
            return response
        else:
            if rtype == 'lodr':
                context.update(self.get_live_offline_delay(**q))
            elif rtype == 'mor':
                context.update(self.get_monthly_offline(**q))

        context.update({
            'from_date': from_date.date(),
            'to_date': to_date.date(),
            # 'tabular': tabular,
            'current_report': rtype or 'lodr',
            'current_industry': None
            # 'can_download': can_download
        })
        info_template = get_template('reports.html')
        html = info_template.render(context, request)
        return HttpResponse(html)

    def get_live_offline_delay(self, **q):
        dwld = q.pop('dwld')
        from_date = q.get('reading__timestamp__gte')
        to_date = q.get('reading__timestamp__lte')
        columns = {
            'Industry': F('name'),
            'State': F('state__name'),
            'Address': F('address'),
            'Industry Type': F('type'),
            'Status': F('status'),
        }
        industries = self.request.user.assigned_industries.filter(
            status__in=['Live', 'Offline', 'Delay']).order_by(
            'name').values(**columns)
        df = pd.DataFrame(industries)
        rdate = datetime.now().strftime('%d_%m_%Y')
        fname = 'live_offline_report_%s.xlsx' % rdate
        if dwld:
            fpath = os.path.join(TMP_PATH, fname)
            writer = ExcelWriter(fpath, engine='xlsxwriter',
                                 datetime_format='mm-dd-yyyy hh:mm:ss',
                                 date_format='mm-dd-yyyy')
            df_live = df[df['Status'] == 'Live']
            df_live.to_excel(writer, 'Live', index=False)
            df_offline = df[df['Status'] == 'Offline']
            df_offline.to_excel(writer, 'Offline', index=False)
            df_delay = df[df['Status'] == 'Delay']
            df_delay.to_excel(writer, 'Delay', index=False)
            writer.save()
            return fpath

        if not df.empty:
            columns = list(df.columns)
            df.rename(columns={col: col.upper() for col in columns},
                      inplace=True)

            records2html = df.to_html(index=False,
                                      justify='left',
                                      classes="table table-bordered",
                                      table_id='reportTable')
            can_download = True
        else:

            records2html = '<br><h3> No Records in range: %s - %s</h1>' % (
                from_date.date(), to_date.date())
            can_download = False
        context = {
            'can_download': can_download,
            'tabular': records2html,
            'reportname': fname
        }
        return context

    def get_monthly_offline(self, **q):
        dwld = q.pop('dwld')
        from_date = q.get('reading__timestamp__gte')
        to_date = q.get('reading__timestamp__lte')
        columns = {
            'Category': F('industry__type'),
            'Industry Code': F('industry__industry_code'),
            'Industry': F('industry__name'),
            'Address': F('industry__address'),
            'Contact No.': F('user_ph'),  # TBD
            'State': F('industry__state'),
            'Station': F('name'),
            'Last Data Fetched': F('stationinfo__last_seen'),
            # 'No. of days when data not submitted': F('stationinfo__last_seen'),
            'Ganga Basin': F('industry__ganga'),
            'Reason for offline': F('closure_status'),
            'uid': F('uuid'),
        }
        industries = self.request.user.assigned_stations.filter(
            status='Offline',
            stationinfo__last_seen__gte=from_date,
        ).order_by('name', '-stationinfo__last_seen').distinct('name').values(
            **columns)
        df = pd.DataFrame(industries)
        rdate = datetime.now().strftime('%d_%m_%Y')
        fname = 'latest_offline_report_%s.xlsx' % rdate
        if not df.empty:
            parameters = []
            for uid in df['uid']:
                parameters.append(
                    ', '.join(
                        StationParameter.objects.filter(
                            station__uuid=uid).values_list(
                            'parameter__name', flat=True)))
            df['Parameters'] = parameters
            df['Days Since Offline'] = (pd.Timestamp.today() - pd.to_datetime(
                df['Last Data Fetched'])).dt.days
            df['Last Data Fetched'] = df['Last Data Fetched'].dt.strftime(
                "%Y-%m-%d %H:%M:%S")
            df = df.sort_values(by=['Last Data Fetched'], ascending=False)
            df['S No.'] = [sno + 1 for sno in range(len(df.uid))]
            apply_yes_no = np.vectorize(yes_no)
            df['Ganga Basin'] = apply_yes_no(df['Ganga Basin'])

            df = df[[
                "S No.",
                "Category",
                "Industry Code",
                "Industry",

                "Contact No.",
                "State",
                "Station",
                "Parameters",
                "Last Data Fetched",
                "Days Since Offline",
                "Ganga Basin",
                "Reason for offline",
                "Address"
            ]]

            columns = list(df.columns)
            df.rename(columns={col: col.upper() for col in columns},
                      inplace=True)
            records2html = df.to_html(
                classes="table table-bordered",
                index=False,
                justify='left',
                # max_cols=14,
                # max_rows=20
                table_id='reportTable'
            )
            can_download = True
            if dwld:
                fpath = os.path.join(TMP_PATH, fname)
                writer = ExcelWriter(fpath, engine='xlsxwriter',
                                     datetime_format='mm-dd-yyyy hh:mm:ss',
                                     date_format='mm-dd-yyyy')
                df.to_excel(writer, rdate, index=False)
                writer.save()
                return fpath
        else:

            records2html = '<br><h3> No Records in range: %s - %s</h1>' % (
                from_date.date(), to_date.date())
            can_download = False
        context = {
            'can_download': can_download,
            'tabular': records2html,
            'reportname': fname
        }
        return context


class SMSReportView(AuthorizedView):

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        from_date = kwargs.get('from_date')
        to_date = kwargs.get('to_date')
        dwld = kwargs.get('dwld')

        industries = request.user.assigned_industries.order_by(
            'name').values(**{
            "uid": F('uuid'),
            "sname": F('name'),
        })
        df = pd.DataFrame(industries)
        industry_options = [('All', 'All')]
        industry_options.extend(list(zip(df.uid, df.sname)))
        # we will give time frame for month wise and all
        context = {
            'industry_options': industry_options,
        }
        if not (from_date and to_date):  # '%d/%m/%Y'
            from_date = datetime.now() - timedelta(days=30)
            to_date = datetime.now()
        else:
            from_date = datetime.strptime(from_date, "%m/%d/%Y")
            to_date = datetime.strptime(to_date, "%m/%d/%Y")
        if pk:
            q = {
                'reading__timestamp__gte': from_date,
                'reading__timestamp__lte': to_date.replace(hour=23, minute=59),
                'dwld': dwld  # this will come via ajax,
            }
            if pk != 'All':
                industry = request.user.assigned_industries.get(uuid=pk)
                context.update({
                    'current_industry': pk,
                    'industry': industry
                })

            if dwld:
                report = self.get_sms_report(**q)
                fl = open(report, 'rb')
                response = FileResponse(fl,
                                        filename=os.path.basename(report))
                return response
            else:
                context.update(self.get_sms_report(**q))

            context.update({
                'from_date': from_date.date(),
                'to_date': to_date.date(),
                # 'tabular': tabular,
                'current_industry': pk,
            })
        else:
            context.update({
                'current_industry': industry_options[0][0],
                'from_date': from_date.date(),
                'to_date': to_date.date(),
            })

        info_template = get_template('sms-data-report.html')
        html = info_template.render(context, request)
        return HttpResponse(html)

    def get_sms_report(self, **q):
        dwld = q.pop('dwld')
        from_date = q.get('reading__timestamp__gte')
        to_date = q.get('reading__timestamp__lte')
        query = {
            "timestamp__gte": from_date,
            "timestamp__lte": to_date,

        }
        if 'industry' in q:
            industry = q.pop('industry')
            query.update({
                "station__industry": industry
            })

        columns = {
            'Category': F('station__industry__type'),
            'Industry Code': F('station__industry__industry_code'),
            'Industry Name': F('station__industry__name'),
            'Address': F('station__industry__address'),
            'Contact No.': F('station__user_ph'),  # TBD
            'State': F('station__industry__state'),
            'Station': F('station__name'),
            'Ganga Basin': F('station__industry__ganga'),
            'uid': F('station__uuid'),
            'Parameter': F('parameter')
        }
        records = Exceedance.objects.filter(**query
                                            ).values(**columns).annotate(
            Exceedance=Count('parameter')).order_by('Exceedance')

        df = pd.DataFrame(records)
        rdate = datetime.now().strftime('%d_%m_%Y')
        fname = 'sms_report_%s.xlsx' % rdate
        if not df.empty:
            df["Parameter Standard Limit"] = ['' for a in df['Parameter']]
            df["Total SMS"] = [a for a in df['Exceedance']]
            df['S No.'] = [sno + 1 for sno in range(len(df.uid))]
            apply_yes_no = np.vectorize(yes_no)
            df['Ganga Basin'] = apply_yes_no(df['Ganga Basin'])

            df = df[[
                "S No.",
                "Category",
                "Industry Code",
                "Industry Name",
                "Address",
                "Contact No.",
                "State",
                "Station",
                "Parameter Standard Limit",
                "Parameter",
                "Exceedance",
                "Total SMS",
                "Ganga Basin",
            ]]

            columns = list(df.columns)
            df.rename(columns={col: col.upper() for col in columns},
                      inplace=True)
            records2html = df.to_html(
                classes="table table-bordered",
                index=False,
                justify='left',
                # max_cols=14,
                # max_rows=20
                table_id='reportTable'
            )
            can_download = True
            if dwld:
                fpath = os.path.join(TMP_PATH, fname)
                writer = ExcelWriter(fpath, engine='xlsxwriter',
                                     datetime_format='mm-dd-yyyy hh:mm:ss',
                                     date_format='mm-dd-yyyy')
                df.to_excel(writer, rdate, index=False)
                writer.save()
                return fpath
        else:
            records2html = '<br><h3> No Records in range: %s - %s</h1>' % (
                from_date.date(), to_date.date())
            can_download = False
        context = {
            'can_download': can_download,
            'tabular': records2html,
            'reportname': fname
        }
        return context


class IndustryReportView(AuthorizedView):

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        type = kwargs.get('type')
        from_date = kwargs.get('from_date')
        to_date = kwargs.get('to_date')
        dwld = kwargs.get('dwld')

        industries = request.user.assigned_industries.order_by(
            'name').values(**{
            "uid": F('uuid'),
            "sname": F('name'),
        })
        category = Category.objects.all().values('id', 'name')
        cdf = pd.DataFrame(category)
        df = pd.DataFrame(industries)
        category_options = [('All', 'All')]
        category_options.extend(list(zip(cdf.id, cdf.name)))
        industry_options = [('All', 'All')]
        industry_options.extend(list(zip(df.uid, df.sname)))
        # we will give time frame for month wise and all
        context = {
            'industry_options': industry_options,
            'category_options': category_options,
        }
        if not (from_date and to_date):  # '%d/%m/%Y'
            from_date = datetime.now() - timedelta(days=30)
            to_date = datetime.now()
        else:
            from_date = datetime.strptime(from_date, "%m/%d/%Y")
            to_date = datetime.strptime(to_date, "%m/%d/%Y")

        context.update({
            'current_industry': pk,
            'current_category': type,
        })
        if pk:
            q = {
                'from_date': from_date,
                'to_date': to_date.replace(hour=23, minute=59),
                'type': type,
                'industry': pk,
                'dwld': dwld  # this will come via ajax,
            }

            if dwld:
                report = self.get_industry_report(**q)
                fl = open(report, 'rb')
                response = FileResponse(fl,
                                        filename=os.path.basename(report))
                return response
            else:
                context.update(self.get_industry_report(**q))

            context.update({
                'from_date': from_date.date(),
                'to_date': to_date.date(),
                # 'tabular': tabular,
                'current_industry': pk,
            })
        else:
            context.update({
                'current_industry': industry_options[0][0],
                'current_category': category_options[0][0],
                'from_date': from_date.date(),
                'to_date': to_date.date(),
            })

        info_template = get_template('industry-data-report.html')
        html = info_template.render(context, request)
        return HttpResponse(html)

    def get_industry_report(self, **q):
        dwld = q.pop('dwld')
        industry_uuid = q.pop('industry')
        from_date = q.get('from_date')
        to_date = q.get('to_date')
        category = q.get('type')

        columns = {
            'Category': F('type'),
            'Industry Code': F('industry_code'),
            'Industry Name': F('name'),
            'Address': F('address'),
            'State': F('state'),
            'Status': F('status'),
            'Ganga Basin': F('ganga'),
            'uid': F('uuid'),
        }
        records = self.request.user.assigned_industries.filter(
            station__stationinfo__last_seen__gte=from_date,
            station__stationinfo__last_seen__lte=to_date
        )

        if industry_uuid != 'All':
            records = records.filter(uuid=industry_uuid)

        if category != 'All':
            records = records.filter(type__id=category)
        records = records.values(**columns)
        df = pd.DataFrame(records)
        rdate = datetime.now().strftime('%d_%m_%Y')
        fname = 'industry_report_%s.xlsx' % rdate
        if not df.empty:
            df['S No.'] = [sno + 1 for sno in range(len(df.uid))]
            apply_yes_no = np.vectorize(yes_no)
            df['Ganga Basin'] = apply_yes_no(df['Ganga Basin'])

            df = df[[
                "S No.",
                "Category",
                "Industry Code",
                "Industry Name",
                "Address",
                "State",
                "Status",
                "Ganga Basin",
            ]]

            columns = list(df.columns)
            df.rename(columns={col: col.upper() for col in columns},
                      inplace=True)
            records2html = df.to_html(
                classes="table table-bordered",
                index=False,
                justify='left',
                # max_cols=14,
                # max_rows=20
                table_id='reportTable'
            )
            can_download = True
            if dwld:
                fpath = os.path.join(TMP_PATH, fname)
                writer = ExcelWriter(fpath, engine='xlsxwriter',
                                     datetime_format='mm-dd-yyyy hh:mm:ss',
                                     date_format='mm-dd-yyyy')
                df.to_excel(writer, rdate, index=False)
                writer.save()
                return fpath
        else:
            records2html = '<br><h3> No Records in range: %s - %s</h1>' % (
                from_date.date(), to_date.date())
            can_download = False
        context = {
            'can_download': can_download,
            'tabular': records2html,
            'reportname': fname
        }
        return context


class MaintenanceView(AuthorizedView):
    def _get_object(self, pk):
        try:
            return Maintenance.objects.get(id=pk)
        except Maintenance.DoesNotExist:
            raise Http404

    def _get_maintenance(self, request, pk):
        mntnc = self._get_object(pk)
        content = {
            'parameter': mntnc,
            'pk': pk,
            'station': mntnc.station,
            'form': MaintenanceForm(instance=mntnc)
        }
        info_template = get_template('maintenance-info.html')
        # TODO: this render guy takes time
        html = info_template.render(content, request)
        return HttpResponse(html)

    def get(self, request, pk=None):
        if pk:
            return self._get_maintenance(request, pk)

        maintenance = Maintenance.objects.all().select_related('station').values(
            ID=F('id'),
            Name=F('station__name'),
            Parameter=F('parameter__name'),
            Start=F('start_date'),
            To=F('send_to_pcb__name'),
            End=F('end_date'),
            Comment=F('comments'),
        )
        df = pd.DataFrame(maintenance)
        mntnc_href = "<a href='/dashboard/maintenance-info/{id}'>{name}</a>"
        df['Name'] = apply_func(mntnc_href, id=df['ID'], name=df['Name'])
        df = df.drop(columns=['ID'])

        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='left', escape=False),
            'form': MaintenanceForm()
        }
        info_template = get_template('maintenance.html')
        html = info_template.render(content, request)
        return HttpResponse(html)

    def post(self, request, pk=None):
        return self._update_maintanence(request, pk)

    def _update_maintanence(self, request, pk):
        if pk:
            mtnc = self._get_object(pk)
            form = MaintenanceForm(request.POST, instance=mtnc)
            url = reverse('dashboard:maintenance-info', kwargs={'pk': pk})
        else:
            form = MaintenanceForm(request.POST)
            url = reverse('dashboard:maintenance-info', kwargs={'pk': pk})

        if form.is_valid():
            form.save()
            messages.success(request, 'Updated Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')

        return redirect(url)

    def delete(self, request, pk, format=None):
        if request.user.is_admin:
            mntnc = self._get_object(pk)
            mntnc.delete()
            message = 'Successfully Deleted'
            messages.success(request, message, extra_tags="success")
        else:
            message = 'Only Admin Can Delete'
            messages.info(request, message, extra_tags="warning")
        return HttpResponse(request, message)


class DeviceView(AuthorizedView):
    def _get_object(self, pk):
        try:
            return Device.objects.get(id=pk)
        except Device.DoesNotExist:
            raise Http404

    def _get_device(self, request, pk):
        device = self._get_object(pk)
        content = {
            'device': device,
            'pk': pk,
            'form': DeviceForm(instance=device)
        }
        info_template = get_template('device-info.html')
        # TODO: this render guy takes time
        html = info_template.render(content, request)
        return HttpResponse(html)

    def get(self, request, pk=None):
        if pk:
            return self._get_device(request, pk)
        columns = {
            "Id": F("id"),
            "Name": F("name"),
            "Make": F("make"),
            "Upload Method": F("upload_method"),
            "Process Attached": F("process_attached"),
            "Type": F("type"),
            "System Certified": F("system_certified"),
            "Frequency": F("frequency"),
            "Manufacture": F("manufacture"),
            "Model": F("model"),
            "Serial No.": F("serial_no"),
            "Description": F("description"),
            "OEM Vendor": F("oem_vendor"),
        }
        maintenance = Device.objects.all().values(**columns)
        df = pd.DataFrame(maintenance)
        if not df.empty:
            mntnc_href = "<a href='/dashboard/device-info/{id}'>{name}</a>"
            df['Name'] = apply_func(mntnc_href, id=df['Id'], name=df['Name'])
            df = df.drop(columns=['Id'])
        content = {
            'tabular': df.to_html(classes="table table-bordered",
                                  table_id="dataTable", index=False,
                                  justify='left', escape=False),
            'form': DeviceForm()
        }
        info_template = get_template('device.html')
        html = info_template.render(content, request)
        return HttpResponse(html)

    def post(self, request, pk=None):
        return self._update_device(request, pk)

    def _update_device(self, request, pk):
        if pk:
            dvc = self._get_object(pk)
            form = DeviceForm(request.POST, instance=dvc)
            url = reverse('dashboard:device-info', kwargs={'pk': pk})
        else:
            form = DeviceForm(request.POST)
            url = reverse('dashboard:device')
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')
        return redirect(url)

    def delete(self, request, pk, format=None):
        if request.user.is_admin:
            device = self._get_object(pk)
            device.delete()
            message = 'Successfully Deleted'
            messages.success(request, message, extra_tags="success")
        else:
            message = 'Only Admin Can Delete'
            messages.info(request, message, extra_tags="warning")
        return HttpResponse(request, message)