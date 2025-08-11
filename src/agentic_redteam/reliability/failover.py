"""
Failover management for high availability operations.
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import time
from ..utils.logger import get_logger


class FailoverState(Enum):
    """Failover system states."""
    ACTIVE = "active"
    STANDBY = "standby" 
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class FailoverStrategy:
    """Configuration for failover behavior."""
    name: str
    primary_handler: Callable
    fallback_handlers: List[Callable]
    health_check: Optional[Callable[[], bool]] = None
    max_retries: int = 3
    retry_delay: float = 1.0
    failure_threshold: int = 5


class FailoverManager:
    """
    Manages failover between primary and backup systems.
    """
    
    def __init__(self):
        self.logger = get_logger("agentic_redteam.reliability.failover")
        self.strategies: Dict[str, FailoverStrategy] = {}
        self.state = FailoverState.ACTIVE
        
    def register_strategy(self, strategy: FailoverStrategy):
        """Register a failover strategy."""
        self.strategies[strategy.name] = strategy
        self.logger.info(f"Registered failover strategy: {strategy.name}")
    
    async def execute_with_failover(self, strategy_name: str, *args, **kwargs):
        """Execute operation with failover protection."""
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        strategy = self.strategies[strategy_name]
        
        # Try primary handler first
        try:
            return await strategy.primary_handler(*args, **kwargs)
        except Exception as e:
            self.logger.warning(f"Primary handler failed for {strategy_name}: {e}")
            
            # Try fallback handlers
            for i, fallback in enumerate(strategy.fallback_handlers):
                try:
                    self.logger.info(f"Trying fallback handler {i+1} for {strategy_name}")
                    return await fallback(*args, **kwargs)
                except Exception as fallback_error:
                    self.logger.warning(f"Fallback handler {i+1} failed: {fallback_error}")
                    continue
            
            # All handlers failed
            raise Exception(f"All handlers failed for strategy {strategy_name}")