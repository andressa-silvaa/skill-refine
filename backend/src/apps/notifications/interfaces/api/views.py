"""Notifications API views."""
from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api.responses import error_response as _error

from apps.notifications.models import Notification

from .payloads import notification_payload


def _user_id(request):
    uid = getattr(request.user, "id", None)
    if not uid:
        return None, _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)
    return str(uid), None


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id, err = _user_id(request)
        if err:
            return err
        limit = min(max(int(request.query_params.get("limit", 20)), 1), 100)
        offset = max(int(request.query_params.get("offset", 0)), 0)
        qs = Notification.objects.filter(user_id=user_id).order_by("-created_at")
        total = qs.count()
        page = list(qs[offset : offset + limit])
        return Response(
            {
                "items": [notification_payload(n) for n in page],
                "limit": limit,
                "offset": offset,
                "total": total,
                "hasNext": offset + limit < total,
                "nextOffset": offset + limit if offset + limit < total else None,
            },
            status=status.HTTP_200_OK,
        )


class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id, err = _user_id(request)
        if err:
            return err
        count = Notification.objects.filter(user_id=user_id, is_read=False).count()
        return Response({"count": count}, status=status.HTTP_200_OK)


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_id):
        user_id, err = _user_id(request)
        if err:
            return err
        updated = Notification.objects.filter(
            id=notification_id,
            user_id=user_id,
        ).update(is_read=True)
        if not updated:
            return _error("not_found", "Notificação não encontrada.", status.HTTP_404_NOT_FOUND)
        return Response({"ok": True}, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id, err = _user_id(request)
        if err:
            return err
        Notification.objects.filter(user_id=user_id, is_read=False).update(is_read=True)
        return Response({"ok": True}, status=status.HTTP_200_OK)


class NotificationDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, notification_id):
        user_id, err = _user_id(request)
        if err:
            return err
        deleted, _ = Notification.objects.filter(
            id=notification_id,
            user_id=user_id,
        ).delete()
        if not deleted:
            return _error("not_found", "Notificação não encontrada.", status.HTTP_404_NOT_FOUND)
        return Response({"ok": True}, status=status.HTTP_200_OK)


class NotificationClearAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user_id, err = _user_id(request)
        if err:
            return err
        count, _ = Notification.objects.filter(user_id=user_id).delete()
        return Response({"ok": True, "deleted": count}, status=status.HTTP_200_OK)
