"""Alert notification backends for cronwatch."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from cronwatch.config import AlertConfig

logger = logging.getLogger(__name__)


def send_email_alert(
    alert_cfg: AlertConfig,
    job_name: str,
    reason: str,
    details: Optional[str] = None,
) -> bool:
    """Send an email alert for a job failure or missed run.

    Returns True if the email was sent successfully, False otherwise.
    """
    if not alert_cfg.email:
        logger.debug("No email recipients configured, skipping email alert.")
        return False

    subject = f"[cronwatch] Job '{job_name}' alert: {reason}"
    body_lines = [
        f"Job:    {job_name}",
        f"Reason: {reason}",
    ]
    if details:
        body_lines.append(f"Details:\n{details}")
    body = "\n".join(body_lines)

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = alert_cfg.smtp_from or "cronwatch@localhost"
    msg["To"] = ", ".join(alert_cfg.email)
    msg.attach(MIMEText(body, "plain"))

    smtp_host = alert_cfg.smtp_host or "localhost"
    smtp_port = alert_cfg.smtp_port or 25

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if alert_cfg.smtp_tls:
                server.starttls()
            if alert_cfg.smtp_user and alert_cfg.smtp_password:
                server.login(alert_cfg.smtp_user, alert_cfg.smtp_password)
            server.sendmail(msg["From"], alert_cfg.email, msg.as_string())
        logger.info("Email alert sent for job '%s' to %s", job_name, alert_cfg.email)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send email alert for job '%s': %s", job_name, exc)
        return False


def log_alert(job_name: str, reason: str, details: Optional[str] = None) -> None:
    """Fallback alert that logs to the standard logger."""
    msg = f"ALERT job='{job_name}' reason='{reason}'"
    if details:
        msg += f" details='{details}'"
    logger.warning(msg)
