import math
from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Eurostat Asylum Insights", page_icon="🟦", layout="wide")

# -----------------------------
# Visual theme
# -----------------------------
EU_BLUE = "#003399"
EU_LIGHT = "#EAF0FF"
UNHCR_BLUE = "#0072BC"
NAVY = "#003B5C"
GOLD = "#FFCC00"
GRID = "#DCE5F2"
COLORS = [EU_BLUE, UNHCR_BLUE, "#4E79A7", "#59C3E6", "#6F4EBA", "#2A9D8F", "#F4A261", "#E76F51"]

st.markdown(
    """
<style>
.stApp {background:linear-gradient(180deg,#F8FAFF 0%,#EDF3FA 100%);}
.block-container {padding-top:1.3rem;padding-bottom:2rem;max-width:1480px;}
h1,h2,h3 {color:#003B5C;}
.hero {padding:24px 28px;border-radius:18px;color:white;margin-bottom:18px;background:linear-gradient(110deg,#003B5C,#003399 55%,#0072BC);box-shadow:0 10px 30px rgba(0,51,153,.18);}
.hero h1 {color:white;margin:0;font-size:2rem;}
.hero p {color:#EAF0FF;margin:8px 0 0;}
.section-title {font-size:1.15rem;font-weight:750;color:#003B5C;margin:16px 0 8px;}
div[data-testid="stMetric"] {background:white;border:1px solid #D4E1F1;padding:17px 19px;border-radius:15px;box-shadow:0 5px 16px rgba(0,59,92,.07);}
div[data-testid="stMetricLabel"] {color:#516979;font-weight:600;}
div[data-testid="stMetricValue"] {color:#003399;font-weight:800;}
div[data-testid="stPlotlyChart"] {background:white;border:1px solid #D4E1F1;border-radius:15px;padding:8px;overflow:hidden;box-shadow:0 5px 16px rgba(0,59,92,.06);}
section[data-testid="stSidebar"] {background:#003B5C;}
section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,section[data-testid="stSidebar"] h3,section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] p {color:white !important;}
section[data-testid="stSidebar"] button {border-radius:10px;}
section[data-testid="stSidebar"] button p {color:#111 !important;}
.note {background:#FFF;border-left:5px solid #FFCC00;padding:11px 14px;border-radius:0 10px 10px 0;color:#365B6D;margin:8px 0 14px;}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Eurostat selections
# Codes follow Eurostat conventions. Greece is EL and the UK is UK.
# -----------------------------
ASYLUM_COUNTRIES = {
    "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR", "Cyprus": "CY",
    "Czechia": "CZ", "Denmark": "DK", "Estonia": "EE", "Finland": "FI", "France": "FR",
    "Germany": "DE", "Greece": "EL", "Hungary": "HU", "Iceland": "IS", "Ireland": "IE",
    "Italy": "IT", "Latvia": "LV", "Liechtenstein": "LI", "Lithuania": "LT", "Luxembourg": "LU",
    "Malta": "MT", "Netherlands": "NL", "Norway": "NO", "Poland": "PL", "Portugal": "PT",
    "Romania": "RO", "Slovakia": "SK", "Slovenia": "SI", "Spain": "ES", "Sweden": "SE",
    "Switzerland": "CH", "United Kingdom": "UK", "Montenegro": "ME",
}

# A practical set of nationalities frequently used in European asylum analysis.
# More can be added later by inserting the Eurostat citizenship code.
NATIONALITIES = {
    "Afghanistan": "AF", "Albania": "AL", "Algeria": "DZ", "Bangladesh": "BD", "Belarus": "BY",
    "Cameroon": "CM", "China": "CN", "Colombia": "CO", "Congo, Democratic Republic": "CD",
    "Côte d’Ivoire": "CI", "Egypt": "EG", "Eritrea": "ER", "Ethiopia": "ET", "Georgia": "GE",
    "Guinea": "GN", "India": "IN", "Iran": "IR", "Iraq": "IQ", "Lebanon": "LB", "Mali": "ML",
    "Morocco": "MA", "Nigeria": "NG", "North Macedonia": "MK", "Pakistan": "PK", "Palestine": "PS",
    "Russia": "RU", "Senegal": "SN", "Serbia": "RS", "Somalia": "SO", "Sudan": "SD",
    "Syria": "SY", "Tunisia": "TN", "Türkiye": "TR", "Ukraine": "UA", "Venezuela": "VE",
}

CAPITALS = {
    "AT": (48.2082,16.3738,"Vienna"), "BE": (50.8503,4.3517,"Brussels"), "BG": (42.6977,23.3219,"Sofia"),
    "HR": (45.8150,15.9819,"Zagreb"), "CY": (35.1856,33.3823,"Nicosia"), "CZ": (50.0755,14.4378,"Prague"),
    "DK": (55.6761,12.5683,"Copenhagen"), "EE": (59.4370,24.7536,"Tallinn"), "FI": (60.1699,24.9384,"Helsinki"),
    "FR": (48.8566,2.3522,"Paris"), "DE": (52.5200,13.4050,"Berlin"), "EL": (37.9838,23.7275,"Athens"),
    "HU": (47.4979,19.0402,"Budapest"), "IS": (64.1466,-21.9426,"Reykjavik"), "IE": (53.3498,-6.2603,"Dublin"),
    "IT": (41.9028,12.4964,"Rome"), "LV": (56.9496,24.1052,"Riga"), "LI": (47.1410,9.5209,"Vaduz"),
    "LT": (54.6872,25.2797,"Vilnius"), "LU": (49.6116,6.1319,"Luxembourg"), "MT": (35.8989,14.5146,"Valletta"),
    "NL": (52.3676,4.9041,"Amsterdam"), "NO": (59.9139,10.7522,"Oslo"), "PL": (52.2297,21.0122,"Warsaw"),
    "PT": (38.7223,-9.1393,"Lisbon"), "RO": (44.4268,26.1025,"Bucharest"), "SK": (48.1486,17.1077,"Bratislava"),
    "SI": (46.0569,14.5058,"Ljubljana"), "ES": (40.4168,-3.7038,"Madrid"), "SE": (59.3293,18.0686,"Stockholm"),
    "CH": (46.9480,7.4474,"Bern"), "UK": (51.5074,-0.1278,"London"), "ME": (42.4304,19.2594,"Podgorica"),
}

EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/migr_asyappctzm"


def decode_jsonstat(payload):
    """Convert Eurostat's JSON-stat response into a tidy DataFrame."""
    dim_ids = payload.get("id", [])
    sizes = payload.get("size", [])
    dimensions = payload.get("dimension", {})
    values = payload.get("value", {})
    statuses = payload.get("status", {})

    code_by_position = {}
    label_by_code = {}
    for dim in dim_ids:
        category = dimensions[dim]["category"]
        index = category.get("index", {})
        if isinstance(index, list):
            ordered_codes = index
        else:
            ordered_codes = [code for code, _ in sorted(index.items(), key=lambda pair: pair[1])]
        code_by_position[dim] = ordered_codes
        label_by_code[dim] = category.get("label", {})

    rows = []
    for flat_key, value in values.items():
        flat_index = int(flat_key)
        coordinates = [0] * len(sizes)
        remainder = flat_index
        for i in range(len(sizes) - 1, -1, -1):
            coordinates[i] = remainder % sizes[i]
            remainder //= sizes[i]

        row = {"value": value, "status": statuses.get(str(flat_key), "")}
        for dim, coordinate in zip(dim_ids, coordinates):
            code = code_by_position[dim][coordinate]
            row[dim] = code
            row[f"{dim}_label"] = label_by_code[dim].get(code, code)
        rows.append(row)

    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_eurostat(country_codes, nationality_codes, start_period, end_period):
    params = [
        ("lang", "en"), ("freq", "M"), ("unit", "PER"), ("sex", "T"),
        ("age", "TOTAL"), ("asyl_app", "NASY_APP"),
        ("sinceTimePeriod", start_period), ("untilTimePeriod", end_period),
    ]
    params.extend(("geo", code) for code in country_codes)
    params.extend(("citizen", code) for code in nationality_codes)

    try:
        response = requests.get(EUROSTAT_URL, params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.Timeout as exc:
        raise RuntimeError("Eurostat took too long to respond. Please try a shorter period or fewer selections.") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"The app could not retrieve Eurostat data: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("Eurostat returned an invalid response.") from exc

    data = decode_jsonstat(payload)
    if data.empty:
        return data, payload.get("updated", "")

    data = data.rename(columns={
        "geo_label": "Country of asylum", "citizen_label": "Nationality",
        "time": "Period", "value": "First-time applications", "status": "Status",
    })
    data["Date"] = pd.to_datetime(data["Period"], format="%Y-%m", errors="coerce")
    data["Year"] = data["Date"].dt.year
    data["Month"] = data["Date"].dt.strftime("%b")
    data["First-time applications"] = pd.to_numeric(data["First-time applications"], errors="coerce")
    data = data.dropna(subset=["Date", "First-time applications"])
    return data, payload.get("updated", "")


def style_chart(fig, title, height=420, legend=False):
    fig.update_layout(
        title=dict(text=title, x=.02, y=.96, xanchor="left", yanchor="top", font=dict(size=18, color=NAVY)),
        height=height, margin=dict(l=18, r=18, t=108 if legend else 80, b=25),
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#365B6D"),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    if legend:
        fig.update_layout(legend=dict(orientation="h", x=.02, xanchor="left", y=1.02, yanchor="bottom", title_text=""))
    return fig


# -----------------------------
# Header and controls
# -----------------------------
st.markdown("""<div class="hero"><h1>🟦 Eurostat Asylum Insights</h1><p>First-time asylum applications by month, year, country of asylum and nationality</p></div>""", unsafe_allow_html=True)

current_year = datetime.now().year
DEFAULT_COUNTRIES = ["Greece", "Germany", "France", "Italy", "Spain"]
DEFAULT_NATIONALITIES = ["Syria", "Afghanistan", "Türkiye", "Venezuela", "Colombia"]


def clear_filters():
    st.session_state["countries"] = DEFAULT_COUNTRIES
    st.session_state["nationalities"] = DEFAULT_NATIONALITIES
    st.session_state["years"] = (max(2015, current_year - 5), current_year)


with st.sidebar:
    st.header("Dashboard filters")
    st.button("↻ Clear all filters", use_container_width=True, on_click=clear_filters)
    selected_countries = st.multiselect("Country of asylum", list(ASYLUM_COUNTRIES), default=DEFAULT_COUNTRIES, key="countries")
    selected_nationalities = st.multiselect("Nationality", list(NATIONALITIES), default=DEFAULT_NATIONALITIES, key="nationalities")
    selected_years = st.slider("Year range", 2008, current_year, (max(2015, current_year - 5), current_year), key="years")
    st.divider()
    st.caption("The app requests monthly first-time applicant data directly from Eurostat dataset migr_asyappctzm.")

if not selected_countries or not selected_nationalities:
    st.warning("Select at least one country of asylum and one nationality.")
    st.stop()
if len(selected_countries) > 10 or len(selected_nationalities) > 15:
    st.warning("For speed and readability, select up to 10 asylum countries and 15 nationalities.")
    st.stop()

start_year, end_year = selected_years
start_period = f"{start_year}-01"
end_period = f"{end_year}-12"

with st.spinner("Retrieving asylum data from Eurostat..."):
    try:
        df, last_updated = fetch_eurostat(
            [ASYLUM_COUNTRIES[name] for name in selected_countries],
            [NATIONALITIES[name] for name in selected_nationalities],
            start_period,
            end_period,
        )
    except RuntimeError as error:
        st.error(str(error))
        st.stop()

if df.empty:
    st.warning("Eurostat returned no observations for this selection. Try a broader period or different countries/nationalities.")
    st.stop()

# -----------------------------
# KPIs
# -----------------------------
latest_date = df["Date"].max()
latest_month = df[df["Date"] == latest_date]
previous_date = latest_date - pd.DateOffset(months=1)
previous_month = df[df["Date"] == previous_date]
latest_total = latest_month["First-time applications"].sum()
previous_total = previous_month["First-time applications"].sum()
monthly_change = ((latest_total - previous_total) / previous_total) if previous_total else None
period_total = df["First-time applications"].sum()
latest_year_total = df[df["Year"] == latest_date.year]["First-time applications"].sum()
top_country = df.groupby("Country of asylum")["First-time applications"].sum().idxmax()
top_nationality = df.groupby("Nationality")["First-time applications"].sum().idxmax()

st.markdown('<div class="section-title">Overview</div>', unsafe_allow_html=True)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Selected-period total", f"{period_total:,.0f}")
k2.metric(f"Latest month · {latest_date:%b %Y}", f"{latest_total:,.0f}", f"{monthly_change:+.1%}" if monthly_change is not None else None)
k3.metric(f"{latest_date.year} total", f"{latest_year_total:,.0f}")
k4.metric("Top asylum country", top_country)
k5.metric("Top nationality", top_nationality)

st.markdown('<div class="note">The latest calendar year may be incomplete. Eurostat observations may also carry provisional, break-in-series or other status flags.</div>', unsafe_allow_html=True)

# -----------------------------
# Trends
# -----------------------------
st.markdown('<div class="section-title">Applications over time</div>', unsafe_allow_html=True)
monthly = df.groupby(["Date", "Country of asylum"], as_index=False)["First-time applications"].sum()
fig_monthly = px.line(monthly, x="Date", y="First-time applications", color="Country of asylum", markers=True, color_discrete_sequence=COLORS)
style_chart(fig_monthly, "Monthly first-time asylum applications", 475, True)
fig_monthly.update_traces(line=dict(width=2.7), marker=dict(size=5), hovertemplate="<b>%{fullData.name}</b><br>%{x|%b %Y}<br>%{y:,.0f}<extra></extra>")
fig_monthly.update_xaxes(title="Month", gridcolor=GRID)
fig_monthly.update_yaxes(title="First-time applications", tickformat=",.0f", gridcolor=GRID)
st.plotly_chart(fig_monthly, use_container_width=True)

yearly = df.groupby(["Year", "Country of asylum"], as_index=False)["First-time applications"].sum()
fig_yearly = px.bar(yearly, x="Year", y="First-time applications", color="Country of asylum", barmode="group", color_discrete_sequence=COLORS)
style_chart(fig_yearly, "Annual first-time asylum applications", 450, True)
fig_yearly.update_xaxes(title="Year", dtick=1, gridcolor=GRID)
fig_yearly.update_yaxes(title="First-time applications", tickformat=",.0f", gridcolor=GRID)
st.plotly_chart(fig_yearly, use_container_width=True)

# -----------------------------
# Country and nationality analysis
# -----------------------------
st.markdown('<div class="section-title">Country and nationality analysis</div>', unsafe_allow_html=True)
left, right = st.columns(2)

country_totals = df.groupby("Country of asylum", as_index=False)["First-time applications"].sum().sort_values("First-time applications")
with left:
    fig_country = px.bar(country_totals, x="First-time applications", y="Country of asylum", orientation="h", color="First-time applications", color_continuous_scale=["#D7E7FF", EU_BLUE], text_auto=".3s")
    style_chart(fig_country, "Applications by country of asylum", 470)
    fig_country.update_layout(coloraxis_showscale=False)
    fig_country.update_xaxes(title="First-time applications", tickformat=",.0f", gridcolor=GRID)
    fig_country.update_yaxes(title="")
    st.plotly_chart(fig_country, use_container_width=True)

nationality_totals = df.groupby("Nationality", as_index=False)["First-time applications"].sum().sort_values("First-time applications")
with right:
    fig_nationality = px.bar(nationality_totals, x="First-time applications", y="Nationality", orientation="h", color="First-time applications", color_continuous_scale=["#D7F3FA", UNHCR_BLUE], text_auto=".3s")
    style_chart(fig_nationality, "Applications by nationality", 470)
    fig_nationality.update_layout(coloraxis_showscale=False)
    fig_nationality.update_xaxes(title="First-time applications", tickformat=",.0f", gridcolor=GRID)
    fig_nationality.update_yaxes(title="")
    st.plotly_chart(fig_nationality, use_container_width=True)

# Country-nationality matrix
matrix = df.pivot_table(index="Nationality", columns="Country of asylum", values="First-time applications", aggfunc="sum", fill_value=0)
fig_heat = px.imshow(matrix, aspect="auto", color_continuous_scale=["#F4F7FF", "#7DA7E8", EU_BLUE], text_auto=".3s", labels=dict(color="Applications"))
style_chart(fig_heat, "Country of asylum × nationality", max(420, 42 * len(matrix) + 120))
fig_heat.update_xaxes(title="Country of asylum")
fig_heat.update_yaxes(title="Nationality")
st.plotly_chart(fig_heat, use_container_width=True)

# -----------------------------
# Real tile-based asylum-country map
# -----------------------------
st.markdown('<div class="section-title">Geographic view</div>', unsafe_allow_html=True)
map_data = country_totals.copy()
code_lookup = {name: code for name, code in ASYLUM_COUNTRIES.items()}
map_data["Code"] = map_data["Country of asylum"].map(code_lookup)
map_data["Latitude"] = map_data["Code"].map(lambda code: CAPITALS.get(code, (None, None, None))[0])
map_data["Longitude"] = map_data["Code"].map(lambda code: CAPITALS.get(code, (None, None, None))[1])
map_data["Capital"] = map_data["Code"].map(lambda code: CAPITALS.get(code, (None, None, None))[2])
map_data = map_data.dropna(subset=["Latitude", "Longitude"])
max_map_value = map_data["First-time applications"].max()
map_data["Marker_Size"] = 12 + 28 * (map_data["First-time applications"] / max_map_value).pow(.5) if max_map_value else 16

fig_map = px.scatter_map(
    map_data, lat="Latitude", lon="Longitude", size="Marker_Size", size_max=34,
    color="First-time applications", hover_name="Country of asylum",
    hover_data={"Capital": True, "First-time applications": ":,.0f", "Marker_Size": False, "Latitude": False, "Longitude": False},
    color_continuous_scale=["#80D4EE", UNHCR_BLUE, EU_BLUE], map_style="open-street-map", zoom=2.3,
    center={"lat": 50, "lon": 12},
)
fig_map.update_traces(marker=dict(opacity=.86))
fig_map.update_layout(
    title=dict(text="First-time applications by country of asylum", x=.02, y=.97, xanchor="left", yanchor="top", font=dict(size=18, color=NAVY)),
    height=560, margin=dict(l=8, r=8, t=65, b=8), paper_bgcolor="rgba(0,0,0,0)",
    coloraxis_colorbar=dict(title="Applications", thickness=12, len=.65),
)
st.plotly_chart(fig_map, use_container_width=True)

# -----------------------------
# Data quality and download
# -----------------------------
with st.expander("View and download the Eurostat observations"):
    output_columns = ["Date", "Year", "Month", "Country of asylum", "Nationality", "First-time applications", "Status"]
    table = df[output_columns].sort_values(["Date", "Country of asylum", "Nationality"], ascending=[False, True, True]).copy()
    table["Date"] = table["Date"].dt.strftime("%Y-%m")
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button(
        "Download selected Eurostat data as CSV",
        table.to_csv(index=False).encode("utf-8"),
        file_name="eurostat_first_time_asylum_applications.csv",
        mime="text/csv",
    )

updated_text = f" Eurostat response updated: {last_updated}." if last_updated else ""
st.caption(f"Showing {len(df):,} monthly country-nationality observations. Source: Eurostat, dataset migr_asyappctzm.{updated_text}")
