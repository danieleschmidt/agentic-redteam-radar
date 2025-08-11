"""
Graceful degradation system for maintaining service availability.
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from ..utils.logger import get_logger


class DegradationLevel(Enum):
    """System degradation levels."""
    NORMAL = "normal"
    LIGHT = "light"       # Minor feature reductions
    MODERATE = "moderate" # Significant feature reductions
    SEVERE = "severe"     # Core functionality only
    EMERGENCY = "emergency" # Minimal operation


@dataclass
class DegradationRule:
    """Rule for when to trigger degradation."""
    name: str
    condition: Callable[[], bool]
    target_level: DegradationLevel
    priority: int = 0  # Higher priority rules are checked first
    cooldown: float = 300.0  # Minimum time between triggers (seconds)
    last_triggered: Optional[float] = None


@dataclass
class DegradationAction:
    """Action to take when degradation is triggered."""
    name: str
    level: DegradationLevel
    action: Callable[[], None]
    rollback_action: Optional[Callable[[], None]] = None
    description: str = ""


class DegradationManager:
    """
    Manages graceful degradation of system functionality.
    
    Monitors system conditions and automatically reduces functionality
    to maintain core operations under stress.
    """
    
    def __init__(self):
        self.logger = get_logger("agentic_redteam.reliability.degradation")
        
        # Current degradation state
        self.current_level = DegradationLevel.NORMAL
        self.degradation_start_time: Optional[float] = None
        self.active_actions: List[str] = []
        
        # Configuration
        self.degradation_rules: List[DegradationRule] = []
        self.degradation_actions: Dict[DegradationLevel, List[DegradationAction]] = {
            level: [] for level in DegradationLevel
        }
        
        # State tracking
        self.level_history: List[Dict[str, Any]] = []
        self.max_history = 100
        
        # Automatic recovery settings
        self.auto_recovery_enabled = True
        self.recovery_check_interval = 60.0  # seconds
        self.recovery_stability_period = 300.0  # 5 minutes of stability needed
        
        # Setup default rules and actions
        self._setup_default_configuration()
        
        # Recovery task
        self._recovery_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
    
    def _setup_default_configuration(self):
        """Setup default degradation rules and actions."""
        
        # Example rules (these would be customized based on actual metrics)
        def high_cpu_rule():
            """Trigger on high CPU usage."""
            try:
                import psutil
                return psutil.cpu_percent(interval=1) > 85.0
            except:
                return False
        
        def high_memory_rule():
            """Trigger on high memory usage."""
            try:
                import psutil
                return psutil.virtual_memory().percent > 90.0
            except:
                return False
        
        def error_rate_rule():
            """Trigger on high error rate."""
            # This would integrate with error monitoring
            return False  # Placeholder
        
        # Register default rules
        self.add_degradation_rule("high_cpu", high_cpu_rule, DegradationLevel.LIGHT, priority=1)
        self.add_degradation_rule("high_memory", high_memory_rule, DegradationLevel.MODERATE, priority=2)
        self.add_degradation_rule("high_errors", error_rate_rule, DegradationLevel.SEVERE, priority=3)
        
        # Default actions for each level
        self._register_default_actions()
    
    def _register_default_actions(self):
        """Register default degradation actions."""
        
        # Light degradation actions
        def reduce_scan_concurrency():
            """Reduce concurrent scan operations."""
            self.logger.info("Reducing scan concurrency for light degradation")
            # Implementation would adjust scanner concurrency settings
        
        def disable_caching():
            """Disable result caching to save memory."""
            self.logger.info("Disabling result caching for light degradation")
            # Implementation would disable cache systems
        
        self.add_degradation_action(
            DegradationLevel.LIGHT, 
            "reduce_concurrency", 
            reduce_scan_concurrency,
            description="Reduce concurrent operations to lower resource usage"
        )
        
        self.add_degradation_action(
            DegradationLevel.LIGHT,
            "disable_caching",
            disable_caching,
            description="Disable caching to conserve memory"
        )
        
        # Moderate degradation actions
        def limit_attack_patterns():
            """Limit to essential attack patterns only."""
            self.logger.info("Limiting to essential attack patterns for moderate degradation")
            # Implementation would filter attack patterns
        
        def reduce_logging():
            """Reduce logging verbosity."""
            self.logger.info("Reducing logging verbosity for moderate degradation")
            # Implementation would adjust log levels
        
        self.add_degradation_action(
            DegradationLevel.MODERATE,
            "limit_patterns",
            limit_attack_patterns,
            description="Run only essential attack patterns"
        )
        
        self.add_degradation_action(
            DegradationLevel.MODERATE,
            "reduce_logging",
            reduce_logging,
            description="Reduce logging to save I/O resources"
        )
        
        # Severe degradation actions
        def emergency_mode():
            """Enable emergency-only operations."""
            self.logger.warning("Entering emergency mode - severe degradation")
            # Implementation would disable non-essential features
        
        self.add_degradation_action(
            DegradationLevel.SEVERE,
            "emergency_mode",
            emergency_mode,
            description="Enable emergency-only operations"
        )
    
    def add_degradation_rule(self, name: str, condition: Callable[[], bool],
                           target_level: DegradationLevel, priority: int = 0,
                           cooldown: float = 300.0):
        """
        Add a degradation rule.
        
        Args:
            name: Unique name for the rule
            condition: Function that returns True when degradation should trigger
            target_level: Degradation level to activate
            priority: Rule priority (higher checked first)
            cooldown: Minimum time between triggers
        """
        rule = DegradationRule(
            name=name,
            condition=condition,
            target_level=target_level,
            priority=priority,
            cooldown=cooldown
        )
        
        self.degradation_rules.append(rule)
        self.degradation_rules.sort(key=lambda r: r.priority, reverse=True)
        
        self.logger.info(f"Added degradation rule: {name} -> {target_level.value}")
    
    def add_degradation_action(self, level: DegradationLevel, name: str,
                             action: Callable[[], None],
                             rollback_action: Optional[Callable[[], None]] = None,
                             description: str = ""):
        """
        Add a degradation action for a specific level.
        
        Args:
            level: Degradation level this action applies to
            name: Unique name for the action
            action: Function to execute when degrading to this level
            rollback_action: Optional function to execute when recovering
            description: Human-readable description
        """
        degradation_action = DegradationAction(
            name=name,
            level=level,
            action=action,
            rollback_action=rollback_action,
            description=description
        )
        
        self.degradation_actions[level].append(degradation_action)
        self.logger.info(f"Added degradation action: {name} for level {level.value}")
    
    async def start_monitoring(self):
        """Start automatic degradation monitoring."""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._recovery_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Degradation monitoring started")
    
    async def stop_monitoring(self):
        """Stop degradation monitoring."""
        self._is_monitoring = False
        
        if self._recovery_task:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Degradation monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for automatic degradation."""
        while self._is_monitoring:
            try:
                # Check for degradation triggers
                await self._check_degradation_rules()
                
                # Check for recovery opportunities
                if self.current_level != DegradationLevel.NORMAL:
                    await self._check_recovery_conditions()
                
                # Sleep before next check
                await asyncio.sleep(self.recovery_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in degradation monitoring loop: {e}")
                await asyncio.sleep(30)  # Back off on error
    
    async def _check_degradation_rules(self):
        """Check all degradation rules and apply highest priority match."""
        current_time = time.time()
        target_level = DegradationLevel.NORMAL
        triggered_rule = None
        
        # Check rules in priority order
        for rule in self.degradation_rules:
            # Skip if in cooldown
            if (rule.last_triggered and 
                current_time - rule.last_triggered < rule.cooldown):
                continue
            
            try:
                if rule.condition():
                    # Rule triggered - use highest severity level found
                    if (target_level == DegradationLevel.NORMAL or 
                        rule.target_level.value > target_level.value):
                        target_level = rule.target_level
                        triggered_rule = rule
            
            except Exception as e:
                self.logger.error(f"Error evaluating degradation rule {rule.name}: {e}")
        
        # Apply degradation if needed
        if target_level != self.current_level:
            if triggered_rule:
                triggered_rule.last_triggered = current_time
            
            await self._apply_degradation(target_level, triggered_rule)
    
    async def _check_recovery_conditions(self):
        """Check if system can recover from current degradation level."""
        if not self.auto_recovery_enabled:
            return
        
        # Check if conditions are stable for recovery
        current_time = time.time()
        
        # Need minimum stability period since last degradation
        if (self.degradation_start_time and 
            current_time - self.degradation_start_time < self.recovery_stability_period):
            return
        
        # Check if any rules are still triggering
        for rule in self.degradation_rules:
            try:
                if rule.condition():
                    # Still have triggering conditions - no recovery yet
                    return
            except Exception as e:
                self.logger.error(f"Error checking recovery condition {rule.name}: {e}")
                # Assume condition is still active on error (safer)
                return
        
        # All conditions clear - attempt recovery
        self.logger.info("Recovery conditions met - attempting to restore normal operation")
        await self._apply_degradation(DegradationLevel.NORMAL, None)
    
    async def _apply_degradation(self, target_level: DegradationLevel, 
                               triggered_rule: Optional[DegradationRule]):
        """Apply degradation to target level."""
        previous_level = self.current_level
        
        if target_level == previous_level:
            return
        
        # Log the change
        if triggered_rule:
            self.logger.warning(
                f"Degradation triggered by rule '{triggered_rule.name}': "
                f"{previous_level.value} -> {target_level.value}"
            )
        else:
            self.logger.info(f"Degradation level change: {previous_level.value} -> {target_level.value}")
        
        # Record in history
        change_record = {
            "timestamp": time.time(),
            "from_level": previous_level.value,
            "to_level": target_level.value,
            "triggered_by": triggered_rule.name if triggered_rule else "recovery",
            "reason": f"Rule '{triggered_rule.name}' triggered" if triggered_rule else "Automatic recovery"
        }
        
        self.level_history.append(change_record)
        if len(self.level_history) > self.max_history:
            self.level_history.pop(0)
        
        # Update state
        self.current_level = target_level
        if target_level != DegradationLevel.NORMAL and previous_level == DegradationLevel.NORMAL:
            self.degradation_start_time = time.time()
        elif target_level == DegradationLevel.NORMAL:
            self.degradation_start_time = None
        
        # Apply actions
        if target_level != DegradationLevel.NORMAL:
            # Apply degradation actions
            await self._apply_level_actions(target_level)
        else:
            # Recovery - rollback actions
            await self._rollback_active_actions()
    
    async def _apply_level_actions(self, level: DegradationLevel):
        """Apply all actions for a degradation level."""
        actions = self.degradation_actions.get(level, [])
        
        for action in actions:
            try:
                self.logger.info(f"Applying degradation action: {action.name}")
                action.action()
                self.active_actions.append(action.name)
                
            except Exception as e:
                self.logger.error(f"Failed to apply degradation action {action.name}: {e}")
    
    async def _rollback_active_actions(self):
        """Rollback all active degradation actions."""
        for action_name in self.active_actions[:]:
            # Find the action to rollback
            for level_actions in self.degradation_actions.values():
                for action in level_actions:
                    if action.name == action_name and action.rollback_action:
                        try:
                            self.logger.info(f"Rolling back degradation action: {action.name}")
                            action.rollback_action()
                            self.active_actions.remove(action_name)
                            
                        except Exception as e:
                            self.logger.error(f"Failed to rollback action {action.name}: {e}")
                        break
        
        # Clear any remaining active actions
        self.active_actions.clear()
    
    def force_degradation(self, level: DegradationLevel, reason: str = "Manual override"):
        """Manually force degradation to a specific level."""
        self.logger.warning(f"Manual degradation override: {reason}")
        
        # Create a manual rule for tracking
        manual_rule = DegradationRule(
            name="manual_override",
            condition=lambda: True,  # Always true for manual
            target_level=level,
            priority=999  # Highest priority
        )
        
        asyncio.create_task(self._apply_degradation(level, manual_rule))
    
    def force_recovery(self, reason: str = "Manual recovery"):
        """Manually force recovery to normal level."""
        self.logger.info(f"Manual recovery override: {reason}")
        asyncio.create_task(self._apply_degradation(DegradationLevel.NORMAL, None))
    
    def get_degradation_status(self) -> Dict[str, Any]:
        """Get current degradation status and history."""
        current_time = time.time()
        
        # Calculate degradation duration
        duration = None
        if self.degradation_start_time:
            duration = current_time - self.degradation_start_time
        
        return {
            "current_level": self.current_level.value,
            "degradation_duration": duration,
            "active_actions": self.active_actions.copy(),
            "auto_recovery_enabled": self.auto_recovery_enabled,
            "total_rules": len(self.degradation_rules),
            "recent_changes": self.level_history[-5:],  # Last 5 changes
            "monitoring_active": self._is_monitoring
        }
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of degradation configuration."""
        rules_summary = [
            {
                "name": rule.name,
                "target_level": rule.target_level.value,
                "priority": rule.priority,
                "cooldown": rule.cooldown,
                "last_triggered": rule.last_triggered
            }
            for rule in self.degradation_rules
        ]
        
        actions_summary = {}
        for level, actions in self.degradation_actions.items():
            actions_summary[level.value] = [
                {
                    "name": action.name,
                    "description": action.description,
                    "has_rollback": action.rollback_action is not None
                }
                for action in actions
            ]
        
        return {
            "rules": rules_summary,
            "actions": actions_summary,
            "levels": [level.value for level in DegradationLevel]
        }