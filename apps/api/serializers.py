from rest_framework import serializers
from apps.services.models import ServiceCategory, Service, Employee, Schedule
from apps.bookings.models import Appointment


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'slug']


class ServiceSerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    class Meta:
        model = Service
        fields = ['id', 'name', 'category', 'description', 'price', 'duration']
        

class EmployeeSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)
    class Meta:
        model = Employee
        fields = ['id', 'first_name', 'last_name', 'email', 'bio', 'services']
        

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ['id', 'employee', 'date', 'start_time', 'end_time']


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'id', 'service', 'employee', 'date_time', 'status',
            'client_name', 'client_email', 'client_phone', 'notes'
        ]        
        

