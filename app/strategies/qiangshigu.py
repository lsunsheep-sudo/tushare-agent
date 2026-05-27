"""
强势股回调战法策略

核心逻辑：
  1. "最近13天曾大涨30%" = 13天内最高价相比13天前收盘价涨>=30%，且高点在最近3天之前
  2. "最近3天从高点回调15%" = 最近3天最低价相比"13天内最高价"下跌>=15%
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from app.strategies.base import BaseStrategy, StrategyParams

logger = logging.getLogger(__name__)

API_DELAY = 0.15

# 评分权重
SCORE_WAVE_WEIGHT = 0.35
SCORE_PULLBACK_WEIGHT = 0.35
SCORE_POSITION_WEIGHT = 0.20
SCORE_LIMIT_UP_WEIGHT = 0.10
SCORE_LIMIT_UP_CAP = 5
SCORE_LIMIT_UP_MULTIPLIER = 2


@dataclass
class QiangshiguParams(StrategyParams):
    """强势股回调战法参数"""
    # 第一波观察窗口
    WAVE_DAYS: int = 13
    # 最小涨幅
    WAVE_MIN_GAIN: float = 0.30
    # 回调观察窗口
    PULLBACK_DAYS: int = 3
    # 最小回调幅度
    PULLBACK_MIN_PCT: float = 0.15
    # 最小成交额（亿元）
    MIN_AMOUNT: float = 0.3
    # 最大总涨幅
    MAX_TOTAL_RISE: float = 2.0

    name: str = "强势股回调战法"
    description: str = "筛选13天内涨幅>=30%且近3天回调>=15%的强势股"


class QiangshiguStrategy(BaseStrategy):
    """强势股回调战法"""

    def __init__(self):
        self.params = QiangshiguParams()
        self._cache: dict[str, pd.DataFrame] = {}

    def _get_all_stocks(self, pro) -> pd.DataFrame:
        """获取所有上市股票（含北交所），过滤上市不足60天的新股"""
        df_main = pro.stock_basic(
            exchange="", list_status="L", fields="ts_code,name,market,list_date"
        )
        try:
            df_bj = pro.stock_basic(
                exchange="BJ", list_status="L", fields="ts_code,name,market,list_date"
            )
        except Exception:
            df_bj = pd.DataFrame()
        df = pd.concat([df_main, df_bj], ignore_index=True)
        df = df.drop_duplicates(subset=["ts_code"])
        today = datetime.now().strftime("%Y%m%d")
        df["list_days"] = (pd.to_datetime(today) - pd.to_datetime(df["list_date"])).dt.days
        df = df[df["list_days"] >= 60].copy()
        time.sleep(API_DELAY)
        return df

    def _get_stock_data(self, pro, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取日线数据，带缓存和重试"""
        cache_key = ts_code
        if cache_key in self._cache:
            return self._cache[cache_key]

        time.sleep(API_DELAY)
        try:
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            min_rows = self.params.WAVE_DAYS + self.params.PULLBACK_DAYS + 5
            if len(df) < min_rows:
                self._cache[cache_key] = pd.DataFrame()
                return pd.DataFrame()
            df = df.sort_values("trade_date").reset_index(drop=True)
            self._cache[cache_key] = df
            return df
        except Exception as e:
            err_msg = str(e)
            if "800次" in err_msg or "频率超限" in err_msg:
                logger.warning("达到API调用上限，等待60秒后重试...")
                time.sleep(60)
                return self._get_stock_data(pro, ts_code, start_date, end_date)
            logger.error("获取 %s 日线数据失败: %s", ts_code, err_msg[:200])
            self._cache[cache_key] = pd.DataFrame()
            return pd.DataFrame()

    def _get_limit_pct(self, ts_code: str) -> float:
        """根据股票代码判断涨停幅度"""
        code = ts_code.split(".")[0]
        if code.startswith(("300", "301", "688")):
            return 19.9
        if code.startswith(("430", "830", "920", "872")):
            return 29.9
        return 9.9

    def run(self, pro, start_date: str, end_date: str) -> pd.DataFrame:
        """
        执行强势股回调战法筛选

        条件A：13天内最高价相比13天前收盘价涨>=30%，且高点在最近3天之前
        条件B：近3天最低价相比13天内最高价回调>=15%
        过滤：成交额>=0.3亿, 总涨幅<=200%, 上市>=60天
        评分：wave_gain(35%) + pullback_pct(35%) + position(20%) + limit_up_count(10%)
        """
        p = self.params

        # 清空本次会话缓存
        self._cache.clear()

        logger.info("=" * 60)
        logger.info("【强势股回调战法】")
        logger.info("  条件A：最近%d天曾大涨>=%d%%（高点在3天前）", p.WAVE_DAYS, int(p.WAVE_MIN_GAIN * 100))
        logger.info("  条件B：最近%d天从高点回调>=%d%%", p.PULLBACK_DAYS, int(p.PULLBACK_MIN_PCT * 100))
        logger.info("=" * 60)

        stocks = self._get_all_stocks(pro)
        logger.info("共检测 %d 只股票，预计耗时 %.1f 分钟", len(stocks), len(stocks) * API_DELAY / 60)

        results: list[dict] = []
        count = 0

        for _, row in stocks.iterrows():
            ts_code = row["ts_code"]
            stock_name = row["name"]
            market = row.get("market", "未知")

            df = self._get_stock_data(pro, ts_code, start_date, end_date)
            if len(df) < p.WAVE_DAYS + p.PULLBACK_DAYS + 1:
                continue

            # ========== 数据切片 ==========
            # 最近13天（用于判断"曾大涨"）
            recent_wave = df.tail(p.WAVE_DAYS).copy().reset_index(drop=True)

            # 最近3天（用于判断"回调"）
            recent_pullback = df.tail(p.PULLBACK_DAYS).copy().reset_index(drop=True)

            # 13天前的那一天（作为"大涨"的起点参考）
            wave_start_idx = len(df) - p.WAVE_DAYS - 1
            if wave_start_idx < 0:
                wave_start_idx = 0
            wave_start_price = df.iloc[wave_start_idx]["close"]
            wave_start_date = df.iloc[wave_start_idx]["trade_date"]

            # ========== 条件A：最近13天曾大涨30%以上 ==========
            wave_high = recent_wave["high"].max()
            wave_high_idx = recent_wave["high"].idxmax()
            wave_high_date = recent_wave.loc[wave_high_idx, "trade_date"]

            wave_gain = (wave_high - wave_start_price) / wave_start_price

            if wave_gain < p.WAVE_MIN_GAIN:
                continue

            # 关键：13天内的最高点必须在"最近3天之前"（即第4天或更早）
            recent_pullback_dates = recent_pullback["trade_date"].tolist()
            if wave_high_date in recent_pullback_dates:
                continue

            # ========== 条件B：最近3天从高点回调15%以上 ==========
            recent3_low = recent_pullback["low"].min()
            recent3_low_idx = recent_pullback["low"].idxmin()
            recent3_low_date = recent_pullback.loc[recent3_low_idx, "trade_date"]

            pullback_pct = (wave_high - recent3_low) / wave_high

            if pullback_pct < p.PULLBACK_MIN_PCT:
                continue

            # ========== 附加过滤条件 ==========
            latest_close = df.iloc[-1]["close"]
            total_rise = (latest_close - df.iloc[0]["close"]) / df.iloc[0]["close"]
            if total_rise > p.MAX_TOTAL_RISE:
                continue

            recent_amount = df.tail(p.PULLBACK_DAYS)["amount"].mean() / 10000
            if recent_amount < p.MIN_AMOUNT:
                continue

            # ========== 计算实战指标 ==========
            # 当前位置（相对于13天高低点的百分比）
            wave_low = recent_wave["low"].min()
            if wave_high != wave_low:
                current_position = (latest_close - wave_low) / (wave_high - wave_low)
            else:
                current_position = 0

            # 最近3天收盘价跌幅（相比3天前收盘价）
            day3_ago_close = df.iloc[-(p.PULLBACK_DAYS + 1)]["close"]
            recent3_close_drop = (day3_ago_close - latest_close) / day3_ago_close

            # 涨停次数统计（13天内）
            limit_pct = self._get_limit_pct(ts_code)
            limit_up_count = (recent_wave["pct_chg"] >= limit_pct).sum()

            # ========== 评分 ==========
            score = round(
                wave_gain * 100 * SCORE_WAVE_WEIGHT
                + pullback_pct * 100 * SCORE_PULLBACK_WEIGHT
                + (100 - current_position * 100) * SCORE_POSITION_WEIGHT
                + min(limit_up_count, SCORE_LIMIT_UP_CAP) * SCORE_LIMIT_UP_MULTIPLIER * SCORE_LIMIT_UP_WEIGHT,
                2,
            )

            result = {
                "ts_code": ts_code,
                "name": stock_name,
                "market": market,
                # 时间信息
                "latest_date": df.iloc[-1]["trade_date"],
                "wave_start_date": wave_start_date,
                "wave_high_date": wave_high_date,
                "recent3_low_date": recent3_low_date,
                # 价格信息
                "latest_close": round(latest_close, 2),
                "wave_start_price": round(wave_start_price, 2),
                "wave_high": round(wave_high, 2),
                "recent3_low": round(recent3_low, 2),
                # 涨跌幅数据
                "wave_gain_pct": round(wave_gain * 100, 2),
                "pullback_pct": round(pullback_pct * 100, 2),
                "total_rise_pct": round(total_rise * 100, 2),
                "recent3_close_drop_pct": round(recent3_close_drop * 100, 2),
                "current_position_pct": round(current_position * 100, 2),
                # 量能数据
                "avg_amount_yi": round(recent_amount, 2),
                "limit_up_count": int(limit_up_count),
                # 评分
                "score": score,
            }

            results.append(result)
            logger.info(
                "  %s(%s): 13天涨%.1f%%(%s) -> 近3天回调%.1f%%(%s) -> 位置%.1f%%",
                stock_name,
                ts_code,
                result["wave_gain_pct"],
                result["wave_high_date"],
                result["pullback_pct"],
                result["recent3_low_date"],
                result["current_position_pct"],
            )

            count += 1
            if count % 100 == 0:
                logger.info("  已检测 %d/%d 只，找到 %d 只", count, len(stocks), len(results))

        df_results = pd.DataFrame(results)
        if len(df_results) > 0:
            df_results = df_results.sort_values("score", ascending=False).reset_index(drop=True)
            # 限制返回 top_n
            df_results = df_results.head(p.top_n)

        logger.info("找到 %d 只强势股，返回 Top %d", len(df_results), p.top_n)
        return df_results
