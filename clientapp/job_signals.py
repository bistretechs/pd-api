"""
Signal handlers for Job-related automations
- Job assignment notifications
- Email templates
- Activity logging
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import Job, ActivityLog

import logging
logger = logging.getLogger(__name__)


@receiver(post_save, sender=Job)
def notify_pt_on_job_assignment(sender, instance, created, update_fields, **kwargs):
    """
    Send email notification when job assigned to PT user (person_in_charge)
    Triggered when:
    - person_in_charge field changes
    - Job status changes to 'assigned'
    """
    
    # Check if this is an update (not creation)
    if created:
        return
    
    # Only process if person_in_charge or status changed
    if update_fields and not ('person_in_charge' in update_fields or 'status' in update_fields):
        return
    
    # Only send if person_in_charge is set
    if not instance.person_in_charge:
        return
    
    # Get PT user
    pt_user = instance.person_in_charge
    
    # Only send if user has email
    if not pt_user.email:
        return
    
    try:
        # Prepare email context
        context = {
            'user_first_name': pt_user.first_name or 'Team Member',
            'job_number': instance.job_number or 'New Job',
            'job_name': instance.job_name,
            'client_name': (instance.client.company or instance.client.name) if instance.client else 'Unknown Client',
            'due_date': instance.expected_completion.strftime('%B %d, %Y') if instance.expected_completion else 'TBD',
            'priority': instance.get_priority_display().upper(),
            'job_url': f"{settings.SITE_URL}/job/{instance.id}/" if hasattr(settings, 'SITE_URL') else f"http://localhost:8000/job/{instance.id}/",
            'product_summary': instance.product or 'Production Required',
            'assignment_date': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
        }
        
        # Render email template
        subject = f"🎯 New Job Assigned: {instance.job_number} - {instance.job_name}"
        try:
            html_message = render_to_string('emails/job_assignment_notification.html', context)
        except Exception as template_error:
            logger.warning(f"Email template not found, using plain text: {template_error}")
            html_message = f"""
            <html>
                <body>
                    <h2>New Job Assigned</h2>
                    <p>Hi {context['user_first_name']},</p>
                    <p>A new job has been assigned to you:</p>
                    <ul>
                        <li><strong>Job Number:</strong> {context['job_number']}</li>
                        <li><strong>Job Name:</strong> {context['job_name']}</li>
                        <li><strong>Client:</strong> {context['client_name']}</li>
                        <li><strong>Due Date:</strong> {context['due_date']}</li>
                        <li><strong>Priority:</strong> {context['priority']}</li>
                    </ul>
                    <p><a href="{context['job_url']}">View Job Details</a></p>
                </body>
            </html>
            """
        
        # Send email
        send_mail(
            subject,
            f"New job {instance.job_number} assigned to you. Check {context['job_url']} for details.",
            settings.DEFAULT_FROM_EMAIL,
            [pt_user.email],
            html_message=html_message,
            fail_silently=True,
        )
        
        logger.info(f"Job assignment notification sent to {pt_user.email} for job {instance.job_number}")
        
        # Create activity log
        try:
            ActivityLog.objects.create(
                client=instance.client,
                activity_type="Job",
                title=f"Job {instance.job_number} Assigned",
                description=f"Job assigned to {pt_user.get_full_name() or pt_user.username}",
                created_by=pt_user,
            )
        except Exception as log_error:
            logger.warning(f"Could not create activity log: {log_error}")
            
    except Exception as e:
        # Log error but don't break the save operation
        logger.error(f"Error sending job assignment email: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
