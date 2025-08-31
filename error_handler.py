"""Enhanced Error Handler for Python"""

class AppError(Exception):
    """Application-specific error"""
    def __init__(self, message, code=500):
        self.message = message
        self.code = code
        super().__init__(self.message)
