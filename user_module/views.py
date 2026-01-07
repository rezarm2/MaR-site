from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import generics
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from utils.util.util import send_reset_password_email
from .models import User
from rest_framework.response import Response
from rest_framework import status
from .serializers import ChangePasswordSerializer, RegisterSerializer, LoginSerializer, UserProfileSerializer, \
    ForgetPasswordSerializer, ResetPasswordSerializer, UserInfoSerializer


# Create your views here.


class UserProfileAPIView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'user': request.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": 1, "message": "Password changed successfully."}, status.HTTP_200_OK)


class RegisterAPIView(APIView):

    def post(self, request):
        User = get_user_model()
        email = request.data.get('email')
        if User.objects.filter(email=email, is_active=False, activation_code_expiration__lt=timezone.now()).exists():
            User.objects.filter(email=email, is_active=False, activation_code_expiration__lt=timezone.now()).delete()
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'message': 'Registration was successful. Please check your email to continue the registration process and activate your account.',
            'user': {
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
            }
        }, status.HTTP_201_CREATED)


class ActivateUserAPIView(APIView):
    def get(self, request, activation_code):
        try:
            user = User.objects.get(activation_code=activation_code)
        except User.DoesNotExist:
            return Response({"detail": "The activation code is not valid."}, status=status.HTTP_400_BAD_REQUEST)

        if user.activation_code_expiration and timezone.now() > user.activation_code_expiration:
            return Response({"detail": "The activation code has expired."}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_active:
            return Response({"detail": "The account has already been activated."}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.activation_code = None
        user.activation_code_expiration = None
        user.save()

        return Response({"success": 1, "detail": "The account was successfully activated."}, status=status.HTTP_200_OK)


def activate_user_redirect(request, activation_code):
    api_views = ActivateUserAPIView()
    response = api_views.get(request, activation_code)

    if response.status_code == status.HTTP_200_OK and response.data.get("success") == 1:
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/activate?code={activation_code}")
    else:
        error_message = response.data.get("detail", "Activation failed.")
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/activate?error={error_message}")


class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        response = Response({
            "success": 1,
            "refresh": str(refresh),
            "access": access_token,
        }, status=status.HTTP_200_OK)

        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=True,
            samesite='Lax'
        )

        return response


class RefreshTokenView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({'error': 'Refresh token not found in cookies.'}, status=400)

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)

            response = Response({'success': 1}, status=200)
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=300
            )
            return response
        except TokenError:
            return Response({'error': 'Invalid refresh token.'}, status=401)


class ForgetPasswordAPIView(APIView):
    def post(self, request):
        serializer = ForgetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        User = get_user_model()
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        if not user.is_active:
            return Response({'error': 'No user with the entered details was found.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user.activation_code = get_random_string(length=72)
        user.activation_code_expiration = timezone.now() + timedelta(hours=24)
        user.save()
        send_reset_password_email(user)

        return Response({"success": 1,
                         'detail': 'Password recovery email sent.',
                         'activation_code': user.activation_code
                         }, status=status.HTTP_200_OK)


class ResetPasswordAPIView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request, activation_code):
        User = get_user_model()
        try:
            user = User.objects.get(activation_code=activation_code)
        except User.DoesNotExist:
            return Response({'error': 'The activation code is not valid.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.activation_code_expiration < timezone.now():
            return Response({'error': 'The activation code has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data, context={'activation_code': activation_code})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"success": 1, 'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)


def reset_password_redirect(request, activation_code):
    User = get_user_model()
    try:
        user = User.objects.get(activation_code=activation_code)
    except User.DoesNotExist:
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/reset-password?error=The activation code is not valid.")

    if user.activation_code_expiration < timezone.now():
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/reset-password?error=The activation code has expired.")

    return HttpResponseRedirect(f"{settings.FRONTEND_URL}/reset-password?code={activation_code}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info_view(request):
    serializer = UserInfoSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    response = Response({"success": 1, 'message': 'Logged out successfully'}, status=200)
    response.set_cookie(
        key='access_token',
        value='',
        max_age=0,
        expires='Thu, 01 Jan 1970 00:00:00 GMT',
        path='/',
        secure=True,
        httponly=True,
        samesite='None'
    )

    response.set_cookie(
        key='refresh_token',
        value='',
        max_age=0,
        expires='Thu, 01 Jan 1970 00:00:00 GMT',
        path='/',
        secure=True,
        httponly=True,
        samesite='None'
    )
    return response
