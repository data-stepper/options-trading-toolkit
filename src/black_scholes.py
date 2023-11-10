import numpy as np
from scipy.stats import norm


def standard_normal_cdf(x: float) -> float:
    """Returns the standard normal cumulative distribution function (CDF)"""
    return norm.cdf(x)


def black_scholes_option_price(
    years_to_expiry: float,
    strike: float,
    spot: float,
    volatility: float,
    interest_rate: float,
    is_call: bool,
) -> tuple[float, float, float]:
    """Returns the Black-Scholes option price, vega and delta."""

    assert years_to_expiry > 0
    assert strike > 0
    assert spot > 0
    assert volatility > 0
    assert interest_rate > 0

    # Calculate the d1 and d2 parameters
    d1 = (
                 np.log(spot / strike)
                 + (interest_rate + 0.5 * volatility**2) * years_to_expiry
    ) / (volatility * np.sqrt(years_to_expiry))
    d2 = d1 - volatility * np.sqrt(years_to_expiry)

    # Calculate the option price
    if is_call:
        price = spot * standard_normal_cdf(d1) - strike * np.exp(
            -interest_rate * years_to_expiry
        ) * standard_normal_cdf(d2)
        delta = standard_normal_cdf(d1)
        vega = spot * np.sqrt(years_to_expiry) * standard_normal_cdf(d1)
    else:
        price = strike * np.exp(-interest_rate * years_to_expiry) * standard_normal_cdf(
            -d2
        ) - spot * standard_normal_cdf(-d1)
        delta = -standard_normal_cdf(-d1)
        vega = spot * np.sqrt(years_to_expiry) * standard_normal_cdf(d1)

    return price, delta, vega
