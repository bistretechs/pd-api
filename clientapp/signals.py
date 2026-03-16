"""
Django signals for automatic change tracking in Product Catalog
Implements ProductChangeHistory entry creation for ALL product field changes
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.apps import AppConfig
from clientapp.models import Product, ProductChangeHistory, ProductSEO
import json
import logging
import secrets
from decimal import Decimal

logger = logging.getLogger(__name__)

# Track previous values before save
_product_previous_values = {}


# ──────────────────────────────────────────────
# Vendor Performance Score — auto-recalculate
# ──────────────────────────────────────────────

@receiver(post_save, sender='clientapp.PurchaseOrder')
def recalculate_vps_on_purchase_order_save(sender, instance, **kwargs):
    vendor = getattr(instance, 'vendor', None)
    if vendor is not None:
        vendor.update_performance_score()


@receiver(post_save, sender='clientapp.QCInspection')
def recalculate_vps_on_qc_inspection_save(sender, instance, **kwargs):
    vendor = getattr(instance, 'vendor', None)
    if vendor is not None:
        vendor.update_performance_score()


# ──────────────────────────────────────────────
# Vendor auto-invite on creation
# ──────────────────────────────────────────────

@receiver(post_save, sender='clientapp.Vendor')
def auto_invite_vendor_on_create(sender, instance, created, **kwargs):
    if not created:
        return
    if not instance.email:
        logger.warning("Vendor %s (%s) created without email — skipping auto-invite.", instance.pk, instance.name)
        return
    vendor_pk = instance.pk
    from django.db import transaction
    transaction.on_commit(lambda: _provision_vendor_invite(vendor_pk))


def _provision_vendor_invite(vendor_pk: int) -> None:
    from django.contrib.auth.models import User
    from django.core.cache import cache
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    from clientapp.models import Vendor, Notification

    try:
        vendor = Vendor.objects.get(pk=vendor_pk)
    except Vendor.DoesNotExist:
        logger.error("Vendor %s not found when trying to send auto-invite.", vendor_pk)
        return

    email = vendor.email.strip().lower()

    # ── Resolve or create the linked User ──────────────────────────────
    existing_user = User.objects.filter(email__iexact=email).first()
    user_created = False

    if existing_user is not None:
        if hasattr(existing_user, 'vendor_profile') and existing_user.vendor_profile.pk != vendor.pk:
            # Email already belongs to a different vendor — do not overwrite
            logger.warning(
                "Vendor %s email '%s' is already linked to vendor %s — skipping user creation.",
                vendor.pk, email, existing_user.vendor_profile.pk,
            )
            return
        # Safe to link (user exists but has no vendor_profile, or this is the same vendor)
        vendor.user = existing_user
        existing_user.is_active = False
        existing_user.save(update_fields=["is_active"])
        vendor.save(update_fields=["user", "updated_at"])
    else:
        username_base = email.split("@")[0]
        username = username_base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{username_base}{counter}"
            counter += 1

        first_name = (
            (vendor.contact_person or "").strip().split(" ")[0]
            if vendor.contact_person
            else vendor.name[:50]
        )
        existing_user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            is_active=False,
            is_staff=False,
        )
        vendor.user = existing_user
        vendor.save(update_fields=["user", "updated_at"])
        user_created = True

    # ── Generate invite token ───────────────────────────────────────────
    invite_token = secrets.token_urlsafe(32)
    cache.set(f"vendor_invite_{invite_token}", existing_user.id, 172800)  # 48 h

    frontend_url = getattr(settings, "FRONTEND_URL", "https://printduka.co.ke").rstrip("/")
    invite_url = f"{frontend_url}/activate?token={invite_token}"

    contact = vendor.contact_person or vendor.name
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "PrintDuka <dev@printduka.co.ke>")

    # ── Send invite email to vendor ─────────────────────────────────────
    plain_body = (
        f"Hello {contact},\n\n"
        f"You have been invited to the PrintDuka Vendor Portal.\n\n"
        f"Set your password and activate your account here:\n{invite_url}\n\n"
        "This link expires in 48 hours.\n\n"
        "PrintDuka Team"
    )

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Vendor Portal Invitation</title></head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f4f8;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
        <tr><td style="background-color:#093756;border-radius:8px 8px 0 0;padding:32px 40px;text-align:center;">
          <h1 style="margin:0;color:#f6b619;font-size:24px;font-weight:800;letter-spacing:1px;">PRINT<span style="color:#ffffff;">DUKA</span></h1>
          <p style="margin:8px 0 0;color:#a8c4d8;font-size:12px;letter-spacing:2px;text-transform:uppercase;">Vendor Portal</p>
        </td></tr>
        <tr><td style="background-color:#ffffff;padding:40px;">
          <h2 style="margin:0 0 16px;color:#093756;font-size:20px;font-weight:700;">You&rsquo;re invited, {contact}</h2>
          <p style="margin:0 0 24px;color:#444444;font-size:15px;line-height:1.6;">
            You have been registered as a supplier on the <strong>PrintDuka Vendor Portal</strong>.
            Click the button below to set your password and activate your account.
          </p>
          <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8ecf0;border-radius:6px;overflow:hidden;margin-bottom:28px;">
            <tr><td colspan="2" style="background-color:#093756;padding:12px 16px;"><span style="color:#f6b619;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Your Account Details</span></td></tr>
            <tr style="background-color:#f8fafc;"><td style="padding:10px 16px;color:#555555;font-size:14px;width:40%;border-bottom:1px solid #e8ecf0;">Company</td><td style="padding:10px 16px;color:#093756;font-size:14px;font-weight:700;border-bottom:1px solid #e8ecf0;">{vendor.name}</td></tr>
            <tr><td style="padding:10px 16px;color:#555555;font-size:14px;border-bottom:1px solid #e8ecf0;">Login Email</td><td style="padding:10px 16px;color:#093756;font-size:14px;font-weight:600;border-bottom:1px solid #e8ecf0;">{email}</td></tr>
            <tr style="background-color:#f8fafc;"><td style="padding:10px 16px;color:#555555;font-size:14px;">Link Expires</td><td style="padding:10px 16px;color:#093756;font-size:14px;font-weight:600;">48 hours</td></tr>
          </table>
          <div style="text-align:center;margin-bottom:28px;">
            <a href="{invite_url}" style="display:inline-block;background-color:#f6b619;color:#093756;font-size:15px;font-weight:800;text-decoration:none;padding:14px 36px;border-radius:6px;letter-spacing:0.5px;">Activate My Account &rarr;</a>
          </div>
          <p style="margin:0;color:#888888;font-size:12px;line-height:1.6;">
            If the button doesn&rsquo;t work, copy and paste this link into your browser:<br>
            <a href="{invite_url}" style="color:#093756;word-break:break-all;">{invite_url}</a>
          </p>
        </td></tr>
        <tr><td style="background-color:#093756;border-radius:0 0 8px 8px;padding:24px 40px;text-align:center;">
          <p style="margin:0 0 4px;color:#a8c4d8;font-size:12px;">This is an automated notification from PrintDuka.</p>
          <p style="margin:0;color:#6b8fa8;font-size:11px;">&copy; 2026 PrintDuka. All rights reserved.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    try:
        msg = EmailMultiAlternatives(
            subject=f"[PrintDuka] Vendor Portal Invitation — {vendor.name}",
            body=plain_body,
            from_email=from_email,
            to=[email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info("Vendor invite email sent to %s (vendor %s).", email, vendor.pk)
    except Exception as exc:
        logger.error("Failed to send vendor invite email to %s: %s", email, exc)

    # ── Notify internal staff (Admin + Production Team) ─────────────────
    _notify_staff_vendor_created(vendor, invite_url)


def _notify_staff_vendor_created(vendor, invite_url: str) -> None:
    from django.contrib.auth.models import User
    from clientapp.models import Notification

    staff_users = User.objects.filter(
        is_active=True,
        groups__name__in=["Admin", "Production Team"],
    ).distinct()

    for staff_user in staff_users:
        try:
            Notification.objects.create(
                recipient=staff_user,
                notification_type="vendor_portal_invite_sent",
                title=f"Vendor Invited — {vendor.name}",
                message=(
                    f"{vendor.name} ({vendor.email}) has been registered as a vendor. "
                    f"A portal invite has been sent automatically."
                ),
                action_url=f"/production-team/vendors",
            )
        except Exception as exc:
            logger.warning("Could not create Notification for staff user %s: %s", staff_user.pk, exc)


# ──────────────────────────────────────────────
# Client auto-invite on creation
# ──────────────────────────────────────────────

@receiver(post_save, sender='clientapp.Client')
def auto_invite_client_on_create(sender, instance, created, **kwargs):
    if not created:
        return
    if not instance.email:
        logger.warning("Client %s (%s) created without email — skipping auto-invite.", instance.pk, instance.name)
        return
    client_pk = instance.pk
    from django.db import transaction
    transaction.on_commit(lambda: _provision_client_invite(client_pk))


def _provision_client_invite(client_pk: int) -> None:
    from django.contrib.auth.models import User
    from django.core.cache import cache
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    from clientapp.models import Client, ClientPortalUser, Notification

    try:
        client = Client.objects.get(pk=client_pk)
    except Client.DoesNotExist:
        logger.error("Client %s not found when trying to send auto-invite.", client_pk)
        return

    email = client.email.strip().lower()

    existing_user = User.objects.filter(email__iexact=email).first()

    if existing_user is not None:
        if hasattr(existing_user, 'client_portal_user') and existing_user.client_portal_user.client_id != client.pk:
            logger.warning(
                "Client %s email '%s' is already linked to another portal user — skipping.",
                client.pk, email,
            )
            return
        portal_user, _ = ClientPortalUser.objects.get_or_create(
            user=existing_user,
            client=client,
            defaults={'role': 'owner'},
        )
        existing_user.is_active = False
        existing_user.save(update_fields=["is_active"])
    else:
        username_base = email.split("@")[0]
        username = username_base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{username_base}{counter}"
            counter += 1

        first_name = (client.name or "").strip().split(" ")[0][:50]
        existing_user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            is_active=False,
            is_staff=False,
        )
        ClientPortalUser.objects.create(
            user=existing_user,
            client=client,
            role='owner',
        )

    invite_token = secrets.token_urlsafe(32)
    cache.set(f"client_invite_{invite_token}", existing_user.id, 172800)  # 48 h

    frontend_url = getattr(settings, "FRONTEND_URL", "https://printduka.co.ke").rstrip("/")
    invite_url = f"{frontend_url}/activate?token={invite_token}"

    contact = client.name
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "PrintDuka <dev@printduka.co.ke>")

    plain_body = (
        f"Hello {contact},\n\n"
        f"You have been registered as a client on the PrintDuka Client Portal.\n\n"
        f"Set your password and activate your account here:\n{invite_url}\n\n"
        "This link expires in 48 hours.\n\n"
        "PrintDuka Team"
    )

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Client Portal Invitation</title></head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f4f8;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
        <tr><td style="background-color:#093756;border-radius:8px 8px 0 0;padding:32px 40px;text-align:center;">
          <h1 style="margin:0;color:#f6b619;font-size:24px;font-weight:800;letter-spacing:1px;">PRINT<span style="color:#ffffff;">DUKA</span></h1>
          <p style="margin:8px 0 0;color:#a8c4d8;font-size:12px;letter-spacing:2px;text-transform:uppercase;">Client Portal</p>
        </td></tr>
        <tr><td style="background-color:#ffffff;padding:40px;">
          <h2 style="margin:0 0 16px;color:#093756;font-size:20px;font-weight:700;">Welcome, {contact}</h2>
          <p style="margin:0 0 24px;color:#444444;font-size:15px;line-height:1.6;">
            You have been registered as a client on the <strong>PrintDuka Client Portal</strong>.
            Click the button below to set your password and activate your account.
          </p>
          <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8ecf0;border-radius:6px;overflow:hidden;margin-bottom:28px;">
            <tr><td colspan="2" style="background-color:#093756;padding:12px 16px;"><span style="color:#f6b619;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Your Account Details</span></td></tr>
            <tr style="background-color:#f8fafc;"><td style="padding:10px 16px;color:#555555;font-size:14px;width:40%;border-bottom:1px solid #e8ecf0;">Name</td><td style="padding:10px 16px;color:#093756;font-size:14px;font-weight:700;border-bottom:1px solid #e8ecf0;">{client.name}</td></tr>
            <tr><td style="padding:10px 16px;color:#555555;font-size:14px;border-bottom:1px solid #e8ecf0;">Login Email</td><td style="padding:10px 16px;color:#093756;font-size:14px;font-weight:600;border-bottom:1px solid #e8ecf0;">{email}</td></tr>
            <tr style="background-color:#f8fafc;"><td style="padding:10px 16px;color:#555555;font-size:14px;">Link Expires</td><td style="padding:10px 16px;color:#093756;font-size:14px;font-weight:600;">48 hours</td></tr>
          </table>
          <div style="text-align:center;margin-bottom:28px;">
            <a href="{invite_url}" style="display:inline-block;background-color:#f6b619;color:#093756;font-size:15px;font-weight:800;text-decoration:none;padding:14px 36px;border-radius:6px;letter-spacing:0.5px;">Activate My Account &rarr;</a>
          </div>
          <p style="margin:0;color:#888888;font-size:12px;line-height:1.6;">
            If the button doesn&rsquo;t work, copy and paste this link into your browser:<br>
            <a href="{invite_url}" style="color:#093756;word-break:break-all;">{invite_url}</a>
          </p>
        </td></tr>
        <tr><td style="background-color:#093756;border-radius:0 0 8px 8px;padding:24px 40px;text-align:center;">
          <p style="margin:0 0 4px;color:#a8c4d8;font-size:12px;">This is an automated notification from PrintDuka.</p>
          <p style="margin:0;color:#6b8fa8;font-size:11px;">&copy; 2026 PrintDuka. All rights reserved.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    try:
        msg = EmailMultiAlternatives(
            subject=f"[PrintDuka] Client Portal Invitation — {client.name}",
            body=plain_body,
            from_email=from_email,
            to=[email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info("Client invite email sent to %s (client %s).", email, client.pk)
    except Exception as exc:
        logger.error("Failed to send client invite email to %s: %s", email, exc)

    _notify_staff_client_created(client)


def _notify_staff_client_created(client) -> None:
    from django.contrib.auth.models import User
    from clientapp.models import Notification

    staff_users = User.objects.filter(
        is_active=True,
        groups__name__in=["Admin", "Account Manager"],
    ).distinct()

    for staff_user in staff_users:
        try:
            Notification.objects.create(
                recipient=staff_user,
                notification_type="client_portal_invite_sent",
                title=f"Client Invited — {client.name}",
                message=(
                    f"{client.name} ({client.email}) has been registered as a client. "
                    f"A portal invite has been sent automatically."
                ),
                action_url=f"/account-manager/clients",
            )
        except Exception as exc:
            logger.warning("Could not create Notification for staff user %s: %s", staff_user.pk, exc)


@receiver(pre_save, sender=Product)
def track_product_changes_pre_save(sender, instance, **kwargs):
    """
    Pre-save signal to capture product values before they change
    Stores in module-level dict for comparison in post_save
    """
    if instance.pk:  # Only for updates, not creates
        try:
            old_instance = Product.objects.get(pk=instance.pk)
            _product_previous_values[instance.pk] = {
                'name': old_instance.name,
                'short_description': old_instance.short_description,
                'long_description': old_instance.long_description,
                'technical_specs': old_instance.technical_specs,
                'pricing_mode': old_instance.pricing_mode,
                'primary_category': str(old_instance.primary_category_id) if old_instance.primary_category_id else None,
                'sub_category': str(old_instance.sub_category_id) if old_instance.sub_category_id else None,
                'product_family': str(old_instance.product_family_id) if old_instance.product_family_id else None,
                'visibility': old_instance.visibility,
                'feature_product': old_instance.feature_product,
                'bestseller_badge': old_instance.bestseller_badge,
                'new_arrival': old_instance.new_arrival,
                'status': old_instance.status,
                'internal_code': old_instance.internal_code,
            }
        except Product.DoesNotExist:
            pass

@receiver(post_save, sender=Product)
def create_change_history_for_product(sender, instance, created, **kwargs):
    """
    Post-save signal to create ProductChangeHistory entries
    Tracks changes to all product fields automatically
    """
    from django.utils import timezone
    
    # Skip if this is a create (not an update)
    if created:
        return
    
    # Get changed_by user (set by the view or model)
    changed_by = getattr(instance, '_changed_by', None)
    if not changed_by:
        # Fall back to updated_by or created_by
        changed_by = instance.updated_by or instance.created_by
    
    # Get previous values
    previous_values = _product_previous_values.pop(instance.pk, {})
    if not previous_values:
        return  # No changes tracked
    
    # Check each field for changes
    fields_to_track = [
        'name', 'short_description', 'long_description', 'technical_specs',
        'pricing_mode', 'primary_category', 'sub_category', 'product_family',
        'visibility', 'feature_product', 'bestseller_badge', 'new_arrival',
        'status', 'internal_code'
    ]
    
    for field in fields_to_track:
        old_value = previous_values.get(field)
        new_value = getattr(instance, field, None)
        
        # Convert to strings for comparison
        old_str = str(old_value) if old_value is not None else ''
        new_str = str(new_value) if new_value is not None else ''
        
        # Skip if no actual change
        if old_str == new_str:
            continue
        
        # Create change history entry
        ProductChangeHistory.objects.create(
            product=instance,
            changed_by=changed_by,
            change_type='update',
            field_changed=field,
            old_value=old_str[:255] if old_str else '',  # Truncate to fit in DB
            new_value=new_str[:255] if new_str else '',
            changed_at=timezone.now()
        )



class ClientAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clientapp'
    
    def ready(self):
        """
        Import signals when app is ready
        This ensures signals are registered when Django starts
        """
        import clientapp.signals  # noqa

