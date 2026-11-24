import gzip
from datetime import datetime
from io import BytesIO

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# =========================================================
# PAGE SETTINGS
# =========================================================
st.set_page_config(
    page_title="Eurostat Asylum Insights",
    page_icon="🌍",
    layout="wide",
)


# =========================================================
# DESIGN
# =========================================================
EU_BLUE = "#003399"
UNHCR_BLUE = "#0072BC"
NAVY = "#003B5C"
GRID = "#DCE5F2"
COLORS = [
    EU_BLUE,
    UNHCR_BLUE,
    "#4E79A7",
    "#59C3E6",
    "#6F4EBA",
    "#2A9D8F",
    "#F4A261",
    "#E76F51",
]

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
    div[data-testid="stMetric"] {background:white;border:1px solid #D4E1F1;
        padding:17px 19px;border-radius:15px;box-shadow:0 5px 16px rgba(0,59,92,.07);}
    div[data-testid="stMetricLabel"] {color:#516979;font-weight:600;}
    div[data-testid="stMetricValue"] {color:#003399;font-weight:800;}
    div[data-testid="stPlotlyChart"] {background:white;border:1px solid #D4E1F1;
        border-radius:15px;padding:8px;overflow:hidden;box-shadow:0 5px 16px rgba(0,59,92,.06);}
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


# =========================================================
# EUROSTAT CONFIGURATION
# Based on the thesis ETL configuration (00_config.json)
# =========================================================
CFG = {
    "dataset": "migr_asyappctzm",
    "freq": "M",
    "unit": "PER",
    "sex": ["M", "F", "UNK"],
    "applicant": ["FRST"],
    "age": ["Y_LT14", "Y14-17", "Y18-34", "Y35-64", "Y_GE65", "UNK"],
    "chunk_size": 40,
    "start_year": 2015,
    "lag_months": 2,
}

API_BASE_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/"
    f"ESTAT/{CFG['dataset']}/1.0/*.*.*.*.*.*.*"
)


# Country of asylum codes used in the dashboard.
COUNTRIES = {
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


# Nationality codes available in the dashboard.
NATIONALITIES = {
    "Afghanistan": "AF",
    "Albania": "AL",
    "Algeria": "DZ",
    "Bangladesh": "BD",
    "Belarus": "BY",
    "Cameroon": "CM",
    "China": "CN",
    "Colombia": "CO",
    "DR Congo": "CD",
    "Côte d’Ivoire": "CI",
    "Egypt": "EG",
    "Eritrea": "ER",
    "Ethiopia": "ET",
    "Georgia": "GE",
    "Guinea": "GN",
    "India": "IN",
    "Iran": "IR",
    "Iraq": "IQ",
    "Lebanon": "LB",
    "Mali": "ML",
    "Morocco": "MA",
    "Nigeria": "NG",
    "North Macedonia": "MK",
    "Pakistan": "PK",
    "Palestine": "PS",
    "Russia": "RU",
    "Senegal": "SN",
    "Serbia": "RS",
    "Somalia": "SO",
    "Sudan": "SD",
    "Syria": "SY",
    "Tunisia": "TN",
    "Türkiye": "TR",
    "Ukraine": "UA",
    "Venezuela": "VE",
}


# Coordinates are used only to position markers on the dashboard map.
CAPITALS = {
    "AT": (48.2082, 16.3738, "Vienna"),
    "BE": (50.8503, 4.3517, "Brussels"),
    "BG": (42.6977, 23.3219, "Sofia"),
    "HR": (45.8150, 15.9819, "Zagreb"),
    "CY": (35.1856, 33.3823, "Nicosia"),
    "CZ": (50.0755, 14.4378, "Prague"),
    "DK": (55.6761, 12.5683, "Copenhagen"),
    "EE": (59.4370, 24.7536, "Tallinn"),
    "FI": (60.1699, 24.9384, "Helsinki"),
    "FR": (48.8566, 2.3522, "Paris"),
    "DE": (52.5200, 13.4050, "Berlin"),
    "EL": (37.9838, 23.7275, "Athens"),
    "HU": (47.4979, 19.0402, "Budapest"),
    "IS": (64.1466, -21.9426, "Reykjavik"),
    "IE": (53.3498, -6.2603, "Dublin"),
    "IT": (41.9028, 12.4964, "Rome"),
    "LV": (56.9496, 24.1052, "Riga"),
    "LI": (47.1410, 9.5209, "Vaduz"),
    "LT": (54.6872, 25.2797, "Vilnius"),
    "LU": (49.6116, 6.1319, "Luxembourg"),
    "MT": (35.8989, 14.5146, "Valletta"),
    "NL": (52.3676, 4.9041, "Amsterdam"),
    "NO": (59.9139, 10.7522, "Oslo"),
    "PL": (52.2297, 21.0122, "Warsaw"),
    "PT": (38.7223, -9.1393, "Lisbon"),
    "RO": (44.4268, 26.1025, "Bucharest"),
    "SK": (48.1486, 17.1077, "Bratislava"),
    "SI": (46.0569, 14.5058, "Ljubljana"),
    "ES": (40.4168, -3.7038, "Madrid"),
    "SE": (59.3293, 18.0686, "Stockholm"),
    "CH": (46.9480, 7.4474, "Bern"),
    "UK": (51.5074, -0.1278, "London"),
    "ME": (42.4304, 19.2594, "Podgorica"),
}


# =========================================================
# EUROSTAT API / EXTRACTION
# =========================================================
def build_url(citizens, geos, time_periods):
    """Build the same SDMX 3.0 query structure used in the thesis ETL."""
    params = {
        "c[freq]": CFG["freq"],
        "c[unit]": CFG["unit"],
        "c[citizen]": ",".join(citizens),
        "c[sex]": ",".join(CFG["sex"]),
        "c[applicant]": ",".join(CFG["applicant"]),
        "c[age]": ",".join(CFG["age"]),
        "c[geo]": ",".join(geos),
        "c[TIME_PERIOD]": ",".join(time_periods),
        "compress": "true",
        "format": "tsv",
    }
    return API_BASE_URL, params


def read_eurostat_response(response):
    """Read Eurostat TSV data and explain clearly when the API returns another format."""
    content = response.content

    if not content:
        raise RuntimeError("Eurostat returned an empty response.")

    # Requests normally decompresses gzip automatically. This also handles
    # responses that are still gzip-compressed.
    if content[:2] == b"\x1f\x8b":
        try:
            content = gzip.decompress(content)
        except OSError as error:
            raise RuntimeError(
                f"Eurostat returned invalid gzip data: {error}"
            ) from error

    text = content.decode("utf-8-sig", errors="replace").strip()

    if not text:
        raise RuntimeError("Eurostat returned an empty text response.")

    # HTTP 200 does not always mean that the response contains TSV data.
    first_line = text.splitlines()[0].lstrip().lower()
    if first_line.startswith(("<?xml", "<html", "<!doctype html")):
        raise RuntimeError(
            "Eurostat returned an HTML/XML page instead of TSV data. "
            f"Response preview: {text[:500]}"
        )
    if first_line.startswith(("{", "[")):
        raise RuntimeError(
            "Eurostat returned JSON instead of TSV data. "
            f"Response preview: {text[:500]}"
        )

    try:
        # The Python parser is more tolerant of irregular TSV formatting than
        # pandas' default C parser, while still raising errors for bad rows.
        raw = pd.read_csv(
            BytesIO(content),
            sep="\t",
            dtype=str,
            engine="python",
        )
    except pd.errors.ParserError as error:
        lines = text.splitlines()[:6]
        preview = "\n".join(
            f"Line {index + 1} (tabs: {line.count(chr(9))}): {line[:250]}"
            for index, line in enumerate(lines)
        )
        raise RuntimeError(
            "Pandas could not parse the Eurostat response as a TSV file. "
            f"Parser error: {error}\nResponse preview:\n{preview}"
        ) from error
    except Exception as error:
        raise RuntimeError(
            "Could not read the Eurostat response as TSV data. "
            f"Error: {error}. Response preview: {text[:500]}"
        ) from error

    if raw.empty or len(raw.columns) < 2:
        raise RuntimeError(
            "Eurostat returned a TSV response without usable observation columns. "
            f"Response preview: {text[:500]}"
        )

    return raw


def parse_observation(cell):
    """Separate the numeric observation from Eurostat flags (e, p, b, etc.)."""
    if pd.isna(cell):
        return None, ""

    value_text = str(cell).strip()
    if not value_text or value_text.startswith(":"):
        return None, value_text[1:].strip() if value_text.startswith(":") else ""

    pieces = value_text.split()
    try:
        value = float(pieces[0].replace(",", ""))
    except (ValueError, IndexError):
        return None, ""

    status = " ".join(pieces[1:])
    return value, status


def transform_response(raw_data):
    """Split the SDMX key and unpivot monthly observations, following the thesis ETL."""
    if raw_data.empty:
        return pd.DataFrame()

    data = raw_data.copy()
    data.columns = [str(column).strip() for column in data.columns]
    data = data.rename(columns={data.columns[0]: "code"})

    # The first column contains the seven SDMX dimensions in this order:
    # freq, unit, citizen, sex, applicant, age, geo.
    split_cols = data["code"].astype(str).str.split(r"[,\.]", n=6, expand=True)

    if split_cols.shape[1] != 7:
        sample = data["code"].iloc[0] if not data.empty else "no data"
        raise RuntimeError(
            "Unexpected Eurostat SDMX key format. Expected 7 dimensions, "
            f"but received {split_cols.shape[1]}. Sample key: {sample}"
        )

    split_cols.columns = ["freq", "unit", "citizen", "sex", "applicant", "age", "geo"]
    data = pd.concat(
        [data.reset_index(drop=True), split_cols.reset_index(drop=True)],
        axis=1,
    )

    dimension_columns = {
        "code", "freq", "unit", "citizen", "sex", "applicant", "age", "geo"
    }
    month_columns = [column for column in data.columns if column not in dimension_columns]

    if not month_columns:
        raise RuntimeError(
            "Eurostat returned the SDMX dimensions but no monthly observation columns."
        )

    tidy = data.melt(
        id_vars=["citizen", "sex", "age", "geo"],
        value_vars=month_columns,
        var_name="Period",
        value_name="Observation",
    )

    parsed = tidy["Observation"].apply(parse_observation)
    tidy["First-time applications"] = parsed.map(lambda item: item[0])
    tidy["Status"] = parsed.map(lambda item: item[1])

    # Keep only numeric observations. Missing/suppressed values are not counted.
    tidy = tidy.dropna(subset=["First-time applications"]).copy()
    tidy["Period"] = tidy["Period"].astype(str).str.strip()
    tidy["Date"] = pd.to_datetime(tidy["Period"], format="%Y-%m", errors="coerce")
    tidy = tidy.dropna(subset=["Date"])

    return tidy


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_eurostat(citizen_codes, geo_codes, time_periods):
    """Fetch selected nationalities in chunks, using the thesis ETL API pattern."""
    frames = []
    chunk_size = int(CFG["chunk_size"])
    chunks = [
        citizen_codes[index:index + chunk_size]
        for index in range(0, len(citizen_codes), chunk_size)
    ]

    if not chunks:
        return pd.DataFrame()

    for chunk_number, citizen_chunk in enumerate(chunks, start=1):
        url, params = build_url(citizen_chunk, geo_codes, time_periods)

        try:
            response = requests.get(
                url,
                params=params,
                headers={"Accept": "text/tab-separated-values", "User-Agent": "Mozilla/5.0 Eurostat-Asylum-Dashboard"},
                timeout=(20, 180),
            )
            response.raise_for_status()
            raw_data = read_eurostat_response(response)
            transformed = transform_response(raw_data)

        except requests.exceptions.HTTPError as error:
            response_text = ""
            if error.response is not None:
                response_text = error.response.text[:800]
            raise RuntimeError(
                f"Eurostat returned an HTTP error for request chunk "
                f"{chunk_number}/{len(chunks)}: {error}. {response_text}"
            ) from error
        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                f"Could not connect to the Eurostat API for request chunk "
                f"{chunk_number}/{len(chunks)}: {error}"
            ) from error
        except Exception as error:
            raise RuntimeError(
                f"Eurostat extraction failed for request chunk "
                f"{chunk_number}/{len(chunks)}: {error}"
            ) from error

        if not transformed.empty:
            frames.append(transformed)

    if not frames:
        return pd.DataFrame()

    detail = pd.concat(frames, ignore_index=True)

    country_by_code = {code: name for name, code in COUNTRIES.items()}
    nationality_by_code = {code: name for name, code in NATIONALITIES.items()}

    detail["Country code"] = detail["geo"]
    detail["Country of asylum"] = detail["geo"].map(country_by_code).fillna(detail["geo"])
    detail["Nationality"] = detail["citizen"].map(nationality_by_code).fillna(detail["citizen"])
    detail["Year"] = detail["Date"].dt.year
    detail["Month"] = detail["Date"].dt.strftime("%b")

    return detail


# =========================================================
# CHART FORMATTING
# =========================================================
def style_chart(fig, title, height=420, legend=False):
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
        margin=dict(l=18, r=18, t=108 if legend else 80, b=25),
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
# USER INTERFACE
# =========================================================
st.markdown(
    '<div class="hero"><h1>🌍 Eurostat Asylum Insights</h1>'
    "<p>First-time asylum applications by month, year, country of asylum and nationality</p></div>",
    unsafe_allow_html=True,
)

now = pd.Timestamp.now()
current_year = now.year

# The thesis configuration uses a two-month lag for the dynamic extraction.
latest_available_period = now.to_period("M") - CFG["lag_months"]
latest_available_year = latest_available_period.year

DEFAULT_COUNTRIES = ["Greece", "Germany", "France", "Italy", "Spain"]
DEFAULT_NATIONALITIES = ["Syria", "Afghanistan", "Türkiye", "Venezuela", "Colombia"]
DEFAULT_YEAR_RANGE = (max(CFG["start_year"], current_year - 4), current_year)


def clear_filters():
    st.session_state["countries"] = DEFAULT_COUNTRIES
    st.session_state["nationalities"] = DEFAULT_NATIONALITIES
    st.session_state["years"] = DEFAULT_YEAR_RANGE


with st.sidebar:
    st.header("Dashboard filters")
    st.button(
        "↻ Clear all filters",
        use_container_width=True,
        on_click=clear_filters,
    )

    selected_countries = st.multiselect(
        "Country of asylum",
        list(COUNTRIES.keys()),
        default=DEFAULT_COUNTRIES,
        key="countries",
    )
    selected_nationalities = st.multiselect(
        "Nationality",
        list(NATIONALITIES.keys()),
        default=DEFAULT_NATIONALITIES,
        key="nationalities",
    )
    selected_years = st.slider(
        "Year range",
        min_value=CFG["start_year"],
        max_value=current_year,
        value=DEFAULT_YEAR_RANGE,
        key="years",
    )

    st.divider()
    st.caption(
        "Source: Eurostat SDMX 3.0 API · migr_asyappctzm · applicant FRST"
    )
    st.caption(
        f"Latest requested month: {latest_available_period} "
        f"(current month minus {CFG['lag_months']} months)"
    )


if not selected_countries or not selected_nationalities:
    st.warning("Select at least one country of asylum and one nationality.")
    st.stop()

if len(selected_countries) > 10 or len(selected_nationalities) > 20:
    st.warning(
        "For performance, select at most 10 asylum countries and 20 nationalities."
    )
    st.stop()


# Convert the selected year range into an explicit monthly period list.
start_year, end_year = selected_years
start_period = pd.Period(f"{start_year}-01", freq="M")
selected_end_period = pd.Period(f"{end_year}-12", freq="M")
end_period = min(selected_end_period, latest_available_period)

if end_period < start_period:
    st.warning("The selected year range is after the latest available Eurostat period.")
    st.stop()

months = pd.period_range(start_period, end_period, freq="M").strftime("%Y-%m").tolist()


# =========================================================
# FETCH DATA
# =========================================================
with st.spinner("Retrieving first-time asylum data from Eurostat..."):
    try:
        detail = fetch_eurostat(
            tuple(NATIONALITIES[name] for name in selected_nationalities),
            tuple(COUNTRIES[name] for name in selected_countries),
            tuple(months),
        )
    except RuntimeError as error:
        st.error(str(error))
        st.info(
            "If the problem continues, check the Streamlit Cloud logs and "
            "confirm that the app's requirements.txt includes requests and plotly."
        )
        st.stop()


if detail.empty:
    st.warning("Eurostat returned no numeric observations for this selection and period.")
    st.stop()


# =========================================================
# AGGREGATION
# Sum the mutually exclusive sex and age categories to obtain totals.
# =========================================================
def combine_status(values):
    statuses = sorted({value for value in values if value})
    return ", ".join(statuses)


df = (
    detail.groupby(
        [
            "Date",
            "Year",
            "Month",
            "Country code",
            "Country of asylum",
            "Nationality",
        ],
        as_index=False,
    )
    .agg(
        **{"First-time applications": ("First-time applications", "sum")},
        Status=("Status", combine_status),
    )
)

if df.empty:
    st.warning("There are no observations to display for the selected filters.")
    st.stop()


# =========================================================
# KPI CALCULATIONS
# =========================================================
latest_date = df["Date"].max()
latest_total = df.loc[
    df["Date"] == latest_date, "First-time applications"
].sum()

previous_date = latest_date - pd.DateOffset(months=1)
previous_total = df.loc[
    df["Date"] == previous_date, "First-time applications"
].sum()

change = None
if previous_total != 0:
    change = (latest_total - previous_total) / previous_total

period_total = df["First-time applications"].sum()
latest_year_total = df.loc[
    df["Year"] == latest_date.year, "First-time applications"
].sum()

top_country = (
    df.groupby("Country of asylum")["First-time applications"].sum().idxmax()
)
top_nationality = (
    df.groupby("Nationality")["First-time applications"].sum().idxmax()
)


# =========================================================
# OVERVIEW / KPI CARDS
# =========================================================
st.markdown('<div class="section-title">Overview</div>', unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Selected-period total", f"{period_total:,.0f}")
k2.metric(
    f"Latest month · {latest_date:%b %Y}",
    f"{latest_total:,.0f}",
    f"{change:+.1%}" if change is not None else None,
)
k3.metric(f"{latest_date.year} total", f"{latest_year_total:,.0f}")
k4.metric("Top asylum country", top_country)
k5.metric("Top nationality", top_nationality)

st.markdown(
    '<div class="note">The latest year may be incomplete. Eurostat observation '
    "flags are retained in the downloadable observations where available. "
    "The dashboard sums the selected sex and age categories to calculate totals.</div>",
    unsafe_allow_html=True,
)


# =========================================================
# APPLICATIONS OVER TIME
# =========================================================
st.markdown(
    '<div class="section-title">Applications over time</div>',
    unsafe_allow_html=True,
)

monthly = (
    df.groupby(["Date", "Country of asylum"], as_index=False)[
        "First-time applications"
    ].sum()
)

fig_monthly = px.line(
    monthly,
    x="Date",
    y="First-time applications",
    color="Country of asylum",
    markers=True,
    color_discrete_sequence=COLORS,
)
style_chart(fig_monthly, "Monthly first-time asylum applications", 475, True)
fig_monthly.update_traces(
    line=dict(width=2.7),
    marker=dict(size=5),
    hovertemplate=(
        "<b>%{fullData.name}</b><br>%{x|%b %Y}<br>"
        "%{y:,.0f}<extra></extra>"
    ),
)
fig_monthly.update_xaxes(title="Month", gridcolor=GRID)
fig_monthly.update_yaxes(
    title="First-time applications",
    tickformat=",.0f",
    gridcolor=GRID,
)
st.plotly_chart(fig_monthly, use_container_width=True)


yearly = (
    df.groupby(["Year", "Country of asylum"], as_index=False)[
        "First-time applications"
    ].sum()
)

fig_yearly = px.bar(
    yearly,
    x="Year",
    y="First-time applications",
    color="Country of asylum",
    barmode="group",
    color_discrete_sequence=COLORS,
)
style_chart(fig_yearly, "Annual first-time asylum applications", 450, True)
fig_yearly.update_xaxes(title="Year", dtick=1, gridcolor=GRID)
fig_yearly.update_yaxes(
    title="First-time applications",
    tickformat=",.0f",
    gridcolor=GRID,
)
st.plotly_chart(fig_yearly, use_container_width=True)


# =========================================================
# COUNTRY AND NATIONALITY ANALYSIS
# =========================================================
st.markdown(
    '<div class="section-title">Country and nationality analysis</div>',
    unsafe_allow_html=True,
)

left, right = st.columns(2)

country_totals = (
    df.groupby("Country of asylum", as_index=False)["First-time applications"]
    .sum()
    .sort_values("First-time applications")
)

with left:
    fig_country = px.bar(
        country_totals,
        x="First-time applications",
        y="Country of asylum",
        orientation="h",
        color="First-time applications",
        color_continuous_scale=["#D7E7FF", EU_BLUE],
        text_auto=".3s",
    )
    style_chart(fig_country, "Applications by country of asylum", 470)
    fig_country.update_layout(coloraxis_showscale=False)
    fig_country.update_xaxes(
        title="First-time applications",
        tickformat=",.0f",
        gridcolor=GRID,
    )
    fig_country.update_yaxes(title="")
    st.plotly_chart(fig_country, use_container_width=True)


nationality_totals = (
    df.groupby("Nationality", as_index=False)["First-time applications"]
    .sum()
    .sort_values("First-time applications")
)

with right:
    fig_nat = px.bar(
        nationality_totals,
        x="First-time applications",
        y="Nationality",
        orientation="h",
        color="First-time applications",
        color_continuous_scale=["#D7F3FA", UNHCR_BLUE],
        text_auto=".3s",
    )
    style_chart(fig_nat, "Applications by nationality", 470)
    fig_nat.update_layout(coloraxis_showscale=False)
    fig_nat.update_xaxes(
        title="First-time applications",
        tickformat=",.0f",
        gridcolor=GRID,
    )
    fig_nat.update_yaxes(title="")
    st.plotly_chart(fig_nat, use_container_width=True)


matrix = df.pivot_table(
    index="Nationality",
    columns="Country of asylum",
    values="First-time applications",
    aggfunc="sum",
    fill_value=0,
)

fig_heat = px.imshow(
    matrix,
    aspect="auto",
    color_continuous_scale=["#F4F7FF", "#7DA7E8", EU_BLUE],
    text_auto=".3s",
    labels=dict(color="Applications"),
)
style_chart(
    fig_heat,
    "Country of asylum × nationality",
    max(420, 42 * len(matrix) + 120),
)
fig_heat.update_xaxes(title="Country of asylum")
fig_heat.update_yaxes(title="Nationality")
st.plotly_chart(fig_heat, use_container_width=True)


# =========================================================
# GEOGRAPHIC VIEW
# =========================================================
st.markdown(
    '<div class="section-title">Geographic view</div>',
    unsafe_allow_html=True,
)

map_data = country_totals.copy()
country_code_by_name = {name: code for name, code in COUNTRIES.items()}
map_data["Code"] = map_data["Country of asylum"].map(country_code_by_name)
map_data["Latitude"] = map_data["Code"].map(
    lambda code: CAPITALS.get(code, (None, None, None))[0]
)
map_data["Longitude"] = map_data["Code"].map(
    lambda code: CAPITALS.get(code, (None, None, None))[1]
)
map_data["Capital"] = map_data["Code"].map(
    lambda code: CAPITALS.get(code, (None, None, None))[2]
)
map_data = map_data.dropna(subset=["Latitude", "Longitude"])

if not map_data.empty:
    max_value = map_data["First-time applications"].max()
    if max_value > 0:
        map_data["Marker_Size"] = 12 + 28 * (
            map_data["First-time applications"] / max_value
        ).pow(0.5)
    else:
        map_data["Marker_Size"] = 16

    fig_map = px.scatter_map(
        map_data,
        lat="Latitude",
        lon="Longitude",
        size="Marker_Size",
        size_max=34,
        color="First-time applications",
        hover_name="Country of asylum",
        hover_data={
            "Capital": True,
            "First-time applications": ":,.0f",
            "Marker_Size": False,
            "Latitude": False,
            "Longitude": False,
        },
        color_continuous_scale=["#80D4EE", UNHCR_BLUE, EU_BLUE],
        map_style="open-street-map",
        zoom=2.3,
        center={"lat": 50, "lon": 12},
    )
    fig_map.update_traces(marker=dict(opacity=0.86))
    fig_map.update_layout(
        title=dict(
            text="First-time applications by country of asylum",
            x=0.02,
            y=0.97,
            xanchor="left",
            yanchor="top",
            font=dict(size=18, color=NAVY),
        ),
        height=560,
        margin=dict(l=8, r=8, t=65, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(title="Applications", thickness=12, len=0.65),
    )
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("No mapped asylum-country coordinates are available for this selection.")


# =========================================================
# DATA TABLE AND CSV DOWNLOAD
# =========================================================
with st.expander("View and download the Eurostat observations"):
    table = df[
        [
            "Date",
            "Year",
            "Month",
            "Country of asylum",
            "Nationality",
            "First-time applications",
            "Status",
        ]
    ].sort_values(
        ["Date", "Country of asylum", "Nationality"],
        ascending=[False, True, True],
    ).copy()

    table["Date"] = table["Date"].dt.strftime("%Y-%m")
    st.dataframe(table, use_container_width=True, hide_index=True)

    csv_data = table.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download selected Eurostat data as CSV",
        data=csv_data,
        file_name="eurostat_first_time_asylum_applications.csv",
        mime="text/csv",
    )


st.caption(
    f"Showing {len(df):,} monthly country-nationality observations. "
    f"Source: Eurostat SDMX 3.0 API · {CFG['dataset']}."
)
