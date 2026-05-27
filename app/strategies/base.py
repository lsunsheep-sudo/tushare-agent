import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class StrategyParams:
    """策略参数基类，子类定义具体参数+默认值"""
    name: str
    description: str
    top_n: int = 20


class BaseStrategy(ABC):
    """所有策略的基类"""

    @abstractmethod
    def run(self, pro, start_date: str, end_date: str) -> pd.DataFrame:
        """执行策略，返回带 score 列的 DataFrame"""
        ...

    @property
    def name(self) -> str:
        return self.params.name
