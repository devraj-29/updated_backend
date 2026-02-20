"""
NDA Shield — Email Service
Sends beautiful HTML emails for NDA assignment, reminders, confirmations.
"""
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _base_ctx(assignment):
    """Build shared template context from an assignment."""
    return {
        "company_name": settings.COMPANY_NAME,
        "signer_name": assignment.person.full_name,
        "signer_email": assignment.person.email,
        "nda_name": assignment.nda_template.name,
        "nda_category": assignment.nda_template.get_category_display() if hasattr(assignment.nda_template, 'get_category_display') else assignment.nda_template.category,
        "nda_version": assignment.nda_version.version_number,
        "signing_url": assignment.signing_url,
        "expires_at": assignment.expires_at,
        "message": assignment.message,
        "assigned_by": assignment.assigned_by.full_name if assignment.assigned_by else "System",
        "frontend_url": settings.FRONTEND_URL,
    }


def _send(subject, to_email, html_body, plain_body=None):
    """Send email with HTML + plain text fallback."""
    if not plain_body:
        import re
        plain_body = re.sub(r'<[^>]+>', '', html_body)
        plain_body = re.sub(r'\n\s*\n', '\n\n', plain_body).strip()

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    msg.attach_alternative(html_body, "text/html")

    try:
        msg.send(fail_silently=False)
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email failed to {to_email}: {e}")
        return False


def _email_wrapper(content, company_name):
    """Wrap content in Apple-inspired email template."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','Segoe UI',Roboto,sans-serif; background:#f5f5f7; color:#1d1d1f; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:580px; margin:0 auto; padding:40px 20px; }}
  .card {{ background:#fff; border-radius:20px; padding:40px; box-shadow:0 4px 24px rgba(0,0,0,0.06); }}
  .logo {{ text-align:center; margin-bottom:28px; padding-bottom:20px; border-bottom:1px solid #f0f0f2; }}
  .logo-icon {{ display:inline-flex; align-items:center; justify-content:center; width:48px; height:48px; border-radius:14px; background:linear-gradient(135deg,#00C853,#00E676); margin-bottom:8px; }}
  .logo-icon svg {{ width:24px; height:24px; }}
  .logo-name {{ font-size:18px; font-weight:700; color:#1d1d1f; letter-spacing:-0.3px; }}
  .logo-sub {{ font-size:11px; color:#86868b; letter-spacing:1.5px; text-transform:uppercase; margin-top:2px; }}
  h1 {{ font-size:24px; font-weight:700; color:#1d1d1f; margin:0 0 8px; letter-spacing:-0.5px; text-align:center; }}
  .subtitle {{ font-size:15px; color:#86868b; text-align:center; margin:0 0 28px; line-height:1.5; }}
  .info-box {{ background:#f5f5f7; border-radius:14px; padding:20px; margin:20px 0; }}
  .info-row {{ display:flex; justify-content:space-between; padding:6px 0; font-size:14px; }}
  .info-label {{ color:#86868b; }}
  .info-value {{ color:#1d1d1f; font-weight:600; }}
  .msg-box {{ background:#FFF8E1; border-left:3px solid #FFC107; border-radius:0 12px 12px 0; padding:14px 18px; margin:18px 0; font-size:14px; color:#5D4037; line-height:1.5; font-style:italic; }}
  .cta {{ display:block; text-align:center; margin:28px 0 20px; }}
  .cta a {{ display:inline-block; padding:16px 48px; background:linear-gradient(135deg,#00C853,#00B848); color:#fff; text-decoration:none; border-radius:14px; font-size:16px; font-weight:600; letter-spacing:-0.2px; }}
  .expire {{ text-align:center; font-size:12px; color:#86868b; margin-bottom:8px; }}
  .security {{ background:#f0faf4; border-radius:12px; padding:14px 18px; margin-top:18px; display:flex; align-items:center; gap:10px; }}
  .security-icon {{ font-size:18px; flex-shrink:0; }}
  .security-text {{ font-size:12px; color:#4a7c5f; line-height:1.4; }}
  .footer {{ text-align:center; padding-top:24px; margin-top:20px; }}
  .footer p {{ font-size:11px; color:#86868b; line-height:1.6; margin:0; }}
  .footer a {{ color:#00B848; text-decoration:none; }}
  .divider {{ height:1px; background:#f0f0f2; margin:18px 0; }}
  .warn {{ color:#FF6B6B; font-weight:600; }}
  .success-icon {{ display:inline-flex; align-items:center; justify-content:center; width:64px; height:64px; border-radius:50%; background:#f0faf4; margin:0 auto 16px; }}
  .badge {{ display:inline-block; padding:4px 12px; border-radius:8px; font-size:12px; font-weight:600; background:#f0faf4; color:#00B848; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <div class="logo">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="none"><path d="M12 2L3 7v5.5c0 5.6 3.8 10.7 9 12 5.2-1.3 9-6.4 9-12V7L12 2z" fill="rgba(255,255,255,0.3)" stroke="#fff" stroke-width="1.5"/><path d="M9 12l2 2 4-4" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </div>
      <div class="logo-name">{company_name}</div>
      <div class="logo-sub">NDA Shield · Secure Document Signing</div>
    </div>
    {content}
    <div class="footer">
      <div class="divider"></div>
      <p>This is an automated message from {company_name} NDA Shield.<br>
      This link is unique to you. Do not forward this email.<br>
      <a href="{settings.FRONTEND_URL}">NDA Shield Portal</a></p>
    </div>
  </div>
</div>
</body>
</html>"""


def send_nda_assigned(assignment):
    """Send NDA assignment notification with signing link."""
    ctx = _base_ctx(assignment)
    exp_str = ctx["expires_at"].strftime("%B %d, %Y at %I:%M %p") if ctx["expires_at"] else "N/A"

    content = f"""
    <h1>📋 NDA Ready for Signing</h1>
    <p class="subtitle">
      Hi <strong>{ctx['signer_name']}</strong>,<br>
      You've been assigned a Non-Disclosure Agreement that requires your review and signature.
    </p>

    <div class="info-box">
      <div class="info-row"><span class="info-label">Document</span><span class="info-value">{ctx['nda_name']}</span></div>
      <div class="info-row"><span class="info-label">Version</span><span class="info-value">v{ctx['nda_version']}</span></div>
      <div class="info-row"><span class="info-label">Category</span><span class="info-value">{ctx['nda_category']}</span></div>
      <div class="info-row"><span class="info-label">Assigned By</span><span class="info-value">{ctx['assigned_by']}</span></div>
      <div class="info-row"><span class="info-label">Expires</span><span class="info-value warn">{exp_str}</span></div>
    </div>
    """

    if ctx["message"]:
        content += f'<div class="msg-box">💬 "{ctx["message"]}"</div>'

    content += f"""
    <div class="cta"><a href="{ctx['signing_url']}">Review & Sign NDA →</a></div>
    <p class="expire">⏰ This link expires on {exp_str}</p>

    <div class="security">
      <span class="security-icon">🔐</span>
      <span class="security-text">
        <strong>Secure & Private</strong> — This link is unique to you and can only be used once.
        Your signature will be cryptographically hashed for tamper-proof verification.
        Do not share this link with anyone.
      </span>
    </div>
    """

    html = _email_wrapper(content, ctx["company_name"])
    plain = (
        f"Hi {ctx['signer_name']},\n\n"
        f"You've been assigned '{ctx['nda_name']}' (v{ctx['nda_version']}) for signing.\n"
        f"Assigned by: {ctx['assigned_by']}\n"
        f"Expires: {exp_str}\n\n"
        f"Review and sign here: {ctx['signing_url']}\n\n"
        f"This link is unique to you. Do not forward.\n"
        f"— {ctx['company_name']} NDA Shield"
    )

    return _send(
        subject=f"🛡️ NDA Signing Required: {ctx['nda_name']} — {ctx['company_name']}",
        to_email=ctx["signer_email"],
        html_body=html,
        plain_body=plain,
    )


def send_nda_reminder(assignment):
    """Send reminder for pending NDA."""
    ctx = _base_ctx(assignment)
    exp_str = ctx["expires_at"].strftime("%B %d, %Y at %I:%M %p") if ctx["expires_at"] else "N/A"
    reminder_n = assignment.reminder_count

    content = f"""
    <h1>⏰ Reminder: NDA Awaiting Signature</h1>
    <p class="subtitle">
      Hi <strong>{ctx['signer_name']}</strong>,<br>
      This is reminder #{reminder_n} — your NDA is still pending your signature.
    </p>

    <div class="info-box">
      <div class="info-row"><span class="info-label">Document</span><span class="info-value">{ctx['nda_name']}</span></div>
      <div class="info-row"><span class="info-label">Version</span><span class="info-value">v{ctx['nda_version']}</span></div>
      <div class="info-row"><span class="info-label">Status</span><span class="info-value warn">Pending Signature</span></div>
      <div class="info-row"><span class="info-label">Expires</span><span class="info-value warn">{exp_str}</span></div>
    </div>

    <div class="cta"><a href="{ctx['signing_url']}">Sign NDA Now →</a></div>
    <p class="expire">⚠️ Please complete before {exp_str}</p>

    <div class="security">
      <span class="security-icon">🔐</span>
      <span class="security-text">This is a secure, one-time link unique to you.</span>
    </div>
    """

    html = _email_wrapper(content, ctx["company_name"])
    return _send(
        subject=f"⏰ Reminder #{reminder_n}: Sign '{ctx['nda_name']}' — {ctx['company_name']}",
        to_email=ctx["signer_email"],
        html_body=html,
    )


def send_nda_signed_confirmation(assignment, signed_document):
    """Send confirmation to signer after successful signing."""
    ctx = _base_ctx(assignment)
    conf_id = signed_document.confirmation_id
    signed_at = signed_document.consent_timestamp.strftime("%B %d, %Y at %I:%M %p") if signed_document.consent_timestamp else "N/A"

    content = f"""
    <div style="text-align:center;">
      <div class="success-icon"><span style="font-size:32px">✅</span></div>
    </div>
    <h1>NDA Signed Successfully</h1>
    <p class="subtitle">
      Thank you, <strong>{ctx['signer_name']}</strong>.<br>
      Your signature has been recorded and is legally binding.
    </p>

    <div class="info-box">
      <div class="info-row"><span class="info-label">Document</span><span class="info-value">{ctx['nda_name']}</span></div>
      <div class="info-row"><span class="info-label">Version</span><span class="info-value">v{ctx['nda_version']}</span></div>
      <div class="info-row"><span class="info-label">Signed At</span><span class="info-value">{signed_at}</span></div>
      <div class="info-row"><span class="info-label">Confirmation</span><span class="info-value" style="font-family:monospace;color:#00B848;">{conf_id}</span></div>
    </div>

    <div class="security">
      <span class="security-icon">🔒</span>
      <span class="security-text">
        Your signature has been cryptographically hashed (SHA-256) for tamper-proof verification.
        Keep this confirmation ID for your records: <strong>{conf_id}</strong>
      </span>
    </div>
    """

    html = _email_wrapper(content, ctx["company_name"])
    return _send(
        subject=f"✅ NDA Signed: {ctx['nda_name']} — Confirmation {conf_id}",
        to_email=ctx["signer_email"],
        html_body=html,
    )


def send_nda_signed_notification_to_admin(assignment, signed_document):
    """Notify the assigner that an NDA was signed."""
    if not assignment.assigned_by or not assignment.assigned_by.email:
        return False

    ctx = _base_ctx(assignment)
    conf_id = signed_document.confirmation_id
    signed_at = signed_document.consent_timestamp.strftime("%B %d, %Y at %I:%M %p") if signed_document.consent_timestamp else "N/A"

    content = f"""
    <h1>✅ NDA Signed</h1>
    <p class="subtitle">
      <strong>{ctx['signer_name']}</strong> has signed the assigned NDA.
    </p>

    <div class="info-box">
      <div class="info-row"><span class="info-label">Signer</span><span class="info-value">{ctx['signer_name']} ({ctx['signer_email']})</span></div>
      <div class="info-row"><span class="info-label">Document</span><span class="info-value">{ctx['nda_name']} v{ctx['nda_version']}</span></div>
      <div class="info-row"><span class="info-label">Signed At</span><span class="info-value">{signed_at}</span></div>
      <div class="info-row"><span class="info-label">Confirmation</span><span class="info-value" style="font-family:monospace;color:#00B848;">{conf_id}</span></div>
    </div>

    <div class="cta"><a href="{ctx['frontend_url']}/documents">View in NDA Shield →</a></div>
    """

    html = _email_wrapper(content, ctx["company_name"])
    return _send(
        subject=f"✅ {ctx['signer_name']} signed '{ctx['nda_name']}' — {conf_id}",
        to_email=assignment.assigned_by.email,
        html_body=html,
    )


def send_nda_declined_notification(assignment):
    """Notify admin that an NDA was declined."""
    if not assignment.assigned_by or not assignment.assigned_by.email:
        return False

    ctx = _base_ctx(assignment)

    content = f"""
    <h1>❌ NDA Declined</h1>
    <p class="subtitle">
      <strong>{ctx['signer_name']}</strong> has declined the NDA.
    </p>

    <div class="info-box">
      <div class="info-row"><span class="info-label">Signer</span><span class="info-value">{ctx['signer_name']} ({ctx['signer_email']})</span></div>
      <div class="info-row"><span class="info-label">Document</span><span class="info-value">{ctx['nda_name']} v{ctx['nda_version']}</span></div>
      <div class="info-row"><span class="info-label">Reason</span><span class="info-value warn">{assignment.decline_reason or 'No reason provided'}</span></div>
    </div>

    <div class="cta"><a href="{ctx['frontend_url']}/assignments">View in NDA Shield →</a></div>
    """

    html = _email_wrapper(content, ctx["company_name"])
    return _send(
        subject=f"❌ {ctx['signer_name']} declined '{ctx['nda_name']}'",
        to_email=assignment.assigned_by.email,
        html_body=html,
    )
