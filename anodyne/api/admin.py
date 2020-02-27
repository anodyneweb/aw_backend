from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Station, Industry, State, PCB, City


class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('email', 'admin')
    list_filter = ('admin',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ()}),
        ('Permissions', {'fields': ('admin',)}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name',
                       'password1', 'password2', 'type', 'site',
                       'phone', 'address', 'zipcode')}
         ),
    )
    search_fields = ('email',)
    ordering = ('email', 'name')
    filter_horizontal = ()


admin.site.register(User, UserAdmin)
admin.site.register(Industry)
admin.site.register(Station)
admin.site.register(PCB)
admin.site.register(State)
admin.site.register(City)
# Remove Group Model from admin. We're not using it.
admin.site.unregister(Group)
