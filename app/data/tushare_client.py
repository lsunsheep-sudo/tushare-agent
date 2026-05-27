import time
import hashlib
import json
from datetime import datetime, timedelta
import pandas as pd
import tushare as ts


class TushareClient:
    def __init__(self, token: str):
        self._token = token
        self._pro = None
        self._last_call = 0.0
        self._min_interval = 0.2

    @property
    def pro(self):
        if self._pro is None:
            self._pro = ts.pro_api(self._token)
        return self._pro

    def _rate_limit(self):
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()

    @staticmethod
    def _format_ts_code(code: str) -> str:
        code = code.strip().upper()
        if "." in code:
            return code
        if code.startswith(("6", "68")):
            return f"{code}.SH"
        if code.startswith(("0", "3")):
            return f"{code}.SZ"
        return code

    @staticmethod
    def _cache_key(method: str, **kwargs) -> str:
        raw = f"{method}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _call_with_retry(self, func, max_retries: int = 3, **kwargs) -> pd.DataFrame:
        self._rate_limit()
        for attempt in range(max_retries):
            try:
                result = func(**kwargs)
                if result is not None and not result.empty:
                    return result
                return pd.DataFrame()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1 * (attempt + 1))
        return pd.DataFrame()

    def get_stock_basic(self, exchange: str = "", list_status: str = "L") -> pd.DataFrame:
        kwargs = {"list_status": list_status}
        if exchange:
            kwargs["exchange"] = exchange
        return self._call_with_retry(self.pro.stock_basic, **kwargs)

    def get_daily_basic(
        self, ts_code: str = "", trade_date: str = "",
        start_date: str = "", end_date: str = ""
    ) -> pd.DataFrame:
        kwargs = {}
        if ts_code:
            kwargs["ts_code"] = ts_code
        if trade_date:
            kwargs["trade_date"] = trade_date
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        return self._call_with_retry(self.pro.daily_basic, **kwargs)

    def get_fina_indicator(
        self, ts_code: str = "", period: str = "",
        start_date: str = "", end_date: str = ""
    ) -> pd.DataFrame:
        kwargs = {}
        if ts_code:
            kwargs["ts_code"] = ts_code
        if period:
            kwargs["period"] = period
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        kwargs["fields"] = "ts_code,ann_date,end_date,roe,roa,grossprofit_margin,netprofit_margin,debt_to_assets,eps,dt_netprofit_yoy,or_yoy"
        return self._call_with_retry(self.pro.fina_indicator, **kwargs)

    def get_income(
        self, ts_code: str = "", period: str = "",
        start_date: str = "", end_date: str = ""
    ) -> pd.DataFrame:
        kwargs = {}
        if ts_code:
            kwargs["ts_code"] = ts_code
        if period:
            kwargs["period"] = period
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        kwargs["fields"] = "ts_code,ann_date,end_date,revenue,operate_profit,total_profit,n_income,basic_eps"
        return self._call_with_retry(self.pro.income, **kwargs)

    def get_daily(
        self, ts_code: str = "", trade_date: str = "",
        start_date: str = "", end_date: str = ""
    ) -> pd.DataFrame:
        kwargs = {}
        if ts_code:
            kwargs["ts_code"] = ts_code
        if trade_date:
            kwargs["trade_date"] = trade_date
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        return self._call_with_retry(self.pro.daily, **kwargs)

    def get_moneyflow(
        self, ts_code: str = "", trade_date: str = "",
        start_date: str = "", end_date: str = ""
    ) -> pd.DataFrame:
        kwargs = {}
        if ts_code:
            kwargs["ts_code"] = ts_code
        if trade_date:
            kwargs["trade_date"] = trade_date
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        return self._call_with_retry(self.pro.moneyflow, **kwargs)

    def get_limit_list_d(
        self, trade_date: str = "", ts_code: str = "",
        limit_type: str = ""
    ) -> pd.DataFrame:
        kwargs = {}
        if trade_date:
            kwargs["trade_date"] = trade_date
        if ts_code:
            kwargs["ts_code"] = ts_code
        if limit_type:
            kwargs["limit_type"] = limit_type
        return self._call_with_retry(self.pro.limit_list_d, **kwargs)

    def get_trade_cal(self, exchange: str = "", start_date: str = "", end_date: str = "") -> pd.DataFrame:
        kwargs = {"is_open": "1"}
        if exchange:
            kwargs["exchange"] = exchange
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        return self._call_with_retry(self.pro.trade_cal, **kwargs)

    def get_latest_trade_date(self) -> str:
        today = datetime.now()
        cal = self.get_trade_cal(
            exchange="SSE",
            start_date=(today - timedelta(days=10)).strftime("%Y%m%d"),
            end_date=today.strftime("%Y%m%d"),
        )
        if not cal.empty:
            return str(cal["cal_date"].max())
        return today.strftime("%Y%m%d")
