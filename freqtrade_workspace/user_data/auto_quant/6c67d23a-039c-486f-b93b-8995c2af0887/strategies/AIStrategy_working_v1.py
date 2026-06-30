from freqtrade.strategy import IntParameter, DecimalParameter, CategoricalParameter, IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np


class AIStrategy(IStrategy):
    INTERFACE_VERSION: int = 3

    minimal_roi = {
        "0": 0.08,
        "30": 0.04,
        "60": 0.02,
        "120": 0,
    }

    stoploss = -0.05
    timeframe = "5m"
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True
    process_only_new_candles = True
    startup_candle_count = 100

    entry_logic = CategoricalParameter(
        ["macd_rsi", "ema_cross", "bb_bounce"],
        default="macd_rsi",
        space="buy",
        optimize=True,
    )

    rsi_buy  = IntParameter(25, 55, default=35, space="buy",  optimize=True)
    rsi_sell = IntParameter(55, 80, default=65, space="sell", optimize=True)

    ema_fast = IntParameter(5, 20,  default=8,  space="buy", optimize=True)
    ema_slow = IntParameter(20, 60, default=21, space="buy", optimize=True)

    bb_std   = DecimalParameter(1.5, 3.0, default=2.0, space="buy", optimize=False)

    macd_hist_min = DecimalParameter(0.0, 0.005, default=0.0005, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"]       = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"]   = macd["macdhist"]

        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)

        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=self.bb_std.value
        )
        dataframe["bb_lower"] = bollinger["lower"]
        dataframe["bb_upper"] = bollinger["upper"]
        dataframe["bb_mid"]   = bollinger["mid"]

        dataframe["volume_ma"] = dataframe["volume"].rolling(window=20, min_periods=1).mean()

        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        logic = self.entry_logic.value

        if logic == "macd_rsi":
            cond = (
                qtpylib.crossed_above(dataframe["macd"], dataframe["macdsignal"])
                & (dataframe["macdhist"] > self.macd_hist_min.value)
                & (dataframe["rsi"] < self.rsi_buy.value + 30)
                & (dataframe["volume"] > 0)
            )
        elif logic == "ema_cross":
            cond = (
                qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])
                & (dataframe["rsi"] < self.rsi_buy.value + 35)
                & (dataframe["volume"] > dataframe["volume_ma"] * 0.8)
            )
        else:
            cond = (
                (dataframe["close"] < dataframe["bb_lower"] * 1.005)
                & (dataframe["rsi"] < self.rsi_buy.value)
                & (dataframe["volume"] > 0)
            )

        dataframe.loc[cond, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rsi"] > self.rsi_sell.value)
            & (dataframe["volume"] > 0),
            "exit_long",
        ] = 1
        return dataframe
