import json
from langchain_core.tools import tool
from app.data.tushare_client import TushareClient


_client: TushareClient | None = None


def set_tushare_client(client: TushareClient) -> None:
    global _client
    _client = client


def _get_client() -> TushareClient:
    if _client is None:
        raise RuntimeError("TushareClient not initialized")
    return _client


@tool
def get_stock_basic(exchange: str = "") -> str:
    """获取 A 股股票基本信息列表，包含股票代码、名称、行业、上市日期。
    参数 exchange 可选：'SSE' 上交所，'SZSE' 深交所，空字符串表示全部。"""
    client = _get_client()
    df = client.get_stock_basic(exchange=exchange)
    if df.empty:
        return json.dumps({"error": "无数据"}, ensure_ascii=False)
    subset = df[["ts_code", "name", "industry", "list_date"]].head(500).copy()
    return subset.to_json(orient="records", force_ascii=False)


@tool
def get_financial_indicators(ts_code: str, period: str = "") -> str:
    """获取指定股票的财务指标：ROE、ROA、毛利率、净利率、资产负债率、净利润同比、营收同比。
    参数 ts_code：股票代码如 '600519.SH'，period：财报期如 '20241231'。"""
    client = _get_client()
    ts_code = client._format_ts_code(ts_code)
    kwargs = {"ts_code": ts_code}
    if period:
        kwargs["period"] = period
    else:
        kwargs["start_date"] = "20230101"
    df = client.get_fina_indicator(**kwargs)
    if df.empty:
        return json.dumps({"error": f"未找到 {ts_code} 的财务数据"}, ensure_ascii=False)
    df = df.sort_values("end_date", ascending=False).head(8)
    return df.to_json(orient="records", force_ascii=False)


@tool
def get_daily_basic(ts_code: str, trade_date: str = "") -> str:
    """获取股票的日频估值数据：PE、PB、PS、总市值、流通市值、换手率。
    参数 ts_code：股票代码，trade_date：交易日期如 '20260101'，空为最新。"""
    client = _get_client()
    ts_code = client._format_ts_code(ts_code)
    if not trade_date:
        trade_date = client.get_latest_trade_date()
    df = client.get_daily_basic(ts_code=ts_code, trade_date=trade_date)
    if df.empty:
        return json.dumps({"error": f"未找到 {ts_code} 的估值数据"}, ensure_ascii=False)
    return df.head(5).to_json(orient="records", force_ascii=False)


@tool
def get_income_statement(ts_code: str, period: str = "") -> str:
    """获取利润表数据：营业收入、营业利润、净利润、基本每股收益。
    参数 ts_code：股票代码，period：报告期如 '20241231'。"""
    client = _get_client()
    ts_code = client._format_ts_code(ts_code)
    kwargs = {"ts_code": ts_code}
    if period:
        kwargs["period"] = period
    else:
        kwargs["start_date"] = "20230101"
    df = client.get_income(**kwargs)
    if df.empty:
        return json.dumps({"error": f"未找到 {ts_code} 的利润表数据"}, ensure_ascii=False)
    df = df.sort_values("end_date", ascending=False).head(8)
    return df.to_json(orient="records", force_ascii=False)


@tool
def get_industry_list() -> str:
    """获取所有 A 股行业分类列表，返回行业名称和股票数量。"""
    client = _get_client()
    df = client.get_stock_basic()
    if df.empty:
        return json.dumps({"error": "无行业数据"}, ensure_ascii=False)
    industry_counts = df.groupby("industry").size().reset_index(name="count")
    industry_counts = industry_counts.sort_values("count", ascending=False)
    return industry_counts.to_json(orient="records", force_ascii=False)


@tool
def get_daily_data(ts_code: str, start_date: str = "", end_date: str = "") -> str:
    """获取个股日线行情数据：开高低收、成交量、涨跌幅、换手率。
    参数 ts_code：股票代码如'600519.SH'，start_date/end_date：日期范围YYYYMMDD。
    返回最近60条记录。"""
    client = _get_client()
    ts_code = client._format_ts_code(ts_code)
    df = client.get_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df.empty:
        return json.dumps({"error": f"未找到 {ts_code} 的日线数据"}, ensure_ascii=False)
    df = df.sort_values("trade_date", ascending=False).head(60)
    return df.to_json(orient="records", force_ascii=False)


@tool
def get_moneyflow(ts_code: str, start_date: str = "", end_date: str = "") -> str:
    """获取个股资金流向：主力净流入、超大单净流入、小单净流入等。
    参数 ts_code：股票代码，start_date/end_date：日期范围YYYYMMDD。
    用于判断主力资金动向。"""
    client = _get_client()
    ts_code = client._format_ts_code(ts_code)
    df = client.get_moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df.empty:
        return json.dumps({"error": f"未找到 {ts_code} 的资金流向数据"}, ensure_ascii=False)
    df = df.sort_values("trade_date", ascending=False).head(60)
    return df.to_json(orient="records", force_ascii=False)


@tool
def get_limit_list(trade_date: str = "") -> str:
    """获取每日涨跌停股票列表，包含涨停/跌停/炸板股票及所属行业。
    可用于判断市场热点和炒作情绪。
    参数 trade_date：交易日期YYYYMMDD，空表示最新。"""
    client = _get_client()
    if not trade_date:
        trade_date = client.get_latest_trade_date()
    df = client.get_limit_list_d(trade_date=trade_date)
    if df.empty:
        return json.dumps({"error": f"未找到 {trade_date} 的涨跌停数据"}, ensure_ascii=False)
    return df.head(200).to_json(orient="records", force_ascii=False)


@tool
def get_trade_calendar(start_date: str, end_date: str) -> str:
    """获取交易日历，返回指定日期范围内的交易日列表。
    参数 start_date/end_date：日期格式 'YYYYMMDD'。"""
    client = _get_client()
    df = client.get_trade_cal(start_date=start_date, end_date=end_date)
    if df.empty:
        return json.dumps({"trading_days": []}, ensure_ascii=False)
    days = sorted(df["cal_date"].tolist())
    return json.dumps({"trading_days": days, "count": len(days)}, ensure_ascii=False)
