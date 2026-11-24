import math
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# =========================================================
# PAGE AND DESIGN
# =========================================================
st.set_page_config(
    page_title="European Asylum Applications",
    page_icon="🌍",
    layout="wide",
)

EU_BLUE = "#003399"
UNHCR_BLUE = "#0072BC"
NAVY = "#003B5C"
GRID = "#DCE5F2"
COLORS = [EU_BLUE, UNHCR_BLUE, "#4E79A7", "#59C3E6", "#6F4EBA", "#2A9D8F", "#F4A261", "#E76F51"]

st.markdown(
    """
    <style>
    .stApp {background:linear-gradient(180deg,#F8FAFF 0%,#EDF3FA 100%);}
    .block-container {padding-top:1.3rem;padding-bottom:2rem;max-width:1480px;}
    h1,h2,h3 {color:#003B5C;}
    .hero {padding:24px 28px;border-radius:18px;color:white;margin-bottom:18px;
           background:linear-gradient(110deg,#003B5C,#003399 55%,#0072BC);
           box-shadow:0 10px 30px rgba(0,51,153,.18);}
    .hero h1 {color:white;margin:0;font-size:2rem;}
    .hero p {color:#EAF0FF;margin:8px 0 0;}
    .section-title {font-size:1.15rem;font-weight:750;color:#003B5C;margin:16px 0 8px;}
    div[data-testid="stMetric"] {background:white;border:1px solid #D4E1F1;padding:17px 19px;
                                  border-radius:15px;box-shadow:0 5px 16px rgba(0,59,92,.07);}
    div[data-testid="stMetricLabel"] {color:#516979;font-weight:600;}
    div[data-testid="stMetricValue"] {color:#003399;font-weight:800;}
    div[data-testid="stPlotlyChart"] {background:white;border:1px solid #D4E1F1;
                                       border-radius:15px;padding:8px;overflow:hidden;
                                       box-shadow:0 5px 16px rgba(0,59,92,.06);}
    section[data-testid="stSidebar"] {background:#003B5C;}
    section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p {color:white !important;}
    section[data-testid="stSidebar"] button {border-radius:10px;}
    section[data-testid="stSidebar"] button p {color:#111 !important;}
    .note {background:#FFF;border-left:5px solid #FFCC00;padding:11px 14px;
           border-radius:0 10px 10px 0;color:#365B6D;margin:8px 0 14px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero"><h1>🌍 European Asylum Applications</h1>'
    '<p>Monthly first-time asylum applications by country of asylum</p></div>',
    unsafe_allow_html=True,
)


# =========================================================
# EUROSTAT SETTINGS
# =========================================================
DATASET_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/"
    "dataflow/ESTAT/migr_asyappctzm/1.0"
)

# Eurostat uses EL for Greece. These are the European reporting countries
# used by this dashboard; aggregate regions such as EU27 are not included.
EUROPEAN_COUNTRIES = {
    "Austria": "AT",
    "Belgium": "BE",
    "Bulgaria": "BG",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czechia": "CZ",
    "Denmark": "DK",
    "Estonia": "EE",
    "Finland": "FI",
    "France": "FR",
    "Germany": "DE",
    "Greece": "EL",
    "Hungary": "HU",
    "Iceland": "IS",
    "Ireland": "IE",
    "Italy": "IT",
    "Latvia": "LV",
    "Liechtenstein": "LI",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Malta": "MT",
    "Netherlands": "NL",
    "Norway": "NO",
    "Poland": "PL",
    "Portugal": "PT",
    "Romania": "RO",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Spain": "ES",
    "Sweden": "SE",
    "Switzerland": "CH",
    "United Kingdom": "UK",
    "Montenegro": "ME",
}

# We request the total citizenship, total sex and total age categories.
# This avoids downloading and adding hundreds of nationality/sex/age series.


def normalise_dimension_name(name):
    return str(name).strip().lower()


def get_dimension_codes(dimension):
    """Return category codes in their correct JSON-stat order."""
    category = dimension.get("category", {})
    index = category.get("index")

    if isinstance(index, dict):
        return [code for code, position in sorted(index.items(), key=lambda item: item[1])]
    if isinstance(index, list):
        return index

    # JSON-stat may omit category.index when the category order is implicit.
    labels = category.get("label", {})
    if isinstance(labels, dict):
        return list(labels.keys())

    raise ValueError("Eurostat JSON response is missing dimension category indexes.")


def parse_jsonstat(payload):
    """Decode JSON-stat and return total monthly values for each asylum country."""
    if payload.get("class") != "dataset":
        message = payload.get("message") or payload.get("error") or payload
        raise ValueError(f"Eurostat did not return a JSON-stat dataset: {str(message)[:500]}")

    dimension_ids = payload.get("id", [])
    dimension_sizes = payload.get("size", [])
    dimensions = payload.get("dimension", {})
    values = payload.get("value")

    if not dimension_ids or not dimension_sizes or values is None:
        raise ValueError("The Eurostat JSON-stat response is missing dimensions or observations.")

    # Find the relevant dimensions without relying on their order in the response.
    id_by_lower = {normalise_dimension_name(name): name for name in dimension_ids}

    required = ["freq", "unit", "applicant", "geo"]
    missing = [name for name in required if name not in id_by_lower]
    if missing:
        raise ValueError(
            "The dataset structure is different from expected. "
            f"Missing dimensions: {', '.join(missing)}. "
            f"Received dimensions: {', '.join(dimension_ids)}"
        )

    geo_dim = id_by_lower["geo"]
    time_dim = id_by_lower.get("time_period") or id_by_lower.get("time")
    if time_dim is None:
        raise ValueError(f"Could not find the time dimension. Dimensions: {dimension_ids}")

    # Build a full array. JSON-stat normally provides a flat list; sparse
    # responses may use a dictionary with flat positions as keys.
    expected_size = math.prod(dimension_sizes)
    data_array = np.full(expected_size, np.nan, dtype=float)

    if isinstance(values, list):
        if len(values) != expected_size:
            raise ValueError(
                f"Unexpected JSON-stat value count: got {len(values)}, "
                f"expected {expected_size}."
            )
        for position, value in enumerate(values):
            if value is not None:
                try:
                    data_array[position] = float(value)
                except (TypeError, ValueError):
                    pass
    elif isinstance(values, dict):
        for position, value in values.items():
            if value is not None:
                try:
                    data_array[int(position)] = float(value)
                except (TypeError, ValueError, IndexError):
                    pass
    else:
        raise ValueError("Eurostat returned an unsupported JSON-stat observation format.")

    shaped = data_array.reshape(tuple(dimension_sizes))

    # Filter the dimensions that define the indicator.
    fixed_filters = {
        "freq": "M",
        "unit": "PER",
        "citizen": "_T",  # Total citizenship
        "sex": "T",       # Total sex
        "applicant": "FRST",
        "age": "TOTAL",   # Total age class
    }
    slices = []
    remaining_dimensions = []

    for dimension_id, dimension_size in zip(dimension_ids, dimension_sizes):
        dimension_key = normalise_dimension_name(dimension_id)
        if dimension_key in fixed_filters:
            dimension = dimensions.get(dimension_id, {})
            codes = get_dimension_codes(dimension)
            wanted_code = fixed_filters[dimension_key]
            if wanted_code not in codes:
                raise ValueError(
                    f"Eurostat does not provide '{wanted_code}' in dimension '{dimension_id}'. "
                    f"Available codes include: {codes[:15]}"
                )
            slices.append(codes.index(wanted_code))
        else:
            slices.append(slice(None))
            remaining_dimensions.append(dimension_key)

    selected = shaped[tuple(slices)]

    # The total citizenship, sex and age categories are already selected.
    # If Eurostat adds another non-country/time dimension, sum it here.
    sum_axes = tuple(
        axis
        for axis, dimension_key in enumerate(remaining_dimensions)
        if dimension_key not in {"geo", "time_period", "time"}
    )

    valid_counts = np.sum(~np.isnan(selected), axis=sum_axes) if sum_axes else (~np.isnan(selected)).astype(int)
    totals = np.nansum(selected, axis=sum_axes) if sum_axes else selected
    totals = np.where(valid_counts > 0, totals, np.nan)

    # The result should now contain only geo and time dimensions.
    output_dimensions = [
        name for name in remaining_dimensions
        if name in {"geo", "time_period", "time"}
    ]
    if len(output_dimensions) != 2:
        raise ValueError(
            "Could not reduce the Eurostat response to country and month. "
            f"Remaining dimensions: {remaining_dimensions}"
        )

    if output_dimensions[0] == "geo":
        totals = totals.T

    geo_info = dimensions[geo_dim]
    geo_codes = get_dimension_codes(geo_info)
    geo_labels = geo_info.get("category", {}).get("label", {})

    time_info = dimensions[time_dim]
    time_codes = get_dimension_codes(time_info)

    # Only keep the countries explicitly listed above; this excludes EU/EA
    # aggregates and any non-European reporting areas.
    allowed_codes = set(EUROPEAN_COUNTRIES.values())
    rows = []
    for geo_position, geo_code in enumerate(geo_codes):
        if geo_code not in allowed_codes:
            continue
        for time_position, period in enumerate(time_codes):
            value = totals[geo_position, time_position]
            if np.isnan(value):
                continue
            try:
                date = pd.Period(str(period), freq="M").to_timestamp()
            except (ValueError, TypeError):
                continue

            country_name = geo_labels.get(geo_code, geo_code) if isinstance(geo_labels, dict) else geo_code
            # Use our consistent display names rather than API label variants.
            country_name = next(
                (name for name, code in EUROPEAN_COUNTRIES.items() if code == geo_code),
                country_name,
            )
            rows.append(
                {
                    "Date": date,
                    "Year": date.year,
                    "Month": date.strftime("%b"),
                    "Country code": geo_code,
                    "Country": country_name,
                    "First-time applications": float(value),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError(
            "The JSON response was read, but no observations matched the selected "
            "European countries and monthly first-time applicant filters."
        )

    return result.sort_values(["Date", "Country"]).reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_eurostat(start_period, end_period):
    """Download monthly first-time asylum applications from the Eurostat JSON API."""
    params = {
        "compress": "false",
        "format": "json",
        "lang": "en",
        "c[freq]": "M",
        "c[unit]": "PER",
        "c[applicant]": "FRST",
        "c[citizen]": "_T",
        "c[sex]": "T",
        "c[age]": "TOTAL",
        "c[geo]": ",".join(EUROPEAN_COUNTRIES.values()),
        "c[TIME_PERIOD]": f"ge:{start_period}+le:{end_period}",
    }

    try:
        response = requests.get(
            DATASET_URL,
            params=params,
            headers={"Accept": "application/json"},
            timeout=(20, 180),
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        details = ""
        if error.response is not None:
            details = error.response.text[:700]
        raise RuntimeError(
            f"Eurostat returned HTTP {response.status_code}: {details}"
        ) from error
    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"Could not connect to Eurostat: {error}") from error

    try:
        payload = response.json()
    except ValueError as error:
        preview = response.text[:500]
        raise RuntimeError(
            "Eurostat did not return valid JSON. Response preview: " + preview
        ) from error

    try:
        return parse_jsonstat(payload)
    except Exception as error:
        raise RuntimeError(f"Could not process the Eurostat JSON response: {error}") from error


def style_chart(fig, title, height=430, legend=False):
    fig.update_layout(
        title=dict(
            text=title,
            x=0.02,
            y=0.96,
            xanchor="left",
            yanchor="top",
            font=dict(size=18, color=NAVY),
        ),
        height=height,
        margin=dict(l=18, r=18, t=105 if legend else 80, b=25),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#365B6D"),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    if legend:
        fig.update_layout(
            legend=dict(
                orientation="h",
                x=0.02,
                xanchor="left",
                y=1.02,
                yanchor="bottom",
                title_text="",
            )
        )


# =========================================================
# FILTERS
# =========================================================
now = pd.Timestamp.now()
current_year = now.year
first_year = 2008

with st.sidebar:
    st.header("Dashboard filters")
    year_range = st.slider(
        "Year range",
        min_value=first_year,
        max_value=current_year,
        value=(max(2015, current_year - 5), current_year),
    )
    st.divider()
    st.caption("Source: Eurostat · migr_asyappctzm · JSON-stat API")
    st.caption("Indicator: monthly · persons · first-time applicants · all citizens/sexes/ages")

start_year, end_year = year_range
start_period = f"{start_year}-01"
# The API is queried through the current month. Missing/latest incomplete
# months are handled as Eurostat observations, not manually estimated.
end_period = min(f"{end_year}-12", now.strftime("%Y-%m"))


# =========================================================
# LOAD DATA
# =========================================================
with st.spinner("Downloading monthly asylum application data from Eurostat..."):
    try:
        df = fetch_eurostat(start_period, end_period)
    except RuntimeError as error:
        st.error(str(error))
        st.info(
            "If this error persists, open Manage app → Logs in Streamlit Cloud "
            "and share the detailed message."
        )
        st.stop()

# Keep the selected period even if the API returns a few extra periods.
df = df[(df["Date"] >= pd.Timestamp(start_period)) & (df["Date"] <= pd.Timestamp(end_period + "-01"))]
if df.empty:
    st.warning("Eurostat returned no observations for the selected period.")
    st.stop()


# =========================================================
# OVERVIEW
# =========================================================
latest_date = df["Date"].max()
latest_total = df.loc[df["Date"] == latest_date, "First-time applications"].sum()
previous_date = latest_date - pd.DateOffset(months=1)
previous_total = df.loc[df["Date"] == previous_date, "First-time applications"].sum()
change = (latest_total - previous_total) / previous_total if previous_total else None
period_total = df["First-time applications"].sum()
country_count = df["Country"].nunique()
top_country = (
    df.groupby("Country")["First-time applications"].sum().idxmax()
)

st.markdown('<div class="section-title">Overview</div>', unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Selected-period total", f"{period_total:,.0f}")
k2.metric(
    f"Latest month · {latest_date:%b %Y}",
    f"{latest_total:,.0f}",
    f"{change:+.1%}" if change is not None else None,
)
k3.metric("Countries with data", f"{country_count}")
k4.metric("Top asylum country", top_country)

st.markdown(
    '<div class="note">Totals combine all nationalities, sexes and age groups. '
    'Only individual European countries are included; regional aggregates such as '
    'EU27 and the euro area are excluded.</div>',
    unsafe_allow_html=True,
)


# =========================================================
# MONTHLY TREND
# =========================================================
st.markdown('<div class="section-title">Monthly applications by country</div>', unsafe_allow_html=True)
monthly = df.groupby(["Date", "Country"], as_index=False)["First-time applications"].sum()
fig_monthly = px.line(
    monthly,
    x="Date",
    y="First-time applications",
    color="Country",
    markers=False,
    color_discrete_sequence=COLORS,
)
style_chart(fig_monthly, "Monthly first-time asylum applications", 500, True)
fig_monthly.update_traces(line=dict(width=2.3))
fig_monthly.update_xaxes(title="Month", gridcolor=GRID)
fig_monthly.update_yaxes(title="First-time applications", tickformat=",.0f", gridcolor=GRID)
st.plotly_chart(fig_monthly, use_container_width=True)


# =========================================================
# COUNTRY RANKING
# =========================================================
st.markdown('<div class="section-title">Applications by country</div>', unsafe_allow_html=True)
country_totals = (
    df.groupby("Country", as_index=False)["First-time applications"]
    .sum()
    .sort_values("First-time applications")
)
fig_country = px.bar(
    country_totals,
    x="First-time applications",
    y="Country",
    orientation="h",
    color="First-time applications",
    color_continuous_scale=["#D7E7FF", EU_BLUE],
    text_auto=".3s",
)
style_chart(fig_country, "Total first-time applications in selected period", max(430, 25 * len(country_totals) + 100))
fig_country.update_layout(coloraxis_showscale=False)
fig_country.update_xaxes(title="First-time applications", tickformat=",.0f", gridcolor=GRID)
fig_country.update_yaxes(title="")
st.plotly_chart(fig_country, use_container_width=True)


# =========================================================
# DATA TABLE AND DOWNLOAD
# =========================================================
with st.expander("View and download monthly observations"):
    table = df[["Date", "Year", "Month", "Country code", "Country", "First-time applications"]].copy()
    table = table.sort_values(["Date", "Country"], ascending=[False, True])
    table["Date"] = table["Date"].dt.strftime("%Y-%m")
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button(
        "Download data as CSV",
        data=table.to_csv(index=False).encode("utf-8-sig"),
        file_name="eurostat_monthly_first_time_asylum_applications.csv",
        mime="text/csv",
    )

st.caption(
    f"Showing {len(df):,} country-month observations. "
    "Source: Eurostat dataset migr_asyappctzm."
)
