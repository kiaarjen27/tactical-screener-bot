# patched_pandas_ta.py

try:
    from pkg_resources import get_distribution, DistributionNotFound
    __version__ = get_distribution("pandas_ta").version
except Exception:
    __version__ = "0.3.14b0"

import pandas_ta
from pandas_ta import *
from pandas_ta import indicators
from pandas_ta.utils import (
    indicators_list, indicators_dict, get_indicator, get_function, get_kwargs,
    remove_prefix, version, final_version, candle_names
)
from pandas_ta.strategy import Strategy
from pandas_ta.ta import TA

__all__ = [
    "Strategy", "TA", "indicators", "indicators_list", "indicators_dict",
    "get_indicator", "get_function", "get_kwargs", "remove_prefix", "version",
    "final_version", "candle_names"
]
