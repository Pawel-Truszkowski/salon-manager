from rest_framework.generics import ListAPIView
from services.models import Service
from api.serializers import ServiceSerializer


class ServiceListView(ListAPIView):
    queryset = Service.objects.all().order_by('category', 'name')
    serializer_class = ServiceSerializer
