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
                    reason="DRY-RUN (no UI yet)",
                    dry_run=True,
                    enabled=True,
                )
            else:
                # Future: UI automation would be invoked here
                logger.info(
                    "ENTRY signal received (no UI implementation yet)",
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
                    reason="no UI implementation yet",
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

