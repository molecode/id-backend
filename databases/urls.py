from core.auth import perm
from django.conf.urls import url

from .views import ExternalDatabaseList, DatabaseRequest


urlpatterns = [
    url(r'^$', perm('any', ExternalDatabaseList), name='externaldb_list'),
    url(r'register$', perm('staff', DatabaseRequest), name='database_register'),
    url(r'edit/(?P<db_id>\d+)$', perm('staff', DatabaseRequest), name='database_register'),
]
