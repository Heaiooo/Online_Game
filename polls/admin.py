from django.contrib import admin
from django.contrib.sessions.models import Session


class SessionAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'expire_date', 'get_decoded']


admin.site.register(Session, SessionAdmin)