"""
Vendor Notification Service
Handles all vendor-related notifications (email, SMS, push, etc)
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.conf import settings
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class VendorNotificationService:
    """
    Service to handle all vendor notifications.
    Supports: Email, SMS, Push Notifications, In-App Notifications
    """
    
    @staticmethod
    def notify_job_assignment(job_vendor_stage, vendor):
        """
        Notify vendor when job is assigned to them
        
        Args:
            job_vendor_stage: JobVendorStage instance
            vendor: Vendor instance
        """
        if not vendor.user or not vendor.user.email:
            logger.warning(f"Cannot notify vendor {vendor.name} - no user or email")
            return False
        
        try:
            job = job_vendor_stage.job
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000').rstrip('/')
            context = {
                'vendor_name': vendor.name,
                'job_number': job.job_number,
                'job_name': job.job_name,
                'job_type': job.get_job_type_display(),
                'product': job.product,
                'quantity': job.quantity,
                'expected_completion': job_vendor_stage.expected_completion,
                'priority': job.priority.upper(),
                'notes': job.notes,
                'portal_url': f'{frontend_url}/vendors/purchase-orders',
            }
            
            # Send email
            VendorNotificationService._send_email(
                recipient=vendor.user.email,
                subject=f"New Job Assignment: {job.job_number}",
                template='emails/vendor_job_assigned.html',
                context=context,
                vendor=vendor
            )
            
            # Send SMS if enabled
            if getattr(vendor, 'prefer_sms', False) and vendor.phone:
                VendorNotificationService._send_sms(
                    phone=vendor.phone,
                    message=f"New job {job.job_number} assigned. {job.job_name}. Complete by {job_vendor_stage.expected_completion.strftime('%Y-%m-%d')}"
                )
            
            # Create in-app notification
            VendorNotificationService._create_notification(
                user=vendor.user,
                notification_type='job_assigned',
                title=f"New Job: {job.job_number}",
                message=f"{job.job_name} — due {job_vendor_stage.expected_completion.strftime('%d %b %Y')}",
                related_job=job,
                action_url='/vendors/purchase-orders',
            )
            
            logger.info(f"Notified vendor {vendor.name} about job {job.job_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error notifying vendor {vendor.name}: {str(e)}")
            return False
    
    @staticmethod
    def notify_deadline_approaching(job_vendor_stage, days_remaining=1):
        """
        Notify vendor when deadline is approaching
        
        Args:
            job_vendor_stage: JobVendorStage instance
            days_remaining: Number of days until deadline
        """
        if not job_vendor_stage.vendor.user or not job_vendor_stage.vendor.user.email:
            return False
        
        try:
            job = job_vendor_stage.job
            vendor = job_vendor_stage.vendor
            
            context = {
                'vendor_name': vendor.name,
                'job_number': job.job_number,
                'job_name': job.job_name,
                'days_remaining': days_remaining,
                'expected_completion': job_vendor_stage.expected_completion,
                'progress': job_vendor_stage.progress,
            }
            
            VendorNotificationService._send_email(
                recipient=vendor.user.email,
                subject=f"Deadline Reminder: {job.job_number} due in {days_remaining} day(s)",
                template='emails/vendor_deadline_reminder.html',
                context=context,
                vendor=vendor
            )
            
            # SMS reminder
            if getattr(vendor, 'prefer_sms', False) and vendor.phone:
                VendorNotificationService._send_sms(
                    phone=vendor.phone,
                    message=f"Reminder: Job {job.job_number} due in {days_remaining} day(s). Progress: {job_vendor_stage.progress}%"
                )
            
            logger.info(f"Deadline reminder sent to {vendor.name} for job {job.job_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending deadline reminder: {str(e)}")
            return False
    
    @staticmethod
    def notify_qc_result(qc_inspection):
        """
        Notify vendor of QC inspection results
        
        Args:
            qc_inspection: QCInspection instance
        """
        if not qc_inspection.job_vendor_stage or not qc_inspection.job_vendor_stage.vendor.user:
            return False
        
        try:
            vendor = qc_inspection.job_vendor_stage.vendor
            job = qc_inspection.job_vendor_stage.job
            
            status_text = "PASSED ✓" if qc_inspection.passed else "FAILED ✗"
            
            context = {
                'vendor_name': vendor.name,
                'job_number': job.job_number,
                'job_name': job.job_name,
                'qc_status': status_text,
                'issues_found': qc_inspection.issues_found or "None",
                'notes': qc_inspection.notes,
                'passed': qc_inspection.passed,
                'vps_score_impact': "+1" if qc_inspection.passed else "-2",
            }
            
            VendorNotificationService._send_email(
                recipient=vendor.user.email,
                subject=f"QC Result: {job.job_number} - {status_text}",
                template='emails/vendor_qc_result.html',
                context=context,
                vendor=vendor
            )
            
            # SMS notification
            if getattr(vendor, 'prefer_sms', False) and vendor.phone:
                VendorNotificationService._send_sms(
                    phone=vendor.phone,
                    message=f"QC Result for {job.job_number}: {status_text}"
                )
            
            logger.info(f"QC result notification sent to {vendor.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending QC result notification: {str(e)}")
            return False
    
    @staticmethod
    def notify_job_completed(job_vendor_stage):
        """
        Notify vendor when job is completed
        
        Args:
            job_vendor_stage: JobVendorStage instance
        """
        if not job_vendor_stage.vendor.user or not job_vendor_stage.vendor.user.email:
            return False
        
        try:
            vendor = job_vendor_stage.vendor
            job = job_vendor_stage.job
            
            context = {
                'vendor_name': vendor.name,
                'job_number': job.job_number,
                'job_name': job.job_name,
                'completed_at': job_vendor_stage.completed_at,
                'duration_days': (job_vendor_stage.completed_at - job_vendor_stage.started_at).days,
            }
            
            VendorNotificationService._send_email(
                recipient=vendor.user.email,
                subject=f"Job Completed: {job.job_number}",
                template='emails/vendor_job_completed.html',
                context=context,
                vendor=vendor
            )
            
            logger.info(f"Job completion notification sent to {vendor.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending job completion notification: {str(e)}")
            return False
    
    @staticmethod
    def notify_invoice_approved(vendor_invoice):
        """
        Notify vendor when invoice is approved
        
        Args:
            vendor_invoice: VendorInvoice instance
        """
        vendor = vendor_invoice.vendor
        if not vendor.user or not vendor.user.email:
            return False
        
        try:
            context = {
                'vendor_name': vendor.name,
                'invoice_number': vendor_invoice.invoice_number,
                'vendor_invoice_ref': vendor_invoice.vendor_invoice_ref,
                'total_amount': vendor_invoice.total_amount,
                'approved_at': vendor_invoice.approved_at,
            }
            
            VendorNotificationService._send_email(
                recipient=vendor.user.email,
                subject=f"Invoice Approved: {vendor_invoice.invoice_number}",
                template='emails/vendor_invoice_approved.html',
                context=context,
                vendor=vendor
            )
            
            logger.info(f"Invoice approval notification sent to {vendor.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending invoice approval notification: {str(e)}")
            return False
    
    @staticmethod
    def notify_invoice_rejected(vendor_invoice, rejection_reason=''):
        """
        Notify vendor when invoice is rejected
        
        Args:
            vendor_invoice: VendorInvoice instance
            rejection_reason: Reason for rejection
        """
        vendor = vendor_invoice.vendor
        if not vendor.user or not vendor.user.email:
            return False
        
        try:
            context = {
                'vendor_name': vendor.name,
                'invoice_number': vendor_invoice.invoice_number,
                'vendor_invoice_ref': vendor_invoice.vendor_invoice_ref,
                'total_amount': vendor_invoice.total_amount,
                'rejection_reason': rejection_reason,
            }
            
            VendorNotificationService._send_email(
                recipient=vendor.user.email,
                subject=f"Invoice Rejected: {vendor_invoice.invoice_number}",
                template='emails/vendor_invoice_rejected.html',
                context=context,
                vendor=vendor
            )
            
            logger.info(f"Invoice rejection notification sent to {vendor.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending invoice rejection notification: {str(e)}")
            return False
    
    # ========== PRIVATE HELPER METHODS ==========
    
    @staticmethod
    def _send_email(recipient, subject, template, context, vendor=None):
        """
        Send email notification
        
        Args:
            recipient: Email address
            subject: Email subject
            template: Template path (e.g., 'emails/vendor_job_assigned.html')
            context: Template context dict
            vendor: Vendor instance (optional)
        """
        try:
            # Render HTML template
            html_content = render_to_string(template, context)
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=f"Please view this email in HTML format.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Send
            email.send(fail_silently=False)
            logger.info(f"Email sent to {recipient}: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
    
    @staticmethod
    def _send_sms(phone, message):
        """
        Send SMS notification
        Uses Africa's Talking or Twilio
        
        Args:
            phone: Phone number
            message: SMS message
        """
        try:
            # TODO: Implement SMS provider integration
            # Options:
            # 1. Africa's Talking (for Kenya/Africa)
            # 2. Twilio (for global)
            # 3. AWS SNS
            logger.info(f"SMS to {phone}: {message}")
            
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone}: {str(e)}")
    
    @staticmethod
    def _create_notification(user, notification_type, title, message, related_job=None, action_url=None):
        try:
            from .models import Notification

            Notification.objects.create(
                recipient=user,
                notification_type=notification_type,
                title=title,
                message=message,
                related_job=related_job,
                action_url=action_url,
                is_read=False,
            )

        except Exception as e:
            logger.error(f"Failed to create notification for {user.username}: {str(e)}")


class PTNotificationService:
    """
    Service to handle Production Team notifications
    """
    
    @staticmethod
    def notify_pt_invoice_submitted(vendor_invoice):
        """
        Notify Production Team when vendor submits invoice
        
        Args:
            vendor_invoice: VendorInvoice instance
        """
        try:
            # Get all PT members
            try:
                pt_group = Group.objects.get(name='Production Team')
                pt_users = pt_group.user_set.all()
            except Group.DoesNotExist:
                # Fallback: Get all users with is_staff=True
                pt_users = User.objects.filter(is_staff=True)
            
            vendor = vendor_invoice.vendor
            job = vendor_invoice.job
            
            for pt_user in pt_users:
                if not pt_user.email:
                    continue
                
                context = {
                    'pt_user_name': pt_user.first_name or pt_user.username,
                    'vendor_name': vendor.name,
                    'invoice_number': vendor_invoice.invoice_number,
                    'vendor_invoice_ref': vendor_invoice.vendor_invoice_ref,
                    'job_number': job.job_number,
                    'total_amount': vendor_invoice.total_amount,
                    'invoice_date': vendor_invoice.invoice_date,
                    'due_date': vendor_invoice.due_date,
                    'approval_url': f"{settings.SITE_URL}/admin/invoices/{vendor_invoice.id}/approve/",
                }
                
                # Send email
                VendorNotificationService._send_email(
                    recipient=pt_user.email,
                    subject=f"Invoice Pending Approval: {vendor_invoice.invoice_number}",
                    template='emails/pt_invoice_pending.html',
                    context=context
                )
                
                # Create in-app notification
                VendorNotificationService._create_notification(
                    user=pt_user,
                    notification_type='vendor_invoice_submitted',
                    title=f"Invoice Pending: {vendor_invoice.invoice_number}",
                    message=f"{vendor.name} submitted invoice for KES {vendor_invoice.total_amount}",
                    action_url='/production-team/my-jobs',
                )
            
            logger.info(f"PT notification sent for invoice {vendor_invoice.invoice_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error notifying PT team about invoice: {str(e)}")
            return False
    
    @staticmethod
    def notify_pt_job_overdue(job_vendor_stage):
        """
        Notify PT when job becomes overdue
        
        Args:
            job_vendor_stage: JobVendorStage instance
        """
        try:
            try:
                pt_group = Group.objects.get(name='Production Team')
                pt_users = pt_group.user_set.all()
            except Group.DoesNotExist:
                pt_users = User.objects.filter(is_staff=True)
            
            job = job_vendor_stage.job
            vendor = job_vendor_stage.vendor
            days_overdue = (timezone.now() - job_vendor_stage.expected_completion).days
            
            for pt_user in pt_users:
                if not pt_user.email:
                    continue
                
                context = {
                    'pt_user_name': pt_user.first_name or pt_user.username,
                    'job_number': job.job_number,
                    'vendor_name': vendor.name,
                    'days_overdue': days_overdue,
                    'expected_completion': job_vendor_stage.expected_completion,
                    'progress': job_vendor_stage.progress,
                }
                
                VendorNotificationService._send_email(
                    recipient=pt_user.email,
                    subject=f"⚠️ OVERDUE: {job.job_number} ({days_overdue} days late)",
                    template='emails/pt_job_overdue.html',
                    context=context
                )
            
            logger.info(f"PT overdue notification for job {job.job_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending PT overdue notification: {str(e)}")
            return False
