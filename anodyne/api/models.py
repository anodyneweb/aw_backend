# Create your models here.
import logging
import uuid as uuid
from datetime import datetime, timedelta

import django.utils.timezone
import jwt
from django.conf import settings
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.contrib.postgres.fields import CICharField
from django.db import models

log = logging.getLogger('vepolink')
from django.contrib.postgres.fields import HStoreField


class State(models.Model):
    name = models.CharField(max_length=256, blank=True, unique=True)

    def __str__(self):  # __unicode__ on Python 2
        return self.name


class City(models.Model):
    name = models.CharField(max_length=256, blank=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

    def __str__(self):
        return '%s: %s' % (self.state, self.name)

    class Meta:
        unique_together = (('name', 'state'),)


class Unit(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.name


class PCB(models.Model):
    name = models.CharField(max_length=256, unique=True)
    email = models.EmailField(verbose_name='PCB Email',
                              max_length=255,
                              blank=True
                              )
    var1 = models.CharField(max_length=256)
    var2 = models.CharField(max_length=256)
    var3 = models.TextField(default=None)
    state = models.ForeignKey(State, on_delete=models.CASCADE,
                              to_field='name', null=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)
    country = models.CharField(max_length=80, default='India', editable=False)

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_staffuser(self, email, password):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, name, type):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.admin = True
        user.name = name
        user.type = type if type in ['CUSTOMER', 'CPCB', 'ADMIN',
                                     'STAFF'] else 'ADMIN'
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    username = None
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    active = models.BooleanField(default=True,
                                 help_text='uncheck to block user (inactivate)',
                                 )
    staff = models.BooleanField(default=True)  # a staff not using it for now;
    is_cpcb = models.BooleanField(default=False,
                                  help_text='Only for CPCB user')
    admin = models.BooleanField(default=False,
                                help_text='admin user can add/edit/delete details')
    created = models.DateTimeField(default=django.utils.timezone.now,
                                   blank=True, editable=False,
                                   verbose_name='Joined On')
    # notice the absence of a "Password field", that's built in.
    # USER DETAILS STARTS
    name = models.CharField(max_length=60, null=False,
                            verbose_name='Full Name',
                            default='')
    phone = models.CharField(max_length=120, null=True,
                             help_text="use semi-colon(;) for multiple numbers")
    address = models.TextField(default=None, null=True)
    zipcode = models.IntegerField(default=None, null=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE,
                              to_field='name', null=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)
    country = models.CharField(max_length=80, default='India', editable=False)
    station = models.ManyToManyField('Station', default=None)

    # USER DETAILS ENDS
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', ]

    def get_full_name(self):
        # The user is identified by their email address
        return self.name

    def get_short_name(self):
        # The user is identified by their email address
        return self.email

    def __str__(self):  # __unicode__ on Python 2
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        """Is the user a member of staff?"""
        return self.staff

    @property
    def is_admin(self):
        """Is the user a admin member?"""
        return self.admin

    @property
    def is_active(self):
        """Is the user active?"""
        return self.active

    def _generate_jwt_token(self):
        """
        Generates a JSON Web Token that stores this user's ID and has an expiry
        date set to 10 days into the future.
        """
        dt = datetime.now() + timedelta(days=10)
        token = jwt.encode({
            'id': str(self.id),
            'exp': int(dt.strftime('%s'))
        }, settings.SECRET_KEY, algorithm='HS256')

        return token.decode('utf-8')

    @property
    def token(self):
        """
        Allows us to get a user's token by calling `user.token` instead of
        `user.generate_jwt_token().

        The `@property` decorator above makes this possible. `token` is called
        a "dynamic property".
        """
        return self._generate_jwt_token()

    # @staticmethod
    # def new_user_hook(sender, instance, created, **kwargs):
    #     """
    #     A User post_save hook to create a User Profile
    #     """
    #     if created and instance.email != settings.ANONYMOUS_USER_NAME:
    #         if instance.is_superuser:
    #             # to add multiple many2many obj. use 'set' else 'add'
    #             sites = Station.objects.select_related()
    #             instance.site.set(sites)
    #             instance.save()

    @property
    def assigned_stations(self):
        if self.admin:
            return Station.objects.select_related('industry')
        return self.station.select_related('industry')

    @property
    def assigned_industries(self):
        if self.is_admin:
            return Industry.objects.all()
        uuids = self.station.values_list('industry__uuid')
        industries = Industry.objects.filter(uuid__in=uuids)
        return industries

    # hook in the New Manager to our Model
    objects = UserManager()


class Industry(models.Model):
    industry_status = (
        ('Live', 'Live'),
        ('Delay', 'Delay'),
        ('Offline', 'Offline'),
    )
    uuid = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True,
        max_length=120,
        unique=True
    )
    user = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL
    )
    name = models.CharField(
        max_length=256,
        unique=True,
        verbose_name='Industry Name'
    )
    industry_code = models.CharField(max_length=160,
                                     verbose_name='Industry Code (as per CPCB)')
    status = models.CharField(
        max_length=120,
        choices=industry_status,
        default='Offline'
    )
    type = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        to_field='name',
        null=True
    )
    industry_id = models.CharField(
        max_length=160,
        default='',
        verbose_name='Industry Code/Id',
        null=True
    )
    # Address details of the Industry
    address = models.TextField(
        default=None,
        null=True
    )
    zipcode = models.IntegerField(
        default=None,
        null=True
    )
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        to_field='name',
        null=True
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        null=True,
    )
    country = models.CharField(
        max_length=80,
        default='India',
        editable=False
    )
    created = models.DateTimeField(
        auto_now_add=True,
        blank=True
    )
    ganga = models.BooleanField(
        default=False,
        verbose_name='Ganga Basin'
    )

    class Meta:
        default_permissions = ()

    def __str__(self):
        return str(self.name)


class Station(models.Model):
    PPCB = 'PPCB'
    MPPCB = 'MPPCB'
    TSPCB = 'TSPCB'
    HSPCB = 'HSPCB'
    UPPCB = 'UPPCB'
    DPCC = 'DPCC'
    JSPCB = 'JSPCB'

    CLOSURE_CHOICES = (
        (None, 'None'),
        ('Seasonal', 'Seasonal'),
        ('Plant Shutdown', 'Plant Shutdown'),
        ('Under Maintenance', 'Under Maintenance'),
        ('By CPCB', 'By CPCB')
    )
    STATUS_CHOICES = (
        ('Live', 'Live'),
        ('Delay', 'Delay'),
        ('Offline', 'Offline')
    )
    MONITORING_TYPE_CHOICES = (
        ('Effluent', 'Effluent'),
        ('Emission', 'Emission'),
        ('CAAQMS', 'CAAQMS'),
    )

    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True,
                            max_length=120)
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE,
                                 verbose_name='Industry')
    name = models.CharField(max_length=100, verbose_name='Station')

    # NOT FOR ALL PCBs #
    site_id = models.CharField(max_length=80,
                               verbose_name='Site ID or Station ID',
                               default=None, null=True)
    key = models.TextField(max_length=1000, default=None, null=True,
                           verbose_name='Key or Token', blank=True)
    pub_key = models.TextField(max_length=1000, null=True, default=None,
                               verbose_name='Public Key', blank=True)
    pvt_key = models.TextField(max_length=1000, null=True, default=None,
                               verbose_name='Private Key', blank=True)
    # NOT FOR ALL PCBs Ends #
    pcb = models.ForeignKey(PCB, on_delete=models.CASCADE,
                            to_field='name', null=True)
    realtime_url = models.CharField(verbose_name='Realtime URL',
                                    default=None, null=True,
                                    max_length=1024,
                                    blank=True)
    delayed_url = models.URLField(verbose_name='Delayed URL',
                                  default=None, null=True,
                                  max_length=1024,
                                  blank=True)
    prefix = models.CharField(max_length=64, unique=True,
                              verbose_name='File Prefix',
                              help_text='unique name used in file, from '
                                        'station',
                              db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES,
                              default='Offline',
                              blank=True)
    # Address details of the Station
    address = models.TextField(default=None, null=True, blank=True)
    zipcode = models.IntegerField(default=None, null=True, blank=True)
    longitude = models.DecimalField(decimal_places=15, max_digits=20,
                                    null=True,
                                    blank=True)
    latitude = models.DecimalField(decimal_places=15, max_digits=20, null=True,
                                   blank=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE,
                              to_field='name', null=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)
    country = models.CharField(max_length=80, default='India', editable=False,
                               blank=True)
    # emails/phone of customer
    user_email = models.TextField(max_length=255, default=None, null=True,
                                  verbose_name='Customer Alert Email',
                                  help_text='for multiple emails use semi-colon(;)',
                                  blank=True)
    user_ph = models.TextField(max_length=255, default=None, null=True,
                               verbose_name='Customer Alert Contact',
                               help_text='for multiple contacts use semi-colon(;)',
                               blank=True)
    is_cpcb = models.BooleanField(default=False, verbose_name='Is CPCB',
                                  help_text='send data to cpcb also',
                                  blank=True)
    cpcb_email = models.TextField(max_length=255, default=None, null=True,
                                  verbose_name='CPCB Alert Email',
                                  help_text='for multiple emails use semi-colon(;)',
                                  blank=True)
    cpcb_ph = models.TextField(max_length=255, default=None, null=True,
                               verbose_name='CPCB Alert Contacts',
                               help_text='for multiple contacts use semi-colon(;)',
                               blank=True)
    closure_status = models.TextField(max_length=255,
                                      verbose_name='Offline Reason',
                                      default=None,
                                      help_text='Mention Offline Reason if any',
                                      blank=True)
    monitoring_type = models.CharField(max_length=20, default=None,
                                       choices=MONITORING_TYPE_CHOICES,
                                       blank=True)
    process_attached = models.CharField(max_length=20, default='Inlet',
                                        choices=(('Inlet', 'Inlet'),
                                                 ('Outlet', 'Outlet'),
                                                 ),
                                        blank=True)
    ganga = models.BooleanField(default=False,
                                verbose_name='Ganga Basin')
    approval_date = models.DateField(verbose_name='Approved On',
                                     help_text='YYYY-MM-DD',
                                     default=django.utils.timezone.now,
                                     blank=True)
    amc = models.DateTimeField(blank=True, null=True,
                               help_text='YYYY-MM-DD',
                               default=None, verbose_name='AMC')
    cmc = models.DateTimeField(blank=True, null=True,
                               help_text='YYYY-MM-DD',
                               default=None, verbose_name='CMC')
    active = models.BooleanField(default=True, verbose_name='Enable Upload',
                                 help_text='uncheck to disable data upload')
    created = models.DateTimeField(auto_now_add=True, blank=True)
    camera = models.URLField(max_length=200, blank=True,
                             help_text='Camera IP or URL',
                             verbose_name='Camera URL/IP')

    @property
    def parameters(self):
        parameters = StationParameter.objects.filter(station=self).values_list(
            'parameter__name',
            flat=True)
        if parameters:
            return parameters
        else:
            return list()

    # def update_status(self):
    #     status = 'Offline'
    #     try:
    #         station = StationInfo.objects.get(station=self)
    #         if station.last_seen > (datetime.now() - timedelta(hours=4)):
    #             status = 'Online'
    #         elif (datetime.now() - timedelta(hours=48)) < station.last_seen < (datetime.now() - timedelta(hours=4)):
    #             status = 'Delay'
    #     except StationInfo.DoesNotExist:
    #         pass
    #     return status

    def __str__(self):
        return "%s | %s | %s | %s" % (self.name, self.industry.name,
                                      self.pcb, self.state)


class StationInfo(models.Model):
    STATUS_CHOICES = (
        ('Live', 'Live'),
        ('Delay', 'Delay'),
        ('Offline', 'Offline')
    )
    station = models.OneToOneField(
        Station,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    last_seen = models.DateTimeField(
        verbose_name='Last Seen',
        auto_now_add=True,
        null=True
    )
    mail_interval = models.IntegerField(
        default=12,  # hours
        null=True,
        verbose_name='Mail Alert Intervals'
    )
    sms_interval = models.IntegerField(
        default=12,  # hours
        null=True,
        verbose_name='SMS Alert Intervals'
    )
    last_upload_info = models.TextField(
        max_length=256,
        blank=True,
        default=''
    )
    latest_reading = models.TextField(max_length=999, blank=True)


class Parameter(models.Model):
    """
    Add the citext extension to postgres: e.g. in psql:
    # connect to database and
    # CREATE EXTENSION IF NOT EXISTS citext;
    else migration will fail
    """
    name = CICharField(max_length=80, default=None, unique=True,
                       db_index=True)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True)
    alias = models.CharField(max_length=100, null=True, verbose_name='Alias')
    # hex code or color name
    color_code = models.CharField(max_length=50, null=True, default=None,
                                  verbose_name='Param Color')

    # allowed = models.BooleanField(default=False, verbose_name='Is Allowed')

    @staticmethod
    def check4new(sender, created, instance=None, **kwargs):
        if created:
            param, pcreated = Parameter.objects.get_or_create(
                parameter=instance.parameter)
            param.station.add(instance.station)
            if pcreated:
                log.info(
                    'New Param: %s Added' % instance.parameter
                )
        # Sync units of all SiteParameters
        parameters = Parameter.objects.all().values_list('parameter',
                                                         flat=True)
        try:
            for p in parameters:
                sparams = StationParameter.objects.filter(
                    unit=None,
                    parameter=p
                )
                p = Parameter.objects.get(parameter=p)
                if sparams and p.unit:
                    sparams.update(unit=p.unit)
        except:
            pass

    def __str__(self):
        return '%s (%s)' % (self.name, self.unit)


class StationParameter(models.Model):
    """
    This will have all the parameters attached to a Site
    """
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        db_index=True
    )
    parameter = models.ForeignKey(
        Parameter,
        on_delete=models.CASCADE,
    )
    minimum = models.FloatField(
        default=0,
        null=True
    )
    maximum = models.FloatField(
        default=0,
        null=True
    )
    process_name = models.CharField(
        max_length=120,
        default='Inlet',
        choices=(('Inlet', 'Inlet'),
                 ('Outlet', 'Outlet'),
                 ),
        verbose_name='Process'
    )
    monitoring_type = models.CharField(
        max_length=20,
        default=None,
        choices=Station.MONITORING_TYPE_CHOICES,
        null=True,
        verbose_name='Monitoring'
    )
    monitoring_id = models.CharField(
        max_length=20,
        default=None,
        null=True,
        verbose_name='Monitoring ID'
    )
    analyser_id = models.CharField(
        max_length=20,
        default=None,
        null=True,
        verbose_name='Monitoring'
    )
    allowed = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )

    class Meta:
        unique_together = (('station', 'parameter'),)

    def __str__(self):
        return '%s: %s' % (self.station.name, self.parameter)


class Reading(models.Model):
    station = models.ForeignKey(Station,
                                null=True,
                                on_delete=models.CASCADE,
                                db_index=True
                                )
    reading = HStoreField(max_length=1024, blank=True)

    class Meta:
        unique_together = (('reading', 'station'),)

    def __str__(self):
        return "%s: %s" % (self.station, self.reading)


class Registration(models.Model):
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
        help_text="use semi-colon(;) for multiple emails"
    )
    fname = models.CharField(
        max_length=120, verbose_name='Contact Person Name',
    )
    # lname = models.CharField(
    #     max_length=120,
    #     verbose_name='Last Name',
    #     blank=True
    # )
    phone = models.CharField(max_length=120,
                             help_text="use semi-colon(;) for multiple numbers")
    # industry = models.CharField(
    #     max_length=120,
    #     blank=True
    # )
    query = models.TextField(
        default=None,
        blank=True
    )


class Exceedance(models.Model):
    station = models.ForeignKey(Station,
                                null=True,
                                on_delete=models.CASCADE,
                                db_index=True
                                )
    parameter = models.CharField(
        max_length=20,
        default=None,
        null=True,
    )
    value = models.FloatField(
        default=0,
        null=True
    )
    timestamp = models.DateTimeField()

    def __str__(self):
        return '%s: %s (%s)' % (self.station, self.parameter, self.value)

    class Meta:
        unique_together = (('station', 'parameter', 'value', 'timestamp'),)


class SMSAlert(models.Model):
    station = models.ForeignKey(Station,
                                null=True,
                                on_delete=models.CASCADE,
                                db_index=True
                                )
    message = models.TextField(default=None)
    contact = models.TextField(default=None,
                               help_text='Contacts Semicolon separated')
    timestamp = models.DateTimeField(
        auto_now_add=True,
        blank=True
    )

    def __str__(self):
        return '%s: %s' % (self.station, self.message)


class Device(models.Model):
    name = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Name')
    make = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Device Make')
    upload_method = models.CharField(
        max_length=256,
        choices=(
            ('MODBUS', 'MODBUS'),
            ('API', 'API'),
            ('CLIENT SW', 'CLIENT SW'),
        ),
        blank=True,
        verbose_name='Upload Method')
    process_attached = models.CharField(
        max_length=256,
        choices=(
            ('ETP', 'ETP'),
            ('STACK', 'STACK'),
            ('STP', 'STP'),
        ),
        blank=True,
        verbose_name='Process Attached')
    type = models.CharField(
        max_length=256,
        blank=True,
        choices=(
            ('GROUND WATER', 'GROUND WATER'),
            ('CAAQMS', 'CAAQMS'),
            ('CEMS', 'CEMS'),
            ('ASH', 'ASH'),
            ('GPS', 'GPS'),
            ('ANALYZER', 'ANALYZER'),
            ('CAMERA', 'CAMERA'),
        ),
        verbose_name='Type')
    system_certified = models.BooleanField(
        max_length=256,
        blank=True,
        verbose_name='System Certified')
    frequency = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Frequency')
    manufacture = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Manufacture')
    model = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Model')
    serial_no = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Serial No.')
    description = models.TextField(
        blank=True,
        verbose_name='Description')
    oem_vendor = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='OEM Vendor')


class Maintenance(models.Model):
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        db_index=True
    )
    parameter = models.ForeignKey(
        Parameter,
        on_delete=models.CASCADE,
    )
    start_date = models.DateField(default=django.utils.timezone.now,
                                  blank=True,
                                  verbose_name='Start Date')
    end_date = models.DateField(default=django.utils.timezone.now,
                                blank=True,
                                verbose_name='End Date')
    send_to_pcb = models.ForeignKey(PCB,
                                    on_delete=models.CASCADE,
                                    verbose_name='Send To')
    comments = models.TextField()


##############################################################################

class Calibration(models.Model):
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        db_index=True
    )
    name = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Calibration Name')
    calibrator = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Calibrator')
    monitoring_label = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Monitoring Label')
    parameter = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Parameter Name')
    analyzer = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Analyzer')
    start_time = models.DateTimeField(
        blank=True,
        verbose_name='Start Time'
    )
    frequency = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Frequecny')
    frequency_time = models.TimeField(
        blank=True,
        verbose_name='Frequency Time')


class Diagnostic(models.Model):
    station = models.ForeignKey(Station,
                                null=True,
                                on_delete=models.CASCADE,
                                db_index=True
                                )
    timestamp = models.DateTimeField(auto_now_add=True,
                                     blank=True)
    no_signal = models.BooleanField(default=True,
                                    verbose_name='FAULT ALARM:No Signal (No '
                                                 'signal from spectograph)')
    light_high = models.BooleanField(default=True,
                                     verbose_name='FAULT ALARM:Light Too High'
                                                  '(Bubble inside the flow'
                                                  ' cell or No sample)')
    light_low = models.BooleanField(default=True,
                                    verbose_name='FAULT ALARM:Light Too '
                                                 'High(Deposit or dirty on '
                                                 'the flow cell)')
    maintenance = models.BooleanField(default=True,
                                       verbose_name='Maintenance Status')
    cleaning = models.BooleanField(default=True,
                                   verbose_name='Cleaning')
    in_config = models.BooleanField(default=True,
                                    verbose_name='In Configuration')
    in_calibration = models.BooleanField(default=True,
                                         verbose_name='In Calibration')
    no_measurement = models.BooleanField(default=False,
                                         verbose_name='No Measurement'
                                                      ' Available')
    sample_mode = models.BooleanField(default=True, verbose_name='Sample Mode')

    def __str__(self):
        return self.station.name