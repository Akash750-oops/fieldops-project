import logging
from sqlalchemy.orm import Session
from app.models import Job, Technician

logger = logging.getLogger(__name__)

class CommsAgent:
    """
    Placeholder service for sending notifications to customers and dispatchers.
    In a real implementation, this would integrate with Twilio SMS, Email, or Push notifications.
    """
    
    @staticmethod
    def notify_customer_job_accepted(db: Session, job: Job, tech: Technician) -> bool:
        """
        Notify the customer that their job has been accepted and a technician is en route.
        """
        try:
            logger.info(
                f"FieldOpsAI: Sending 'EN_ROUTE' notification to customer '{job.customer_name}' "
                f"for job {job.id}. Technician: {tech.technician_name}."
            )
            # Placeholder for actual SMS/Email sending logic
            # e.g., twilio_sms.send_sms(job.contact_number, message)
            return True
        except Exception as e:
            logger.error(f"FieldOpsAI: Failed to notify customer for job {job.id}: {str(e)}")
            return False

    @staticmethod
    def notify_technician_reassignment(db: Session, job: Job, old_tech: Technician, new_tech: Technician) -> bool:
        """
        Notify the new technician that a job has been reassigned to them.
        """
        try:
            logger.info(
                f"FieldOpsAI: Sending 'REASSIGNMENT' notification to new technician '{new_tech.technician_name}' "
                f"for job {job.id} (from {old_tech.technician_name})."
            )
            return True
        except Exception as e:
            logger.error(f"FieldOpsAI: Failed to notify technician for job {job.id}: {str(e)}")
            return False


