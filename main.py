from math import floor
import matplotlib.pyplot as plt

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from src.black_scholes import black_scholes_option_price

st.title("Welcome to Option Trader's Toolkit")

# Add a textfield to enter a stock ticker
ticker = st.text_input("Enter a stock ticker", "AAPL")
eur_usd = st.number_input(
    "Enter the current EUR/USD exchange rate", value=1.0
)
risk_free_rate = st.number_input(
    "Enter the current risk free rate", value=5.5, step=0.01
)
ratio = st.number_input(
    "Enter the option ratio (i.e. how stocks per option)", value=0.1, step=0.01
)

# Get the current price of the stock
@st.cache_data
def get_90_days_history_for_ticker(ticker: str) -> pd.DataFrame:
    return yf.Ticker(ticker).history(period="90d")


price_history = get_90_days_history_for_ticker(ticker)
period_high = price_history["High"].max()
period_low = price_history["Low"].min()
historical_vola = price_history["Close"].pct_change().std() * np.sqrt(252)

last_price = price_history.iloc[-1]["Close"]

# Maybe the user wants to adjust the vola
historical_vola = st.number_input(
    "Historical Volatiliy", value=historical_vola * 100.0
)
# Or even the last price
last_price = st.number_input("Last Price", value=last_price)

# Print a small summary of the stock
summary = pd.DataFrame(
    {
        "Last Price": last_price,
        "Period High": period_high,
        "Period Low": period_low,
        "Trading Range (%)": (period_high / period_low - 1.0) * 100.0,
        "Historical Volatility (%)": historical_vola,
    },
    index=[ticker],
)
st.table(summary)

# Add a date picker to select a date
# Either by a date or by number of days from today
default_date = datetime.utcnow() + timedelta(weeks=20)
date = st.date_input("Select a date", default_date)
days_to_expiry = (date - datetime.utcnow().date()).days
st.write(f"Days to expiry: {days_to_expiry}")
bs_mu = np.exp(
    ((risk_free_rate / 100.0) - 0.5 * (historical_vola / 100.0) ** 2) * days_to_expiry / 365.0
)

f"""
Black-Scholes' Expected Price at Maturity: {bs_mu * last_price:.2f}

## Now please select a range of strikes
"""
# Let the user select a range of strikes to display
# First get a strike range step size (default 10 USD)
strike_range_step = st.number_input(
    "Enter a strike range step size", value=10.0
)

def round_strike(strike: float) -> float:
    """Floors the strike to the nearest multiple of steps"""
    return strike_range_step * np.floor(strike / strike_range_step)

strike_range_start = st.number_input(
    "Enter a starting strike", value=round_strike(last_price * 0.8), step=strike_range_step
)
strike_range_end = st.number_input(
    "Enter an ending strike", value=round_strike(last_price * 1.2), step=strike_range_step
)
dollars_to_invest = st.number_input(
    "Enter the amount of dollars to invest", value=1000.0, step=100.0
)

strikes = np.arange(
    strike_range_start, strike_range_end + strike_range_step, strike_range_step
)

# Calculate all option prices in the strike grid
option_prices = {
    "Strike": [],
    "Call Price": [],
    "Call Delta": [],
    "Put Price": [],
    "Put Delta": [],
    "Vega": []
}

vola = float(historical_vola) / 100.0
r = float(risk_free_rate) / 100.0
years_to_expiry = float(days_to_expiry) / 365.0

for strike in strikes:
    option_prices["Strike"].append(int(strike))

    # First for the call
    price, delta, _ = black_scholes_option_price(
        years_to_expiry=years_to_expiry,
        strike=strike,
        spot=last_price,
        volatility=vola,
        interest_rate=r,
        is_call=True,
    )

    option_prices["Call Price"].append(price * ratio / eur_usd)
    option_prices["Call Delta"].append(delta)

    # Then for the put
    price, delta, vega = black_scholes_option_price(
        years_to_expiry=years_to_expiry,
        strike=strike,
        spot=last_price,
        volatility=vola,
        interest_rate=r,
        is_call=False,
    )

    option_prices["Put Price"].append(price * ratio / eur_usd)
    option_prices["Put Delta"].append(delta)
    option_prices["Vega"].append(vega * ratio)


option_prices = pd.DataFrame(option_prices)
option_prices["Distance to Strike (%)"] = (option_prices["Strike"] / last_price - 1.0) * 100.0

for idx, row in option_prices.iterrows():
    puts_per_call = -row['Call Delta'] / row['Put Delta']

    max_options = floor(
        dollars_to_invest / (row['Call Price'] + row['Put Price'] * puts_per_call)
    )

    call_break_even = row['Strike'] + row['Call Price'] / ratio
    put_break_even = row['Strike'] - row['Put Price'] / ratio

    option_prices.loc[idx, "Call Break Even"] = call_break_even
    option_prices.loc[idx, "Put Break Even"] = put_break_even
    option_prices.loc[idx, "Puts per Call"] = puts_per_call

    # option_prices.loc[idx, "Max Options"] = max_options

option_prices["Vega per Straddle"] = 2 * option_prices["Vega"] / (
    option_prices["Call Price"] + option_prices["Put Price"] * option_prices["Puts per Call"]
)

# Highlight the highest vega per straddle value
# Use a red-green gradient for the vega per straddle
# df = option_prices.style.background_gradient(
#     subset=["Vega per Straddle",
#             "Distance to Strike (%)"
#             ], cmap="RdBu"
# )
option_prices = option_prices.set_index("Strike")
df = option_prices.style.highlight_max(subset=["Vega per Straddle"], color="lightgreen")
st.table(df)

# Plot the option prices
fig, ax = plt.subplots(figsize=(10, 7))
ax.plot(option_prices.index, option_prices["Call Price"], label="Call")
ax.plot(option_prices.index, option_prices["Put Price"], label="Put")
ax.plot(option_prices.index, option_prices["Vega per Straddle"], label="Vega per Straddle")

ax.set_xlabel("Strike")
ax.set_ylabel("Option Price")
ax.legend()

# Add a vertical line for the current price
ax.axvline(last_price, color="black", linestyle="--")
st.pyplot(fig)
