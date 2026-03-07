import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'client.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

print("=" * 60)
print("Testing Staff Invite Email")
print("=" * 60)

test_email = input("Enter test recipient email address: ").strip()

if not test_email:
    print("No email provided. Exiting.")
    exit(1)

context = {
    'first_name': 'Peter',
    'admin_name': 'Collins Tonui',
    'activation_link': 'http://localhost:3000/activate?token=test123',
    'group_names': 'Production Team',
    'company_name': 'PrintDuka',
}

html_message = render_to_string('emails/staff_invite.html', context)
plain_message = strip_tags(html_message)

print(f"\nSending test invite email to: {test_email}")

try:
    result = send_mail(
        subject=f"You've been invited to join {context['company_name']} Staff Portal",
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[test_email],
        html_message=html_message,
        fail_silently=False,
    )
    print(f"\n✅ Email sent successfully! Result: {result}")
    print("Check your inbox (and spam folder) for the invite email.")
except Exception as e:
    print(f"\n❌ Failed to send email!")
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
