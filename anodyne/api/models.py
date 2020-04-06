# Create your models here.
import json
import logging
import uuid as uuid

import django.utils.timezone
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.db.models.signals import post_save

from api.GLOBAL import STATES, CITIES, USER_CHOICES, CATEGORIES, PCB_CHOICES, \
    UNIT
from django.contrib.postgres.fields import CICharField

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
    unit = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.unit


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.name


class PCB(models.Model):
    name = models.CharField(max_length=256, unique=True)
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
    active = models.BooleanField(default=True)
    staff = models.BooleanField(default=False)  # a staff;
    admin = models.BooleanField(default=False)  # a admin
    created = models.DateTimeField(default=django.utils.timezone.now,
                                   blank=True, editable=False,
                                   verbose_name='Joined On')
    # notice the absence of a "Password field", that's built in.

    # USER DETAILS STARTS
    name = models.CharField(max_length=60, null=False, verbose_name='Name',
                            default='')
    phone = models.CharField(max_length=10, null=True)
    type = models.CharField(max_length=20, null=False, choices=USER_CHOICES,
                            default='ADMIN')
    address = models.TextField(default=None, null=True)
    zipcode = models.IntegerField(default=None, null=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE,
                              to_field='name', null=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)
    country = models.CharField(max_length=80, default='India', editable=False)
    # USER DETAILS ENDS

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'type']

    def get_full_name(self):
        # The user is identified by their email address
        return self.email

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
    dir = models.CharField(
        max_length=50,
        null=False,
        blank=False,
        editable=False,
        verbose_name='Data File Directory Name'
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
        verbose_name='Industry Id',
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

    class Meta:
        default_permissions = ()

    def __str__(self):
        return str(self.name)


class Station(models.Model):
    MPCB = 'MPCB'
    MPPCB = 'MPPCB'
    KSPCB = 'KSPCB'
    OSPCB = 'OSPCB'
    CPCB = 'CPCB'
    RSPCB = 'RSPCB'
    HSPCB = 'HSPCB'
    WBPCB = 'WBPCB'
    PPCB = 'PPCB'
    DJB = 'DJB'
    UKPCB = 'UKPCB'
    DPCC = 'DPCC'
    JSPCB = 'JSPCB'
    BSPCB = 'BSPCB'

    ATTACHED_CHOICES = (
        ('Inlet', 'Inlet'),
        ('Outlet', 'Outlet'),
    )
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
                               verbose_name='StationID/StationID',
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
                              verbose_name='File Prefix', db_index=True)

    version = models.CharField(max_length=10, default='ver_1.0',
                               verbose_name='PCB Software Version',
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
                                  blank=True)
    user_ph = models.TextField(max_length=255, default=None, null=True,
                               verbose_name='Customer Alert Contact',
                               blank=True)
    is_cpcb = models.BooleanField(default=False, verbose_name='Is CPCB',
                                  blank=True)
    # emails/phone to CPCB only if notify_cpcb is enabled
    notify_cpcb = models.BooleanField(default=True, verbose_name='Notify CPCB',
                                      blank=True)
    cpcb_email = models.TextField(max_length=255, default=None, null=True,
                                  verbose_name='CPCB Alert Email',
                                  blank=True)
    cpcb_ph = models.TextField(max_length=255, default=None, null=True,
                               verbose_name='CPCB Alert Contacts',
                               blank=True)
    closure_status = models.CharField(max_length=20, choices=CLOSURE_CHOICES,
                                      default=None,
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
                                     default=django.utils.timezone.now,
                                     blank=True)

    amc = models.DateTimeField(blank=True, null=True,
                               default=None, verbose_name='AMC')
    cmc = models.DateTimeField(blank=True, null=True,
                               default=None, verbose_name='CMC')
    active = models.BooleanField(default=True, verbose_name='Active/Blocked')
    created = models.DateTimeField(auto_now_add=True, blank=True)

    def __str__(self):
        return "%s | %s | %s | %s" % (self.name, self.industry.name,
                                      self.pcb, self.state)

    def save(self, *args, **kwargs):
        if self.pcb.name not in [Station.KSPCB, Station.MPCB, Station.RSPCB,
                            Station.OSPCB,
                            Station.MPPCB]:
            self.key = self.pub_key = None

        elif self.pcb.name == Station.MPCB:  # needs only key
            self.pub_key = None

        elif self.pcb.name == Station.RSPCB:  # this needs site id
            self.key = self.pub_key = None

        elif self.pcb.name == Station.OSPCB:  # this needs token to connect
            self.pub_key = None

        super(Station, self).save(*args, **kwargs)


class StationInfo(models.Model):
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
    name = CICharField(max_length=80, default=None, unique=True)
    unit = models.CharField(max_length=50, default=None, choices=UNIT,
                            null=True)
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
        on_delete=models.CASCADE
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
    allowed = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )

    class Meta:
        unique_together = (('station', 'parameter'),)

    def __str__(self):
        return '%s: %s' % (self.station.name, self.parameter)


class Reading(models.Model):
    station = models.ForeignKey(Station, null=True, to_field='prefix',
                             on_delete=models.CASCADE, db_index=True)
    reading = HStoreField(max_length=1024, blank=True)

    class Meta:
        unique_together = (('reading', 'station'),)

    def __str__(self):
        return "%s: %s" % (self.station, self.reading)


class Registration(models.Model):
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True
    )
    fname = models.CharField(
        max_length=120, verbose_name='First Name',
    )
    lname = models.CharField(
        max_length=120,
        verbose_name='Last Name',
        blank=True
    )
    phone = models.CharField(
        max_length=120,
    )
    industry = models.CharField(
        max_length=120,
        blank=True
    )
    query = models.TextField(
        default=None,
        blank=True
    )


# class ReadingJSON(models.Model):
#     station = models.ForeignKey(
#         Station,
#         on_delete=models.CASCADE
#     )
#     # {'param1': 'val1', 'param2': 'val2'...}
#     reading = JSONField(
#         max_length=9999,
#         blank=True
#     )
#     timestamp = models.DateTimeField(
#         db_index=True,
#         auto_now_add=True,
#         blank=True
#     )
#     filename = models.CharField(
#         max_length=80
#     )
#
#     class Meta:
#         unique_together = (('timestamp', 'filename'),)
#
#     def __str__(self):
#         return "%s: \n %s" % (self.station.name, self.reading)

##############################################################################
# SIGNALS
post_save.connect(Parameter.check4new, sender=StationParameter)
