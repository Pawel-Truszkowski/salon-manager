from django.shortcuts import render

from services.models import Employee, Service



def home(request):
    employees = Employee.objects.all()
    services = Service.objects.all()
    return render(request, 'home.html', {'employees': employees, 'services': services})
