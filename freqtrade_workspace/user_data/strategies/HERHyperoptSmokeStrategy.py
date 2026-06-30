"""
HERHyperoptSmokeStrategy - Freqtrade Hyperopt Validation Strategy

IMPORTANT: This is a SMOKE TEST strategy ONLY for Hyperopt validation.
- NOT a profitable strategy
- NOT a production strategy
- NOT financial advice
- Used ONLY for validating HER's Hyperopt pipeline

This strategy is specifically designed to validate Hyperopt pipeline mechanics:
- Has hyperoptable buy/sell parameters
- Small parameter spaces for fast validation
- Should generate enough trades on BTC/USDT 5m 30 days
- No external network calls
- No secrets
- No live trading behavior
"""
from freqtrade.strategy import IStrategy
from pandas import DataFrame
from pandas_ta import sma, rsi
from freqtrade.strategy import IntParameter, DecimalParameter


class HERHyperoptSmokeStrategy(IStrategy):
    """
    Hyperopt smoke test strategy for validating Hyperopt pipeline.
    
    This strategy has hyperoptable parameters that Freqtrade Hyperopt can optimize.
    It uses simple indicators to ensure the HER backend can successfully:
    - Run Hyperopt with parameter spaces
    - Parse Hyperopt results
    - Persist all trials
    - Select best trial
    - Run optimized backtest
    
    Do NOT use this for actual trading.
    """
    
    # Strategy interface version
    INTERFACE_VERSION = 3
    
    # Minimal ROI - for smoke testing only
    minimal_roi = {
        "0": 0.05  # 5% ROI target (not realistic, just for testing)
    }
    
    # Stop loss - for smoke testing only
    stoploss = -0.05  # 5% stop loss (not realistic, just for testing)
    
    # Timeframe
    timeframe = '5m'
    
    # Trailing stop
    trailing_stop = False
    
    # Run this strategy only in dry_run mode
    dry_run = True
    
    # Startup candles
    startup_candle_count: int = 30
    
    # Hyperoptable parameters - buy signals
    buy_rsi = IntParameter(low=20, high=40, default=30, space='buy')
    buy_sma_fast = IntParameter(low=5, high=15, default=10, space='buy')
    buy_sma_slow = IntParameter(low=20, high=40, default=30, space='buy')
    
    # Hyperoptable parameters - sell signals
    sell_rsi = IntParameter(low=60, high=80, default=70, space='sell')
    sell_sma_fast = IntParameter(low=5, high=15, default=10, space='sell')
    sell_sma_slow = IntParameter(low=20, high=40, default=30, space='sell')
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate simple indicators for Hyperopt smoke testing.
        
        Uses basic indicators that work with Hyperopt parameter spaces.
        """
        # RSI
        dataframe['rsi'] = rsi(dataframe['close'], length=14)
        
        # Simple moving averages
        dataframe['sma_fast'] = sma(dataframe['close'], length=10)
        dataframe['sma_slow'] = sma(dataframe['close'], length=30)
        
        # Volume filter
        dataframe['volume_gt_0'] = dataframe['volume'] > 0
        
        return dataframe
    
    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Buy signal with hyperoptable parameters.
        
        Buy when:
        - RSI is below buy_rsi threshold
        - Fast SMA is above slow SMA
        - Volume is positive
        
        This is NOT a real trading signal.
        """
        dataframe.loc[
            (
                (dataframe['rsi'] < self.buy_rsi.value) &
                (dataframe['sma_fast'] > dataframe['sma_slow']) &
                (dataframe['volume_gt_0'])
            ),
            'buy'
        ] = 1
        
        return dataframe
    
    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Sell signal with hyperoptable parameters.
        
        Sell when:
        - RSI is above sell_rsi threshold
        - Fast SMA is below slow SMA
        
        This is NOT a real trading signal.
        """
        dataframe.loc[
            (
                (dataframe['rsi'] > self.sell_rsi.value) &
                (dataframe['sma_fast'] < dataframe['sma_slow'])
            ),
            'sell'
        ] = 1
        
        return dataframe
