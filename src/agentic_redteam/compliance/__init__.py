"""
Compliance module for global regulatory compliance
Supports GDPR, CCPA, PDPA, and other regional data protection regulations
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    GDPR = "gdpr"  # EU General Data Protection Regulation
    CCPA = "ccpa"  # California Consumer Privacy Act
    PDPA = "pdpa"  # Personal Data Protection Act (Singapore)
    LGPD = "lgpd"  # Lei Geral de Proteção de Dados (Brazil)
    PIPEDA = "pipeda"  # Personal Information Protection and Electronic Documents Act (Canada)
    SOC2 = "soc2"  # SOC 2 Type II
    ISO27001 = "iso27001"  # ISO 27001
    NIST = "nist"  # NIST Cybersecurity Framework


@dataclass
class DataProcessingRecord:
    """Record of data processing activities for compliance audit"""
    timestamp: str
    operation: str
    data_type: str
    purpose: str
    retention_period: str
    user_consent: bool
    data_minimization: bool
    framework: ComplianceFramework
    metadata: Dict[str, Any]


@dataclass
class PrivacySettings:
    """Privacy settings configuration"""
    data_retention_days: int = 30
    anonymize_pii: bool = True
    require_consent: bool = True
    allow_data_export: bool = True
    allow_data_deletion: bool = True
    log_access: bool = True
    encrypt_at_rest: bool = True
    encrypt_in_transit: bool = True


class ComplianceManager:
    """Manages regulatory compliance requirements"""
    
    def __init__(self, frameworks: List[ComplianceFramework] = None):
        self.frameworks = frameworks or [ComplianceFramework.GDPR]
        self.processing_log: List[DataProcessingRecord] = []
        self.privacy_settings = PrivacySettings()
        self._audit_trail = []
    
    def log_data_processing(
        self,
        operation: str,
        data_type: str,
        purpose: str,
        user_consent: bool = False,
        retention_period: str = "30 days",
        **metadata
    ):
        """Log data processing activity for compliance audit"""
        record = DataProcessingRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            operation=operation,
            data_type=data_type,
            purpose=purpose,
            retention_period=retention_period,
            user_consent=user_consent,
            data_minimization=self._check_data_minimization(data_type),
            framework=self.frameworks[0],  # Primary framework
            metadata=metadata
        )
        
        self.processing_log.append(record)
        self._audit_trail.append({
            "timestamp": record.timestamp,
            "event": "data_processing",
            "details": asdict(record)
        })
    
    def _check_data_minimization(self, data_type: str) -> bool:
        """Check if data minimization principles are followed"""
        # Implement data minimization checks
        sensitive_types = ["pii", "biometric", "financial", "health"]
        return data_type.lower() not in sensitive_types
    
    def anonymize_data(self, data: str, method: str = "hash") -> str:
        """Anonymize sensitive data for compliance"""
        if not self.privacy_settings.anonymize_pii:
            return data
        
        if method == "hash":
            return hashlib.sha256(data.encode()).hexdigest()[:16]
        elif method == "redact":
            return "*" * len(data) if len(data) <= 10 else data[:2] + "*" * (len(data) - 4) + data[-2:]
        else:
            return "[REDACTED]"
    
    def check_consent(self, user_id: str, purpose: str) -> bool:
        """Check if user has given consent for specific purpose"""
        # In real implementation, this would query a consent database
        return self.privacy_settings.require_consent
    
    def handle_data_request(self, request_type: str, user_id: str) -> Dict[str, Any]:
        """Handle GDPR/CCPA data subject requests"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if request_type == "access":
            # Right to access personal data
            user_data = self._get_user_data(user_id)
            response = {
                "status": "completed",
                "data": user_data,
                "processed_at": timestamp
            }
        elif request_type == "deletion":
            # Right to erasure (right to be forgotten)
            self._delete_user_data(user_id)
            response = {
                "status": "completed",
                "message": "User data deleted",
                "processed_at": timestamp
            }
        elif request_type == "portability":
            # Right to data portability
            user_data = self._export_user_data(user_id)
            response = {
                "status": "completed",
                "export_format": "json",
                "data": user_data,
                "processed_at": timestamp
            }
        elif request_type == "rectification":
            # Right to rectification
            response = {
                "status": "pending",
                "message": "Data rectification request received",
                "processed_at": timestamp
            }
        else:
            response = {
                "status": "error",
                "message": f"Unknown request type: {request_type}",
                "processed_at": timestamp
            }
        
        # Log the request handling
        self.log_data_processing(
            operation=f"data_request_{request_type}",
            data_type="personal_data",
            purpose="legal_compliance",
            user_consent=True,
            user_id=user_id,
            response_status=response["status"]
        )
        
        return response
    
    def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Retrieve all data associated with a user"""
        # Filter processing log for this user
        user_records = [
            record for record in self.processing_log
            if record.metadata.get("user_id") == user_id
        ]
        
        return {
            "user_id": user_id,
            "processing_records": [asdict(record) for record in user_records],
            "data_types_processed": list(set(record.data_type for record in user_records))
        }
    
    def _delete_user_data(self, user_id: str):
        """Delete all data associated with a user"""
        # Remove user records from processing log
        self.processing_log = [
            record for record in self.processing_log
            if record.metadata.get("user_id") != user_id
        ]
        
        # Add deletion audit entry
        self._audit_trail.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "user_data_deletion",
            "user_id": user_id,
            "compliant": True
        })
    
    def _export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export user data in portable format"""
        user_data = self._get_user_data(user_id)
        user_data["export_timestamp"] = datetime.now(timezone.utc).isoformat()
        user_data["export_format"] = "json"
        user_data["compliance_frameworks"] = [f.value for f in self.frameworks]
        return user_data
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report for audit purposes"""
        total_records = len(self.processing_log)
        consented_records = sum(1 for r in self.processing_log if r.user_consent)
        minimized_records = sum(1 for r in self.processing_log if r.data_minimization)
        
        framework_compliance = {}
        for framework in self.frameworks:
            framework_compliance[framework.value] = self._assess_framework_compliance(framework)
        
        report = {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "compliance_frameworks": [f.value for f in self.frameworks],
            "summary": {
                "total_processing_records": total_records,
                "consent_rate": consented_records / total_records if total_records > 0 else 0,
                "data_minimization_rate": minimized_records / total_records if total_records > 0 else 0,
                "audit_trail_entries": len(self._audit_trail)
            },
            "framework_compliance": framework_compliance,
            "privacy_settings": asdict(self.privacy_settings),
            "recent_data_requests": self._get_recent_data_requests(),
            "recommendations": self._generate_compliance_recommendations()
        }
        
        return report
    
    def _assess_framework_compliance(self, framework: ComplianceFramework) -> Dict[str, Any]:
        """Assess compliance with specific framework"""
        compliance_score = 0.0
        total_checks = 0
        
        if framework == ComplianceFramework.GDPR:
            # GDPR compliance checks
            checks = {
                "consent_mechanism": self.privacy_settings.require_consent,
                "data_minimization": any(r.data_minimization for r in self.processing_log),
                "right_to_erasure": self.privacy_settings.allow_data_deletion,
                "data_portability": self.privacy_settings.allow_data_export,
                "encryption_at_rest": self.privacy_settings.encrypt_at_rest,
                "access_logging": self.privacy_settings.log_access
            }
        elif framework == ComplianceFramework.CCPA:
            # CCPA compliance checks
            checks = {
                "right_to_know": True,  # Data transparency
                "right_to_delete": self.privacy_settings.allow_data_deletion,
                "right_to_opt_out": True,  # Opt-out of sale
                "non_discrimination": True,  # No discrimination for exercising rights
                "data_minimization": any(r.data_minimization for r in self.processing_log)
            }
        else:
            # Default checks for other frameworks
            checks = {
                "data_protection": self.privacy_settings.encrypt_at_rest,
                "access_control": self.privacy_settings.log_access,
                "consent": self.privacy_settings.require_consent
            }
        
        total_checks = len(checks)
        compliance_score = sum(checks.values()) / total_checks if total_checks > 0 else 0
        
        return {
            "framework": framework.value,
            "compliance_score": compliance_score,
            "status": "compliant" if compliance_score >= 0.8 else "needs_attention",
            "checks": checks,
            "last_assessment": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_recent_data_requests(self) -> List[Dict[str, Any]]:
        """Get recent data subject requests"""
        recent_requests = [
            entry for entry in self._audit_trail
            if entry.get("event", "").startswith("data_request_")
        ]
        return recent_requests[-10:]  # Last 10 requests
    
    def _generate_compliance_recommendations(self) -> List[str]:
        """Generate recommendations for improving compliance"""
        recommendations = []
        
        if not self.privacy_settings.encrypt_at_rest:
            recommendations.append("Enable encryption at rest for sensitive data")
        
        if not self.privacy_settings.require_consent:
            recommendations.append("Implement user consent mechanisms")
        
        consent_rate = sum(1 for r in self.processing_log if r.user_consent) / len(self.processing_log) if self.processing_log else 0
        if consent_rate < 0.8:
            recommendations.append("Improve consent collection rate")
        
        if not any(r.data_minimization for r in self.processing_log):
            recommendations.append("Implement data minimization practices")
        
        return recommendations


# Global compliance manager
_compliance_manager = ComplianceManager()

def get_compliance_manager() -> ComplianceManager:
    """Get global compliance manager instance"""
    return _compliance_manager

def log_processing(operation: str, data_type: str, purpose: str, **kwargs):
    """Log data processing activity"""
    _compliance_manager.log_data_processing(operation, data_type, purpose, **kwargs)

def handle_request(request_type: str, user_id: str) -> Dict[str, Any]:
    """Handle data subject request"""
    return _compliance_manager.handle_data_request(request_type, user_id)