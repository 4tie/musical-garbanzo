"""
HERSmokeStrategy - Freqtrade Integration Smoke Test Strategy

IMPORTANT: This is a SMOKE TEST strategy ONLY.
- NOT a profitable strategy
- NOT a production strategy
- NOT financial advice
- Used ONLY for validating HER's Freqtrade integration

This strategy is intentionally simple to test the integration pipeline
without requiring complex dependencies or advanced indicators.
"""
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd


class HERSmokeStrategy(IStrategy):
    """
    Simple smoke test strategy for Freqtrade integration validation.
    
    This strategy uses basic moving average crossover logic to ensure
    the HER backend can successfully:
    - Detect strategies
    - Generate configs
    - Download data
    - Run backtests
    
    Do NOT use this for actual trading.
    """
    
    # Strategy interface version
    INTERFACE_VERSION = 3
    
    # Minimal ROI - for smoke testing only
    minimal_roi = {
        "0": 0.10  # 10% ROI target (not realistic, just for testing)
    }
    
    # Stop loss - for smoke testing only
    stoploss = -0.10  # 10% stop loss (not realistic, just for testing)
    
    # Timeframe
    timeframe = '5m'
    
    # Trailing stop
    trailing_stop = False
    
    # Run this strategy only in dry_run mode
    dry_run = True
    
    # Startup candles
    startup_candle_count: int = 30
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate simple indicators for smoke testing.
        
        Uses only basic pandas operations to avoid dependency issues.
        """
        # Simple moving averages
        dataframe['sma_fast'] = dataframe['close'].rolling(window=10).mean()
        dataframe['sma_slow'] = dataframe['close'].rolling(window=30).mean()
        
        # Volume filter
        dataframe['volume_gt_0'] = dataframe['volume'] > 0
        
        return dataframe
    
    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Simple buy signal for smoke testing.
        
        Buy when fast SMA crosses above slow SMA and volume is positive.
        This is NOT a real trading signal.
        """
        dataframe.loc[
            (
                (dataframe['sma_fast'] > dataframe['sma_slow']) &
                (dataframe['volume_gt_0'])
            ),
            'buy'
        ] = 1
        
        return dataframe
    
    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Simple sell signal for smoke testing.
        
        Sell when fast SMA crosses below slow SMA.
        This is NOT a real trading signal.
        """
        dataframe.loc[
            (
                (dataframe['sma_fast'] < dataframe['sma_slow'])
            ),
            'sell'
        ] = 1
        
        return dataframe
