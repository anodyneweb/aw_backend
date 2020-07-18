from django.test import TestCase

# Create your tests here.
# class ReportView_TP(AuthorizedView):
#
#     def get(self, request, **kwargs):
#         pk = kwargs.get('pk')
#         freq = kwargs.get('freq')
#         from_date = kwargs.get('from_date')
#         to_date = kwargs.get('to_date')
#         rtype = kwargs.get('rtype')
#         dwld = kwargs.get('dwld')
#         stations = request.user.assigned_stations.order_by(
#             'name').values(**{
#             "uid": F('uuid'),
#             "sname": Concat(F('name'), Value(': '),
#                             F('industry__name'),
#                             output_field=CharField())
#
#         })
#         df = pd.DataFrame(stations)
#         station_options = list(zip(df.uid, df.sname))
#         # we will give time frame for month wise and all
#         reports = (
#             ('sdr', 'Station Data'),
#             ('lodr', 'Live Offline Delay'),
#             ('offr', 'Montly Backup Report'),
#             ('exceed', 'Exceedance Report'),
#             # latest offline---> List of station which recently got offline
#
#             # ('mbr', 'Monthly Backup Report'),
#             # ('smsr', 'SMS Report'),
#
#             # later ('cpcbar', 'Alarm Report'),
#             # later ('shr', 'Station Halt Report'),
#             # later ('dr', 'Distillery Report'),
#             # ('crpr', 'CRP Report'),
#         )
#         categories = Category.objects.all().values_list('name', flat=True)
#         context = {
#             'station_options': station_options,
#             'reports': reports,
#             'categories': categories
#         }
#         if station_options:
#             context.update({'current_station': station_options[0][0]})
#         if pk:
#             station = Station.objects.get(uuid=pk)
#             if not (from_date and to_date):  # '%d/%m/%Y'
#                 from_date = datetime.now() - timedelta(days=90)
#                 to_date = datetime.now()
#             else:
#                 from_date = datetime.strptime(from_date, "%m/%d/%Y")
#                 to_date = datetime.strptime(to_date, "%m/%d/%Y")
#
#             q = {
#                 'reading__timestamp__gte': from_date,
#                 'reading__timestamp__lte': to_date,
#                 'station': station,
#                 'freq': freq,
#                 'dwld': dwld  # this will come via ajax,
#             }
#             if dwld:
#                 response = JsonResponse(dict(status=False))
#                 if rtype == 'lodr':
#                     report = self.get_live_offline_delay(**q)
#                     fl = open(report, 'rb')
#                     response = FileResponse(fl,
#                                             filename=os.path.basename(report))
#                 elif rtype == 'sdr':
#                     report = self.get_station_data(**q)
#                     fl = open(report, 'rb')
#                     response = FileResponse(fl,
#                                             filename=os.path.basename(report))
#                 elif rtype == 'offr':
#                     report = self.get_latest_offline(**q)
#                     fl = open(report, 'rb')
#                     response = FileResponse(fl,
#                                             filename=os.path.basename(report))
#                 return response
#             else:
#                 if rtype == 'lodr':
#                     context.update(self.get_live_offline_delay(**q))
#                 elif rtype == 'sdr':
#                     context.update(self.get_station_data(**q))
#                 elif rtype == 'offr':
#                     context.update(self.get_latest_offline(**q))
#
#             context.update({
#                 'from_date': from_date.date(),
#                 'to_date': to_date.date(),
#                 # 'tabular': tabular,
#                 'station_name': station.name,
#                 'industry_name': station.industry.name,
#                 'industry_type': station.industry.type,
#                 'current_station': pk,
#                 'current_freq': freq,
#                 'current_report': rtype,
#                 # 'can_download': can_download
#             })
#         info_template = get_template('reports.html')
#         html = info_template.render(context, request)
#         return HttpResponse(html)
#
#     # TODO Industry Wise Report Offline Live Delay
#
#     def get_live_offline_delay(self, **q):
#         dwld = q.pop('dwld')
#         from_date = q.get('reading__timestamp__gte')
#         to_date = q.get('reading__timestamp__lte')
#         columns = {
#             'Company Name': F('name'),
#             'State': F('state__name'),
#             'Address': F('address'),
#             'Industry Type': F('type'),
#             'Status': F('status'),
#         }
#         industries = self.request.user.assigned_industries.filter(
#             status__in=['Live', 'Offline', 'Delay']).order_by(
#             'name').values(**columns)
#         df = pd.DataFrame(industries)
#         rdate = datetime.now().strftime('%d_%m_%Y')
#         fname = 'industry_report_%s.xlsx' % rdate
#         if dwld:
#             writer = ExcelWriter(fname, engine='xlsxwriter',
#                                  datetime_format='mm-dd-yyyy hh:mm:ss',
#                                  date_format='mm-dd-yyyy')
#             df_live = df[df['Status'] == 'Live']
#             df_live.to_excel(writer, 'Live', index=False)
#             df_offline = df[df['Status'] == 'Offline']
#             df_offline.to_excel(writer, 'Offline', index=False)
#             df_delay = df[df['Status'] == 'Delay']
#             df_delay.to_excel(writer, 'Delay', index=False)
#             writer.save()
#             return fname
#
#         if not df.empty:
#             columns = list(df.columns)
#             df.rename(columns={col: col.upper() for col in columns},
#                       inplace=True)
#
#             records2html = df.to_html(
#                 classes='report_scroll table table-bordered table-responsive '
#                         'table-hover', table_id='reportTable')
#             can_download = True
#         else:
#
#             records2html = '<br><h3> No Records in range: %s - %s</h1>' % (
#                 from_date.date(), to_date.date())
#             can_download = False
#         context = {
#             'can_download': can_download,
#             'tabular': records2html,
#             'reportname': fname
#         }
#         return context
#
#     def get_station_data(self, **q):
#         freq = q.pop('freq')
#         station = q.pop('station')
#         dwld = q.pop('dwld')
#         from_date = q.get('reading__timestamp__gte')
#         to_date = q.get('reading__timestamp__lte')
#         current_readings = Reading.objects.filter(station=station,
#                                                   **q).values_list(
#             'reading', flat=True)
#         readings = list(current_readings)
#         rdate = datetime.now().strftime('%d_%m_%Y')
#         fname = 'station_data_%s.xlsx' % rdate
#         df = pd.DataFrame(readings)
#         if not df.empty:
#             columns = list(df.columns)
#             df.rename(columns={col: col.upper() for col in columns},
#                       inplace=True)
#             df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])
#             cols = df.columns.drop('TIMESTAMP')
#             df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
#             if freq == 'monthly':
#                 df = df.resample('M', on='TIMESTAMP').mean()
#             elif freq == 'weekly':
#                 df = df.resample('7D', on='TIMESTAMP').mean()
#             elif freq == 'daily':
#                 df = df.resample('D', on='TIMESTAMP').mean()
#             elif freq == 'hourly':
#                 df = df.resample('h', on='TIMESTAMP').mean()
#             elif freq == '15Min':
#                 df = df.resample('15Min', on='TIMESTAMP').mean()
#             elif freq == 'yearly':
#                 df = df.resample('A', on='TIMESTAMP').mean()
#
#             df = df.round(2)
#             df = df.dropna(axis=0, how='all', thresh=None,
#                            subset=list(df.columns), inplace=False)
#             df = df.fillna('')
#             df.sort_values(by='TIMESTAMP', ascending=False, inplace=True)
#             df = df.set_index('TIMESTAMP')
#             if dwld:
#                 writer = ExcelWriter(fname, engine='xlsxwriter',
#                                      datetime_format='mm-dd-yyyy hh:mm:ss',
#                                      date_format='mm-dd-yyyy')
#                 df.to_excel(writer)
#                 writer.save()
#                 return fname
#
#             records2html = df.to_html(
#                 classes='report_scroll table table-bordered table-responsive '
#                         'table-hover', table_id='reportTable',
#                 max_rows=150
#             )
#             can_download = True
#         else:
#
#             records2html = '<br><h3> No Records in range: %s - %s</h1>' % (
#                 from_date.date(), to_date.date())
#             can_download = False
#         context = {
#             'can_download': can_download,
#             'tabular': records2html,
#             'reportname': fname
#         }
#         return context
#
#     def get_latest_offline(self, **q):
#         dwld = q.pop('dwld')
#         from_date = q.get('reading__timestamp__gte')
#         to_date = q.get('reading__timestamp__lte')
#         columns = {
#             'Category': F('industry__type'),
#             'Industry Code': F('industry__industry_code'),
#             'Industry': F('industry__name'),
#             'Address': F('industry__address'),
#             'Contact No.': F('user_ph'),  # TBD
#             'State': F('industry__state'),
#             'Station': F('name'),
#             'Last Data Fetched': F('stationinfo__last_seen'),
#             # 'No. of days when data not submitted': F('stationinfo__last_seen'),
#             'Ganga Basin': F('ganga_basin'),
#             'Reason for offline': F('closure_status'),
#             'uid': F('uuid'),
#         }
#         industries = self.request.user.assigned_stations.filter(
#             stationinfo__last_seen__lt=(
#                     datetime.now() - timedelta(hours=48))).order_by('name',
#                                                                     '-stationinfo__last_seen').distinct(
#             'name').values(**columns)
#         df = pd.DataFrame(industries)
#         parameters = []
#         for uid in df['uid']:
#             parameters.append(
#                 ', '.join(
#                     StationParameter.objects.filter(
#                         station__uuid=uid).values_list(
#                         'parameter_name__parameter', flat=True)))
#         df['Parameters'] = parameters
#         #
#         df['Days Since Offline'] = (pd.Timestamp.today() - pd.to_datetime(
#             df['Last Data Fetched'])).dt.days
#         df['Last Data Fetched'] = df['Last Data Fetched'].dt.strftime(
#             "%Y-%m-%d %H:%M:%S")
#         df = df.sort_values(by=['Last Data Fetched'], ascending=False)
#         df['S No.'] = [sno + 1 for sno in range(len(df.uid))]
#
#         df = df[[
#             "S No.",
#             "Category",
#             "Industry Code",
#             "Industry",
#
#             "Contact No.",
#             "State",
#             "Station",
#             "Parameters",
#             "Last Data Fetched",
#             "Days Since Offline",
#             "Ganga Basin",
#             "Reason for offline",
#             "Address"
#         ]]
#         rdate = datetime.now().strftime('%d_%m_%Y')
#         fname = 'latest_offline_report_%s.xlsx' % rdate
#         if not df.empty:
#             columns = list(df.columns)
#             df.rename(columns={col: col.upper() for col in columns},
#                       inplace=True)
#             records2html = df.to_html(
#                 classes='report_scroll table table-bordered table-responsive '
#                         'table-hover',
#                 index=False,
#                 justify='center',
#                 # max_cols=14,
#                 # max_rows=20
#                 table_id='reportTable'
#             )
#             can_download = True
#             if dwld:
#                 writer = ExcelWriter(fname, engine='xlsxwriter',
#                                      datetime_format='mm-dd-yyyy hh:mm:ss',
#                                      date_format='mm-dd-yyyy')
#                 df.to_excel(writer, rdate, index=False)
#                 writer.save()
#                 return fname
#         else:
#
#             records2html = '<br><h3> No Records in range: %s - %s</h1>' % (
#                 from_date.date(), to_date.date())
#             can_download = False
#         context = {
#             'can_download': can_download,
#             'tabular': records2html,
#             'reportname': fname
#         }
#         return context