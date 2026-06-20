import datetime
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from api.serializers import ServiceSerializer, EmployeeSerializer
from rest_framework.response import Response
from rest_framework import status

from services.models import Service, Employee
from bookings.utils import get_available_slots


class ServiceListView(ListAPIView):
    queryset = Service.objects.all().order_by('category', 'name')
    serializer_class = ServiceSerializer


class EmployeeListView(ListAPIView):
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        service_id = self.request.query_params.get('service')
        if service_id:
            return Employee.objects.filter(services__id=service_id).order_by('first_name')
        return Employee.objects.all().order_by('first_name')
    

class AvailableSlots(APIView):
    def get(self, request, format=None):
        date_str = request.query_params.get('date')
        employee_id = request.query_params.get('employee')
        service_id = request.query_params.get('service')
        if not date_str or not service_id:
            return Response({'slots': [], 'error': 'Missing date or service_id parameter'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = Service.objects.get(id=service_id)
            date = datetime.date.fromisoformat(date_str)
        except (Service.DoesNotExist, ValueError):
            return Response({'slots': [], 'error': 'Nieprawidłowe dane.'}, status=status.HTTP_400_BAD_REQUEST)

        if date < datetime.date.today():
            return Response({'slots': [], 'error': 'Cannot book appointments in the past.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if employee_id:
            try:
                employee = service.employees.get(id=employee_id)
                slots = get_available_slots(employee, date, service)
            except Employee.DoesNotExist:
                return Response({'slots': [], 'error': 'Employee not found for this service.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            candidates = service.employees.all()
            slots_set = set()
            for employee in candidates:
                slots_set.update(get_available_slots(employee, date, service))
            slots = sorted(slots_set)
        
        
        return Response({'slots': [s.strftime('%H:%M') for s in slots]})