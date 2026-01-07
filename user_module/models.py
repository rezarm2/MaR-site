from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.crypto import get_random_string


class User(AbstractUser):
    avatar = models.ImageField(upload_to='images/profile', verbose_name='تصویر', null=True, blank=True)
    activation_code = models.CharField(max_length=100, blank=True, null=True)
    activation_code_expiration = models.DateTimeField(null=True, blank=True)
    about_user = models.TextField(null=True, blank=True, verbose_name='درباره شخص')
    address = models.TextField(null=True, blank=True, verbose_name='آدرس')
    phone_number = models.CharField(null=False, blank=False, default='09100000000')

    def save(self, *args, **kwargs):
        if not self.activation_code:
            self.activation_code = get_random_string(length=72)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        if self.first_name and self.last_name:
            return self.get_full_name()
        return self.email


# training------------------------------------------------------

class LeaveRequest(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('SICK', 'Sick Leave'),
        ('ANNUAL', 'Annual Leave'),
        ('UNPAID', 'Unpaid Leave'),
    ]

    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=10, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Course(models.Model):
    title = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    max_students = models.PositiveIntegerField()
    students_count = models.PositiveIntegerField(default=0)


class CourseRegistration(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)
