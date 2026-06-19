from django.db import models


class ServiceCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "Service Categories"
    
    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in minutes")

    def __str__(self):
        return self.name


class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    bio = models.TextField()
    services = models.ManyToManyField(Service, related_name='employees')
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
   
 
class Schedule(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ('employee', 'date', 'start_time')

    def __str__(self):
        return f"{self.employee} - {self.date} {self.start_time}-{self.end_time}"
    
