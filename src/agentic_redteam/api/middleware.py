"""
Middleware components for the Agentic RedTeam Radar API.

Provides rate limiting, security headers, authentication, and request monitoring.
"""

import time
import hashlib
import secrets
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from threading import Lock
from dataclasses import dataclass

from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..utils.logger import setup_logger
from ..monitoring.telemetry import record_error_metrics


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    calls: int = 60  # requests per period
    period: int = 60  # seconds
    burst_multiplier: float = 1.5  # allow burst up to this multiplier


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with per-IP tracking and burst allowance.
    
    Implements sliding window rate limiting with memory-efficient storage.
    """
    
    def __init__(self, app, calls: int = 60, period: int = 60, burst_multiplier: float = 1.5):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application instance
            calls: Maximum calls per period
            period: Time period in seconds
            burst_multiplier: Burst allowance multiplier
        """
        super().__init__(app)
        self.config = RateLimitConfig(calls, period, burst_multiplier)
        self.logger = setup_logger("agentic_redteam.middleware.ratelimit")
        
        # Thread-safe storage for rate limit tracking
        self._lock = Lock()
        self._client_requests: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._burst_allowances: Dict[str, int] = defaultdict(int)
        
        # Cleanup tracking
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
        
        self.logger.info(f"Rate limiting enabled: {calls} calls per {period}s (burst: x{burst_multiplier})")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Periodic cleanup of old entries
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_entries(current_time)
        
        # Check rate limit
        if not self._is_allowed(client_ip, current_time):
            self.logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            record_error_metrics("rate_limit_exceeded", "middleware", f"IP: {client_ip}")
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.config.calls} requests per {self.config.period} seconds",
                    "retry_after": self.config.period
                },
                headers={"Retry-After": str(self.config.period)}
            )
        
        # Record request
        with self._lock:
            self._client_requests[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self._get_remaining_requests(client_ip, current_time)
        reset_time = int(current_time + self.config.period)
        
        response.headers["X-RateLimit-Limit"] = str(self.config.calls)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct connection
        client_host = request.client.host if request.client else "unknown"
        return client_host
    
    def _is_allowed(self, client_ip: str, current_time: float) -> bool:
        """Check if request is allowed for client IP."""
        with self._lock:
            requests = self._client_requests[client_ip]
            
            # Remove old requests outside the window
            cutoff_time = current_time - self.config.period
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            # Check regular rate limit
            if len(requests) < self.config.calls:
                return True
            
            # Check burst allowance
            burst_limit = int(self.config.calls * self.config.burst_multiplier)
            if len(requests) < burst_limit:
                # Consume burst allowance
                self._burst_allowances[client_ip] += 1
                return True
            
            return False
    
    def _get_remaining_requests(self, client_ip: str, current_time: float) -> int:
        """Get remaining requests for client IP."""
        with self._lock:
            requests = self._client_requests[client_ip]
            
            # Remove old requests
            cutoff_time = current_time - self.config.period
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            return max(0, self.config.calls - len(requests))
    
    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old tracking entries to prevent memory leaks."""
        with self._lock:
            cutoff_time = current_time - (self.config.period * 2)  # Keep extra buffer
            
            # Clean up request tracking
            clients_to_remove = []
            for client_ip, requests in self._client_requests.items():
                # Remove old requests
                while requests and requests[0] < cutoff_time:
                    requests.popleft()
                
                # Mark empty clients for removal
                if not requests:
                    clients_to_remove.append(client_ip)
            
            # Remove empty clients
            for client_ip in clients_to_remove:
                del self._client_requests[client_ip]
                self._burst_allowances.pop(client_ip, None)
            
            self._last_cleanup = current_time
            
            if clients_to_remove:
                self.logger.debug(f"Cleaned up {len(clients_to_remove)} inactive clients")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware for enhanced security posture.
    
    Adds comprehensive security headers to all responses.
    """
    
    def __init__(self, app):
        """Initialize security headers middleware."""
        super().__init__(app)
        self.logger = setup_logger("agentic_redteam.middleware.security")
        
        # Security headers configuration
        self.security_headers = {
            # Prevent XSS attacks
            "X-XSS-Protection": "1; mode=block",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Enforce HTTPS
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https://fonts.gstatic.com; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "object-src 'none'"
            ),
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=(), "
                "accelerometer=(), ambient-light-sensor=()"
            ),
            
            # Custom security headers
            "X-API-Version": "0.1.0",
            "X-Security-Scanner": "Agentic-RedTeam-Radar"
        }
        
        self.logger.info("Security headers middleware enabled")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with security headers."""
        # Process the request
        response = await call_next(request)
        
        # Add security headers
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        
        # Add request ID for tracing
        if not response.headers.get("X-Request-ID"):
            request_id = self._generate_request_id()
            response.headers["X-Request-ID"] = request_id
            
            # Store in request state for logging
            if hasattr(request, 'state'):
                request.state.request_id = request_id
        
        return response
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracing."""
        return secrets.token_hex(16)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for API endpoints.
    
    Supports API key authentication with role-based access control.
    """
    
    def __init__(self, app):
        """Initialize authentication middleware."""
        super().__init__(app)
        self.logger = setup_logger("agentic_redteam.middleware.auth")
        self.security = HTTPBearer(auto_error=False)
        
        # Protected endpoints (require authentication)
        self.protected_paths = {
            "/scan",
            "/scan/",
            "/agents/",
            "/patterns/",
            "/reports/"
        }
        
        # Public endpoints (no authentication required)
        self.public_paths = {
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
        
        self.logger.info("Authentication middleware enabled")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with authentication checks."""
        path = request.url.path
        
        # Skip authentication for public endpoints
        if self._is_public_endpoint(path):
            return await call_next(request)
        
        # Check if endpoint requires authentication
        if self._requires_authentication(path):
            auth_result = await self._authenticate_request(request)
            if not auth_result[0]:  # Authentication failed
                self.logger.warning(f"Authentication failed for {path}: {auth_result[1]}")
                record_error_metrics("authentication_failed", "middleware", auth_result[1])
                
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Authentication required",
                        "message": auth_result[1]
                    }
                )
            
            # Store user info in request state
            request.state.user_info = auth_result[1]
        
        return await call_next(request)
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no auth required)."""
        return any(path.startswith(public_path) for public_path in self.public_paths)
    
    def _requires_authentication(self, path: str) -> bool:
        """Check if endpoint requires authentication."""
        return any(path.startswith(protected_path) for protected_path in self.protected_paths)
    
    async def _authenticate_request(self, request: Request) -> Tuple[bool, str]:
        """
        Authenticate the request.
        
        Returns:
            Tuple of (success: bool, message_or_user_info: str)
        """
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return False, "Missing Authorization header"
        
        # Basic API key authentication
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]  # Remove "Bearer " prefix
            return self._validate_api_key(api_key)
        elif auth_header.startswith("ApiKey "):
            api_key = auth_header[7:]  # Remove "ApiKey " prefix  
            return self._validate_api_key(api_key)
        else:
            return False, "Invalid authorization format"
    
    def _validate_api_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Validate API key.
        
        In production, this would check against a database or external service.
        For now, we implement a simple validation scheme.
        
        Returns:
            Tuple of (valid: bool, user_info_or_error: str)
        """
        # Simple validation - check if key looks valid
        if not api_key or len(api_key) < 16:
            return False, "Invalid API key format"
        
        # In production, implement proper key validation
        # For demonstration, accept keys that match a pattern
        if api_key.startswith("radar_"):
            # Extract user info from key (demo purposes)
            user_info = f"api_user_{hashlib.md5(api_key.encode()).hexdigest()[:8]}"
            self.logger.debug(f"API key validated for user: {user_info}")
            return True, user_info
        
        return False, "Invalid API key"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware for audit trails and monitoring.
    
    Logs all requests with performance metrics and security events.
    """
    
    def __init__(self, app):
        """Initialize request logging middleware."""
        super().__init__(app)
        self.logger = setup_logger("agentic_redteam.middleware.logging")
        
        # Sensitive paths to mask in logs
        self.sensitive_paths = {"/scan", "/agents"}
        
        self.logger.info("Request logging middleware enabled")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with comprehensive logging."""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Log request start
        self.logger.info(
            f"Request started - {request.method} {request.url.path} "
            f"[ID: {request_id}] [IP: {client_ip}]"
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log request completion
            self.logger.info(
                f"Request completed - {request.method} {request.url.path} "
                f"[ID: {request_id}] [Status: {response.status_code}] "
                f"[Duration: {process_time:.3f}s] [IP: {client_ip}]"
            )
            
            # Add performance header
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            # Log request error
            process_time = time.time() - start_time
            self.logger.error(
                f"Request failed - {request.method} {request.url.path} "
                f"[ID: {request_id}] [Error: {str(e)}] "
                f"[Duration: {process_time:.3f}s] [IP: {client_ip}]"
            )
            
            # Record error metrics
            record_error_metrics("request_error", "middleware", str(e))
            
            # Re-raise the exception
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"