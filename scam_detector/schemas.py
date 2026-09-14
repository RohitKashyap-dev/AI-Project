from typing import List, Literal, Optional

from pydantic import BaseModel, Field

SCAM_TYPES = [
    "Phishing",
    "OTP_Fraud",
    "Reward_Manipulation",
    "Account_Suspension",
    "Urgency",
    "Fake_Authority",
    "Loan_Scam",
    "Financial_Fraud",
    "Social_Engineering",
    "SIM_Swap",
    "Tech_Support_Scam",
    "Subscription_Scam",
    "Job_Scam",
    "Malware_Link",
    "Charity_Scam",
    "Promotional",
    "Transactional_Notification",
    "Service_Reminder",
    "Informational_Alert",
    "Other",
]

ScamType = Literal[
    "Phishing",
    "OTP_Fraud",
    "Reward_Manipulation",
    "Account_Suspension",
    "Urgency",
    "Fake_Authority",
    "Loan_Scam",
    "Financial_Fraud",
    "Social_Engineering",
    "SIM_Swap",
    "Tech_Support_Scam",
    "Subscription_Scam",
    "Job_Scam",
    "Malware_Link",
    "Charity_Scam",
    "Promotional",
    "Transactional_Notification",
    "Service_Reminder",
    "Informational_Alert",
    "Other",
]


class ScamDetector(BaseModel):
    is_scam: Literal["Scam", "Not Scam", "Unknown"]
    scam_type: ScamType
    confidence: float = Field(ge=0.0, le=1.0)
    reply: str
    indicators: Optional[List[str]] = None
    recommended_action: Optional[Literal["ignore", "verify", "report", "delete", "block"]] = None
