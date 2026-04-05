"""Services package — Facade Pattern.

Each service class orchestrates one or more providers to expose a clean,
high-level API to the CLI and UI layers.  The service layer is the only
place that is allowed to call providers directly.
"""

from finscope.services.stock_service import StockAnalysisService
from finscope.services.fund_service import FundAnalysisService

__all__ = ["StockAnalysisService", "FundAnalysisService"]
