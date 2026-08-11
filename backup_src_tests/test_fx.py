import logging

from risk_dashboard.core.fx_forecast import forecast_fx_arima
    
logger = logging.getLogger(__name__)

h, f = forecast_fx_arima("EURUSD=X", period="1y", steps=10)
logger.debug("HISTORICAL (head):")
logger.debug(h.head())
logger.debug("\nFORECAST (head):")
logger.debug(f.head())

