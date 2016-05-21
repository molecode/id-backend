from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from django.http import JsonResponse

from .models import Notification, NotificationSubscription, AuditLog
from .models import channel_components, notification_channel_format
from .serializers import NotificationSerializer, AuditLogSerializer
from .mixins import NotificationMixin


class NotificationSeen(APIView):
    permission_classes = (IsAuthenticated, )

    def get(self, request, *args, **kwargs):
        nid = kwargs.get('pk')
        if nid == "all":
            nots = Notification.objects.filter(user=request.user)
            for n in nots:
                n.seen()
            return JsonResponse({
                "action": "seen",
                "notifications": [n.id for n in nots],
                "unseen_count": Notification.objects.filter(user=request.user, is_seen=False).count()
            })
        else:
            try:
                notification = Notification.objects.get(
                    pk=nid,
                    user=request.user
                )
            except Exception, e:
                return JsonResponse({"error": str(e)})

            notification.seen()
            return JsonResponse({
                "action": "seen",
                "notifications": [notification.id],
                "unseen_count": Notification.objects.filter(user=request.user, is_seen=False).count()
            })


class NotificationStream(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-timestamp")

class NotificationSubscriptions(APIView):
    # TODO: Needs security
    permission_classes = (IsAuthenticated, )

    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'notification_subscriptions': [x.channel for x in request.user.notificationsubscription_set.all()]
        })

    def put(self, request, *args, **kwargs):
        channel = request.data.get('channel')
        try:
            request.user.notifications_subscribe(channel)
            return JsonResponse({'result': 'subscribed'})
        except AssertionError, e:
            j = JsonResponse({
                'error': 'invalid channel format.',
                'format_hint': 'app:module:model:instance:action'})
            j.status_code = 400
            return j
        except TypeError, e:
            j = JsonResponse({
                'error': 'you must supply a channel',
                'params': request.data,
            })
            j.status_code = 400
            return j

    def delete(self, request, *args, **kwargs):
        channel = request.data.get('channel')
        try:
            cnt = request.user.notifications_unsubscribe(channel)
            if cnt == 0:
                return JsonResponse({'result': 'none', 'found': 0})
            else:
                return JsonResponse({'result': 'unsubscribed', 'found': cnt})
        except AssertionError, e:
            j = JsonResponse({'error': 'invalid channel format'})
            j.status_code = 400
            return j
        except TypeError, e:
            j = JsonResponse({
                'error': 'you must supply a channel',
                'params': request.data,
            })
            j.status_code=418
            return j


class Notify(NotificationMixin, APIView):
    def post(self, request, *args, **kwargs):
        if not request.auth:
            j = JsonResponse({"error": "no valid oauth token"})
            j.status_code = 403
            return j

        channel = request.data.get('channel')
        if not notification_channel_format.match(channel):
            j = JsonResponse({'error': 'invalid channel format'})
            j.status_code = 400
            return j

        components = channel_components(channel)
        if components['app'] != request.auth.application.name:
            j = JsonResponse({
                'error': 'invalid application name',
                'got': components['app'],
                'expected': request.auth.application.name
            })
            j.status_code = 409
            return j

        text = request.data.get('text', None)
        if not text:
            j = JsonResponse({'error': 'no text provided'})
            j.status_code = 400
            return j
        url = request.data.get('url', None)

        self.notify_channel(channel=channel, text=text, user=request.user, url=url)
        return JsonResponse({
            'result': 'sent',
            'channel': channel,
            'text': text,
            'url': url
        })

class AuditLogView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = (IsAdminUser, )

    def get_queryset(self):
        filter_terms = ["user", "level", "module", "filename", "lineno",
                        "funcname", "message", "process",
                        "thread", "ip", "timestamp"]

        filters = {}
        for i in filter_terms:
            filters[i] = self.request.data.get(i, None)
            if not filters[i]:
                del filters[i]

        if 'user' in filters:
            filters['user__email'] = filters['user']
            del filters['user']

        audits = AuditLog.objects.filter(**filters).order_by('-timestamp')

        return audits
