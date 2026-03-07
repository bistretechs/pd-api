import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'client.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("=" * 60)
print("Testing Email Configuration")
print("=" * 60)
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print("=" * 60)

test_email = input("Enter test recipient email address: ").strip()

if not test_email:
    print("No email provided. Exiting.")
    exit(1)

print(f"\nSending test email to: {test_email}")

try:
    result = send_mail(
        subject='Test Email from PrintDuka',
        message='This is a test email to verify email configuration is working correctly.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[test_email],
        html_message='<h1>Test Email</h1><p>This is a test email to verify email configuration is working correctly.</p>',
        fail_silently=False,
    )
    print(f"\n✅ Email sent successfully! Result: {result}")
    print("Check your inbox (and spam folder) for the test email.")
except Exception as e:
    print(f"\n❌ Failed to send email!")
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
