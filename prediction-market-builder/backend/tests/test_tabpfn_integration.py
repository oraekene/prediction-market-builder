import pytest
import numpy as np
from app.services.tabpfn_integration import TabPFNQuantileEstimator


@pytest.fixture
def estimator():
    return TabPFNQuantileEstimator()


@pytest.mark.asyncio
async def test_fallback_when_tabpfn_not_available(estimator):
    returns = list(np.random.normal(0.001, 0.02, 100))
    var = await estimator.estimate_var(returns=returns, confidence=0.95)
    assert isinstance(var, float)
    assert var > 0


@pytest.mark.asyncio
async def test_estimate_var_returns_zero_for_empty(estimator):
    var = await estimator.estimate_var(returns=[], confidence=0.95)
    assert var == 0.0


@pytest.mark.asyncio
async def test_estimate_var_different_confidence(estimator):
    returns = list(np.random.normal(0.001, 0.02, 100))
    var_95 = await estimator.estimate_var(returns=returns, confidence=0.95)
    var_99 = await estimator.estimate_var(returns=returns, confidence=0.99)
    assert var_99 >= var_95


@pytest.mark.asyncio
async def test_estimate_es(estimator):
    returns = list(np.random.normal(0.001, 0.02, 100))
    es = await estimator.estimate_es(returns=returns, confidence=0.95)
    assert isinstance(es, float)
    assert es > 0
