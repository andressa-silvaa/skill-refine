from rest_framework.response import Response
from rest_framework.views import APIView


class HealthcheckView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, *_args, **_kwargs):
        return Response({"status": "ok"})


