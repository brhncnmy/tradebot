"""Trade executor for PocketOption signals."""

from app.config import PocketOptionBotConfig
from app.logging_config import get_logger
from app.models.pocketoption import (
    PocketOptionDirection,
    PocketOptionSignal,
    PocketOptionSignalType,
    TradeResult,
)

logger = get_logger("trade-executor")


class TradeExecutor:
    """Executes PocketOption trades based on signals."""
    
    def __init__(self, config: PocketOptionBotConfig):
        """
        Initialize the trade executor.
        
        Args:
            config: PocketOption bot configuration
        """
        self.config = config
    
    def execute(self, signal: PocketOptionSignal) -> TradeResult:
        """
        Execute a trade based on the signal.
        
        Args:
            signal: PocketOptionSignal to execute
            
        Returns:
            TradeResult indicating the outcome
        """
        # Check if bot is enabled
        if not self.config.enabled:
            logger.warning("PocketOption bot is disabled")
            return TradeResult(
                status="skipped",
                reason="PocketOption bot disabled",
                dry_run=self.config.dry_run,
                enabled=False,
            )
        
        # Handle PREPARE signals
        if signal.signal_type == PocketOptionSignalType.PREPARE:
            logger.info(
                "PREPARE signal received",
                extra={
                    "asset": signal.asset,
                    "message_id": signal.raw_message_id,
                }
            )
            return TradeResult(
                status="accepted",
                reason="prepare only (no UI yet)",
                dry_run=self.config.dry_run,
                enabled=True,
            )
        
        # Handle ENTRY signals
        if signal.signal_type == PocketOptionSignalType.ENTRY:
            # Determine stake
            stake = self.config.base_stake
            
            # Apply max stake limit if set
            if self.config.max_stake_per_trade is not None:
                if stake > self.config.max_stake_per_trade:
                    logger.warning(
                        "Stake exceeds max_stake_per_trade, clamping",
                        extra={
                            "stake": stake,
                            "max_stake": self.config.max_stake_per_trade,
                        }
                    )
                    stake = self.config.max_stake_per_trade
            
            # Get normalized direction
            direction = signal.normalized_direction
            direction_str = direction.value if direction else None
            
            if self.config.dry_run:
                logger.info(
                    "DRY-RUN: ENTRY signal would be executed",
                    extra={
                        "asset": signal.asset,
                        "duration_minutes": signal.duration_minutes,
                        "direction": direction_str,
                        "stake": stake,
                        "account_type": self.config.account_type,
                        "message_id": signal.raw_message_id,
                    }
                )
                return TradeResult(
                    status="accepted",
                    reason="DRY-RUN (no UI calls)",
                    dry_run=True,
                    enabled=True,
                )
            else:
                # Non-DRY-RUN: Check if UI is enabled
                if not self.config.ui_enabled:
                    logger.warning(
                        "ENTRY signal received but POCKETOPTION_UI_ENABLED is false",
                        extra={
                            "asset": signal.asset,
                            "duration_minutes": signal.duration_minutes,
                            "direction": direction_str,
                            "stake": stake,
                            "message_id": signal.raw_message_id,
                        }
                    )
                    return TradeResult(
                        status="error",
                        reason="UI disabled while DRY_RUN=false",
                        dry_run=False,
                        enabled=True,
                    )
                
                # UI is enabled: attempt to use UI driver
                try:
                    from app.ui_driver.playwright_driver import PocketOptionUIDriver
                    
                    # Initialize UI driver
                    try:
                        driver = PocketOptionUIDriver(self.config)
                    except RuntimeError as e:
                        logger.error(
                            "UI driver initialization failed",
                            extra={"error": str(e), "message_id": signal.raw_message_id},
                            exc_info=True,
                        )
                        return TradeResult(
                            status="error",
                            reason="UI driver initialization failed",
                            dry_run=False,
                            enabled=True,
                        )
                    
                    # Execute trade via UI
                    try:
                        driver.place_entry_trade(
                            asset=signal.asset or "",
                            duration_minutes=signal.duration_minutes or 0,
                            direction=direction,
                            stake=stake,
                        )
                        logger.info(
                            "ENTRY trade executed via UI",
                            extra={
                                "asset": signal.asset,
                                "duration_minutes": signal.duration_minutes,
                                "direction": direction_str,
                                "stake": stake,
                                "message_id": signal.raw_message_id,
                            }
                        )
                        return TradeResult(
                            status="accepted",
                            reason="ENTRY executed via UI",
                            dry_run=False,
                            enabled=True,
                        )
                    except Exception as e:
                        logger.error(
                            "UI trade execution failed",
                            extra={
                                "error": str(e),
                                "asset": signal.asset,
                                "duration_minutes": signal.duration_minutes,
                                "direction": direction_str,
                                "stake": stake,
                                "message_id": signal.raw_message_id,
                            },
                            exc_info=True,
                        )
                        return TradeResult(
                            status="error",
                            reason="UI trade execution failed",
                            dry_run=False,
                            enabled=True,
                        )
                except ImportError as e:
                    logger.error(
                        "Failed to import UI driver",
                        extra={"error": str(e), "message_id": signal.raw_message_id},
                        exc_info=True,
                    )
                    return TradeResult(
                        status="error",
                        reason="UI driver not available",
                        dry_run=False,
                        enabled=True,
                    )
        
        # Handle REPEAT_X2 signals
        if signal.signal_type == PocketOptionSignalType.REPEAT_X2:
            logger.info(
                "REPEAT_X2 signal received",
                extra={
                    "amount_multiplier": signal.amount_multiplier,
                    "message_id": signal.raw_message_id,
                }
            )
            return TradeResult(
                status="accepted",
                reason="repeat not implemented (no UI yet)",
                dry_run=self.config.dry_run,
                enabled=True,
            )
        
        # Unknown signal type
        logger.error(
            "Unknown signal type",
            extra={
                "signal_type": signal.signal_type.value if signal.signal_type else None,
                "message_id": signal.raw_message_id,
            }
        )
        return TradeResult(
            status="error",
            reason=f"Unknown signal type: {signal.signal_type}",
            dry_run=self.config.dry_run,
            enabled=self.config.enabled,
        )

