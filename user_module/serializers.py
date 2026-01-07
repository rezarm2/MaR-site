import re
from datetime import timedelta
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from utils.util.util import validate_password_strength, validate_unique_field, send_activation_email
from .models import User, LeaveRequest, CourseRegistration


class UserProfileSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'role']

    def get_role(self, obj):
        return "admin" if obj.is_staff else "user"

    def validate_email(self, value):
        user = self.instance
        if value != user.email:
            if User.objects.filter(email=value).exclude(id=user.id).exists():
                raise serializers.ValidationError("This email has already been registered.")
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", value):
            raise serializers.ValidationError("The email format is not valid.")
        return value

    def validate_username(self, value):
        user = self.instance
        if value != user.username:
            if User.objects.filter(username=value).exclude(id=user.id).exists():
                raise serializers.ValidationError("This username has already been used.")
        return value

    def validate_phone_number(self, value):
        user = self.instance
        if value != user.phone_number:
            if User.objects.filter(phone_number=value).exclude(id=user.id).exists():
                raise serializers.ValidationError("This phone number is already registered.")
        if not re.fullmatch(r"^09\d{9}$", str(value)):
            raise serializers.ValidationError("The number must be 11 digits and start with 09.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("The password must be at least 8 characters long.")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("It must have at least one number.")
        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError("It must have at least one letter.")
        return value

    def save(self):
        user = self.context['user']
        old_password = self.initial_data['old_password']
        new_password = self.initial_data['new_password']

        if not user.check_password(old_password):
            raise serializers.ValidationError("The old password is incorrect.")

        if user.check_password(new_password):
            raise serializers.ValidationError("The new password cannot be the same as the old password.")

        user.set_password(new_password)
        user.save()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'password']

    def validate_email(self, value):
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", value):
            raise serializers.ValidationError("The email format is not valid.")
        if not value:
            raise serializers.ValidationError("Email must be entered.")
        return validate_unique_field(User, "email", value)

    def validate_phone_number(self, value):
        if not re.fullmatch(r"^09\d{9}$", str(value)):
            raise serializers.ValidationError("The number must be 11 digits and start with 09.")
        if not value:
            raise serializers.ValidationError("A phone number must be entered.")
        return validate_unique_field(User, "phone_number", value)

    def validate_username(self, value):
        if not value:
            raise serializers.ValidationError("Username must be entered.")
        return validate_unique_field(User, "username", value)

    def validate_password(self, value):
        try:
            return validate_password_strength(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.is_active = False
        user.activation_code = get_random_string(length=72)
        user.activation_code_expiration = timezone.now() + timedelta(hours=24)
        user.save()
        send_activation_email(user)
        return user


class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username_or_email = attrs.get('username_or_email')
        password = attrs.get('password')

        user = authenticate(username=username_or_email, password=password)
        if user is None:
            User = get_user_model()
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if not user:
            raise serializers.ValidationError("The username/email or password is incorrect.")

        attrs['user'] = user
        return attrs


class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        User = get_user_model()
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError('No user with this email was found.')
        return value


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        if password != password_confirm:
            raise serializers.ValidationError('The password and its repetition are not the same.')

        validate_password_strength(password)

        return attrs

    def save(self, **kwargs):
        User = get_user_model()
        activation_code = self.context.get('activation_code')
        try:
            user = User.objects.get(activation_code=activation_code)
        except User.DoesNotExist:
            raise serializers.ValidationError('The activation code is not valid.')

        if user.activation_code_expiration and timezone.now() > user.activation_code_expiration:
            return Response({"detail": "The activation code has expired."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(self.validated_data['password'])
        user.activation_code = None
        user.activation_code_expiration = None
        user.save()

        return user


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


##////////////////////////////////////////////////////////////////////////////////////////////////

# class CommentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Comment
#         fields = ['id', 'created_at', 'auther', 'text']
#         read_only_fields = ['auther', 'created_at']
#
#     def validate_text(self, text):
#         if len(text) < 15:
#             raise serializers.ValidationError({'error': 'Text must be at least 15 characters.'})
#         return text
#
#     def create(self, validated_data):
#         validated_data['auther'] = self.context['request'].user
#         return Comment.objects.create(**validated_data)
#


# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ['username', 'is_staff', 'date_joined', 'email', 'bio']
#         read_only_fields = ['username', 'is_staff', 'date_joined', 'email']
#
#     def create_or_update(self, validated_data):
#         validated_data['username'] = self.context['request'].user
#         return User.objects.create(**validated_data)


class Discount:
    pass


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = ['code', 'percent', 'start_date', 'end_date', 'is_active']

    def validate(self, attrs):
        if attrs.get['percent'] >= 90:
            raise serializers.ValidationError({'percent': 'percent must be less than 90'})
        if attrs.get['start_date'] > attrs.get['end_date']:
            raise serializers.ValidationError({'start_date': 'start date must be before end date'})
        if attrs.get['end_date'] >= attrs.get['end_date']:
            discount = Discount
            discount.is_active = False

        if 'code' or 'start_date' in attrs:
            raise serializers.ValidationError({'detail': 'These fields cannot be changed.'})

        return attrs

    def update(self, instance, validated_data):
        instance.end_date = validated_data.get('end_date', instance.end_date)
        instance.percent = validated_data.get('percent', instance.percent)
        instance.is_active = validated_data.get('is_active', instance.is_active)

        if 'code' or 'start_date' in validated_data:
            raise serializers.ValidationError({'detail': 'These fields cannot be changed.'})
        instance.save()
        return instance

        # def validate(self, attrs):
    #     if attrs.get('percent') >= 90:
    #         raise serializers.ValidationError({'percent': 'Percent must be less than or equal to 90.'})
    #
    #     if attrs.get('start_date') > attrs.get('end_date'):
    #         raise serializers.ValidationError({'start_date': 'Start date cannot be after end date.'})
    #     return attrs
    #
    # def update(self, instance, validated_data):
    #     instance.percent = validated_data.get('percent', instance.percent)
    #     instance.end_date = validated_data.get('end_date', instance.end_date)
    #
    #     if 'start_date' in validated_data:
    #         raise serializers.ValidationError({'star_date': 'Start date cannot be changed'})
    #     if 'code' in validated_data:
    #         raise serializers.ValidationError({'code': 'code cannot be changed'})
    #
    #     instance.save()
    #     return instance


class Subscription:
    pass


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['plan_name', 'discount', 'start_date', 'end_date', 'is_active']
        read_only_fields = ['plan_name']

    def validate(self, attrs):
        if attrs.get('discount') > 70:
            raise serializers.ValidationError({'discount': 'discount must be litten than 70'})

        if attrs.get('start_date') and attrs.get('end_date') and attrs.get('start_date') >= attrs.get('end_date'):
            raise serializers.ValidationError({'start_date': 'Start date cannot be after end date.'})

        if attrs.get('end_date') and attrs['end_date'] < timezone.now().date():
            attrs['is_active'] = False

        return attrs

    def update(self, instance, validated_data):
        if 'plan_name' in validated_data:
            raise serializers.ValidationError({'plan_name': 'you cannot change plan_name'})

        instance.end_date = validated_data.get('end_date', instance.end_date)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.start_date = validated_data.get('start_date', instance.start_date)
        instance.discount = validated_data.get('discount', instance.discount)

        instance.save()
        return instance


class Review:
    pass


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['created_at', 'user', 'comment', 'rate']
        read_only_fields = ['user', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return Review.objects.create(**validated_data)


class OrderItem:
    pass


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['order', 'product', 'quantity']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get('product'):
            raise serializers.ValidationError({'product': 'the product is not defined'})
        if attrs.get('quantity') is None or attrs.get('quantity') <= 0:
            raise serializers.ValidationError({'quantity': 'this product cannot be purchased'})
        if attrs.get('product').stock < attrs.get('quantity'):
            raise serializers.ValidationError({'quantity': 'Not enough stock available'})

        return attrs

    def update(self, instance, validated_data):
        instance.quantity = validated_data.get('quantity', instance.quantity)
        instance.save()
        return instance

    def create(self, validated_data):
        with transaction.atomic():
            order_id = self.context.get('order_id')
            if not order_id:
                raise serializers.ValidationError({'order_id': 'Order ID is required in context'})
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                raise serializers.ValidationError({'order': 'Order does not exist'})
            validated_data['order'] = order

            product = validated_data.get('product')
            if not product:
                raise serializers.ValidationError({'product': 'Product is required'})
            if product.stock < validated_data.get('quantity', 0):
                raise serializers.ValidationError({'product': 'Not enough stock available'})
            product.stock -= validated_data['quantity']
            product.save()

            return OrderItem.objects.create(**validated_data)


class Booking:
    pass


class Room:
    is_active = True


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['user', 'room', 'start_date', 'end_date', 'created_at']
        read_only_fields = ['user', 'created_at']

    def validate(self, attrs):
        if attrs.get("start_date") >= attrs.get("end_date"):
            raise serializers.ValidationError({'start_date': 'Start date cannot be greater than or equal to end date'})

        room = attrs.get('room')
        if room and not room.is_available:
            raise serializers.ValidationError({'room': 'Room is not available'})
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return Booking.objects.create(**validated_data)


class Event:
    pass


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["title", "start_time", "end_time", "max_participants", "participants_count", "is_active"]
        read_only_fields = ["participants_count", "is_active"]

    def validate(self, attrs):
        if attrs.get("start_time") >= attrs.get("end_time"):
            raise serializers.ValidationError({'start_time': 'Start time must be before end time'})
        return attrs

    def create(self, validated_data):
        # اول رویداد رو بساز
        event = Event.objects.create(**validated_data)

        # اگر زمان پایان گذشته باشه، is_active رو False کن
        if event.end_time < timezone.now():
            event.is_active = False
            event.save()

        return event


class EventRegistration:
    pass


class EventRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRegistration
        fields = ["user", "event", "registered_at"]
        read_only_fields = ["user", "registered_at"]

    def validate(self, attrs):
        user = self.context['request'].user
        event = attrs.get("event")

        if EventRegistration.objects.filter(user=user, event=event).exists():
            raise serializers.ValidationError({'user': 'You are already registered in this event.'})

        if event.end_time <= timezone.now():
            raise serializers.ValidationError({'event': 'The event has already ended.'})

        if event.participants_count >= event.max_participants:
            raise serializers.ValidationError({'event': 'Event is full. Cannot register more participants.'})

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        event = validated_data["event"]

        # افزایش تعداد شرکت‌کننده‌ها
        event.participants_count += 1
        event.save()

        return EventRegistration.objects.create(user=user, event=event)


class Appointment:
    pass


class Doctor:
    pass


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ["doctor", "patient", "appointment_time", "created_at"]
        read_only_fields = ["patient", "created_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        patient = self.context['request'].user
        doctor = attrs.get('doctor')
        appointment_time = attrs.get('appointment_time')

        if appointment_time < timezone.now():
            raise serializers.ValidationError({'appointment_time': 'Appointment time cannot be in the past.'})

        if Appointment.objects.filter(doctor=doctor, appointment_time=appointment_time).exists():
            raise serializers.ValidationError(
                {'appointment_time': 'This time is already taken for the selected doctor.'})

        if Appointment.objects.filter(patient=patient, doctor=doctor, appointment_time=appointment_time).exists():
            raise serializers.ValidationError({'non_field_errors': ['You already booked this appointment.']})

        return attrs

    def create(self, validated_data):
        validated_data['patient'] = self.context['request'].user
        return Appointment.objects.create(**validated_data)


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ['employee', 'leave_type', 'reason', 'created_at', 'start_date', 'end_date']
        read_only_fields = ['employee', 'created_at']

    def validate(self, attrs):
        attrs = super().validate(attrs)

        leave_type = attrs.get('leave_type')
        reason = attrs.get('reason')
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if start_date > end_date:
            raise serializers.ValidationError({'start_date': 'Start date cannot be after end date.'})

        if start_date < timezone.now().date():
            raise serializers.ValidationError({'start_date': 'Start date cannot be in the past.'})

        if leave_type == 'SICK' and not reason:
            raise serializers.ValidationError({'reason': 'Reason is required for sick leave.'})

        if leave_type == 'UNPAID':
            duration = (end_date - start_date).days
            if duration > 5:
                raise serializers.ValidationError({'end_date': 'Unpaid leave cannot be more than 5 days.'})

        return attrs

    def create(self, validated_data):
        validated_data['employee'] = self.context['request'].user
        return LeaveRequest.objects.create(**validated_data)


class CourseRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseRegistration
        fields = ['student', 'course', 'registered_at']
        read_only_fields = ['student', 'registered_at']

    def validate(self, attrs):
        student = self.context['request'].user
        course = attrs.get('course')

        if CourseRegistration.objects.filter(student=student, course=course).exists():
            raise serializers.ValidationError({'student': 'You are already registered for this course.'})

        if course.students_count >= course.max_students:
            raise serializers.ValidationError({'student': 'Course capacity is full.'})

        if course.end_date < timezone.now().date():
            raise serializers.ValidationError({'course': 'Course has already ended.'})

        return attrs

    def create(self, validated_data):
        validated_data['student'] = self.context['request'].user
        course = validated_data['course']
        course.students_count += 1
        course.save()

        return CourseRegistration.objects.create(**validated_data)
