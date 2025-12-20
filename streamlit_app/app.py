"""

STREAMLIT DASHBOARD - PRODUCTION-GRADE MEMORY-SAFE (SQL-ONLY, MYSQL 8)

======================================================================

CRITICAL ARCHITECTURE CHANGES:

1. REMOVED: load_data_from_mysql() - NO full table loading

2. REMOVED: pd.read_sql("SELECT *") - causes OOM for 1.1M rows

3. ADDED: load_filter_metadata() - lightweight SQL metadata queries

4. ADDED: SQL-based KPI calculations (SUM, COUNT, AVG at DB level)

5. FIXED: All date expressions now ONLY_FULL_GROUP_BY compliant

MySQL 8 ONLY_FULL_GROUP_BY Compliance:

- NEVER reference ungrouped columns in SELECT

- Group ONLY by final columns: YEAR(order_date), MONTH(order_date)

- Derive new columns from grouped columns only

- No DATE_TRUNC, no DATE_FORMAT with % codes

- All aggregates at SQL level, not pandas

- Zero memory accumulation

UI RESTRUCTURING (V3.4):

- SIDEBAR: Navigation + Filters ONLY (no descriptive content)

- MAIN BODY: Page header with title, subtitle, metadata

- Reusable render_page_header() function for consistency

- Clean separation of concerns

Author: Data Engineering Team

Version: 3.4 (UI Refactored: Clean sidebar, centered headers)

"""

import sys

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

import pandas as pd

import numpy as np

import plotly.express as px

import plotly.graph_objects as go

from sqlalchemy import create_engine, text

from scripts import config

import logging

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Amazon India Analytics", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def get_db_engine():
    """Get MySQL database engine."""
    return create_engine(config.DATABASE_URL, echo=False)

@st.cache_data(ttl=3600)
def load_filter_metadata():
    """Load ONLY metadata needed for filters (DISTINCT values, year range).

    Returns lightweight dict with:

    - years: list of years

    - categories: list of categories

    - cities: list of cities

    - payment_methods: list of payment methods

    This replaces loading the full 1.1M row table.

    """
    engine = get_db_engine()

    metadata = {}

    query_years = "SELECT MIN(YEAR(order_date)) as min_year, MAX(YEAR(order_date)) as max_year FROM transactions"

    result_years = pd.read_sql(query_years, engine)

    min_year = int(result_years['min_year'][0])

    max_year = int(result_years['max_year'][0])

    metadata['years'] = list(range(min_year, max_year + 1))

    query_cats = "SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL ORDER BY category"

    result_cats = pd.read_sql(query_cats, engine)

    metadata['categories'] = ['All'] + result_cats['category'].tolist()

    query_cities = "SELECT DISTINCT customer_city FROM transactions WHERE customer_city IS NOT NULL ORDER BY customer_city"

    result_cities = pd.read_sql(query_cities, engine)

    metadata['cities'] = ['All'] + result_cities['customer_city'].tolist()

    query_payments = "SELECT DISTINCT payment_method FROM transactions WHERE payment_method IS NOT NULL ORDER BY payment_method"

    result_payments = pd.read_sql(query_payments, engine)

    metadata['payment_methods'] = result_payments['payment_method'].tolist()

    return metadata

def build_where_clause(filters):
    """Build WHERE clause from filters."""
    where_clauses = []

    if filters['years']:
        years_str = ','.join(map(str, filters['years']))
        where_clauses.append(f"YEAR(order_date) IN ({years_str})")

    if filters['category'] != 'All':
        where_clauses.append(f"category = '{filters['category']}'")

    if filters['city'] != 'All':
        where_clauses.append(f"customer_city = '{filters['city']}'")

    if filters['payment_method']:
        methods_str = ','.join([f"'{m}'" for m in filters['payment_method']])
        where_clauses.append(f"payment_method IN ({methods_str})")

    if filters['prime_status'] == 'Prime':
        where_clauses.append("is_prime_member = True")

    elif filters['prime_status'] == 'Non-Prime':
        where_clauses.append("is_prime_member = False")

    if filters['festival']:
        where_clauses.append("is_festival_sale = True")

    return " AND ".join(where_clauses) if where_clauses else "1=1"

def get_kpi_metrics(filters):
    """Calculate KPI metrics using SQL aggregates (not pandas)."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    SUM(final_amount_inr) as total_revenue,

    COUNT(*) as total_orders,

    COUNT(DISTINCT customer_id) as unique_customers,

    AVG(final_amount_inr) as avg_order_value

    FROM transactions

    WHERE {where_clause}

    """

    result = pd.read_sql(query, engine)

    return {

        'total_revenue': result['total_revenue'][0] or 0,

        'total_orders': result['total_orders'][0] or 0,

        'unique_customers': result['unique_customers'][0] or 0,

        'avg_order_value': result['avg_order_value'][0] or 0,

    }

def get_monthly_revenue(filters):
    """Get monthly revenue trend - ONLY_FULL_GROUP_BY compliant.

    Groups by YEAR(order_date), MONTH(order_date) only.

    Derives month display column from grouped columns.

    """
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    YEAR(order_date) as year,

    MONTH(order_date) as month_num,

    SUM(final_amount_inr) as revenue

    FROM transactions

    WHERE {where_clause}

    GROUP BY YEAR(order_date), MONTH(order_date)

    ORDER BY YEAR(order_date), MONTH(order_date)

    """

    result = pd.read_sql(query, engine)

    if not result.empty:

        result['month'] = pd.to_datetime(

            result['year'].astype(str) + '-' + result['month_num'].astype(str).str.zfill(2) + '-01'

        )

        result = result[['month', 'revenue']]

    return result

def get_category_revenue(filters, limit=10):
    """Get revenue by category."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    category,

    SUM(final_amount_inr) as revenue

    FROM transactions

    WHERE {where_clause}

    GROUP BY category

    ORDER BY revenue DESC

    LIMIT {limit}

    """

    return pd.read_sql(query, engine)

def get_payment_distribution(filters):
    """Get payment method distribution."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    payment_method,

    COUNT(*) as count

    FROM transactions

    WHERE {where_clause}

    GROUP BY payment_method

    ORDER BY count DESC

    """

    return pd.read_sql(query, engine)

def get_yearly_revenue(filters):
    """Get annual revenue."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    YEAR(order_date) as year,

    SUM(final_amount_inr) as revenue

    FROM transactions

    WHERE {where_clause}

    GROUP BY YEAR(order_date)

    ORDER BY year

    """

    return pd.read_sql(query, engine)

def get_rating_distribution(filters):
    """Get customer rating distribution."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    ROUND(customer_rating, 1) as rating,

    COUNT(*) as count

    FROM transactions

    WHERE {where_clause}

    GROUP BY ROUND(customer_rating, 1)

    ORDER BY rating

    """

    return pd.read_sql(query, engine)

def get_category_details(filters):
    """Get detailed category analysis."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    category,

    SUM(final_amount_inr) as total_revenue,

    COUNT(*) as orders,

    AVG(final_amount_inr) as avg_value

    FROM transactions

    WHERE {where_clause}

    GROUP BY category

    ORDER BY total_revenue DESC

    """

    return pd.read_sql(query, engine)

def get_monthly_average_revenue(filters):
    """Get average revenue by month (seasonal pattern) - ONLY_FULL_GROUP_BY compliant.

    Groups by MONTH(order_date) only (aggregates across all years).

    """
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    MONTH(order_date) as month,

    AVG(final_amount_inr) as avg_revenue

    FROM transactions

    WHERE {where_clause}

    GROUP BY MONTH(order_date)

    ORDER BY month

    """

    return pd.read_sql(query, engine)

def get_city_customer_distribution(filters, limit=15):
    """Get geographic customer distribution."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    customer_city,

    COUNT(DISTINCT customer_id) as customer_count,

    SUM(final_amount_inr) as revenue

    FROM transactions

    WHERE {where_clause}

    GROUP BY customer_city

    ORDER BY customer_count DESC

    LIMIT {limit}

    """

    return pd.read_sql(query, engine)

def get_top_products(filters, limit=20):
    """Get top products by revenue."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    product_name,

    SUM(final_amount_inr) as revenue,

    COUNT(*) as order_count,

    AVG(product_rating) as avg_rating

    FROM transactions

    WHERE {where_clause}

    GROUP BY product_name

    ORDER BY revenue DESC

    LIMIT {limit}

    """

    return pd.read_sql(query, engine)

def get_operations_metrics(filters):
    """Get operational metrics."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    AVG(delivery_days) as avg_delivery_days,

    SUM(delivery_charges) as total_delivery_charges,

    SUM(CASE WHEN delivery_days <= 3 THEN 1 ELSE 0 END) as on_time_count,

    COUNT(*) as total_orders

    FROM transactions

    WHERE {where_clause}

    """

    result = pd.read_sql(query, engine)

    return {

        'avg_delivery_days': result['avg_delivery_days'][0] or 0,

        'total_delivery_charges': result['total_delivery_charges'][0] or 0,

        'on_time_pct': (result['on_time_count'][0] / result['total_orders'][0] * 100) if result['total_orders'][0] > 0 else 0,

    }

def get_payment_revenue(filters):
    """Get revenue by payment method."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    payment_method,

    SUM(final_amount_inr) as revenue

    FROM transactions

    WHERE {where_clause}

    GROUP BY payment_method

    ORDER BY revenue DESC

    """

    return pd.read_sql(query, engine)

def get_product_metrics(filters):
    """Get product metrics."""
    engine = get_db_engine()

    where_clause = build_where_clause(filters)

    query = f"""

    SELECT

    COUNT(DISTINCT product_id) as unique_products,

    AVG(product_rating) as avg_rating,

    SUM(CASE WHEN return_status = 'Returned' THEN 1 ELSE 0 END) as returned_count,

    COUNT(*) as total_orders

    FROM transactions

    WHERE {where_clause}

    """

    result = pd.read_sql(query, engine)

    return {

        'unique_products': result['unique_products'][0] or 0,

        'avg_rating': result['avg_rating'][0] or 0,

        'return_rate': (result['returned_count'][0] / result['total_orders'][0] * 100) if result['total_orders'][0] > 0 else 0,

    }

def format_currency(value):
    return f"₹{value:,.0f}"

def format_number(value):
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value/1_000:.1f}K"
    else:
        return f"{value:,.0f}"

def create_sidebar_filters(metadata):
    """Create interactive filters using metadata (NOT full DataFrame).
    
    Sidebar contains ONLY:
    - Navigation (handled in main())
    - Filter Controls
    
    """
    st.sidebar.markdown("### 🎛️ Filter Controls")
    st.sidebar.markdown("---")
    
    filters = {}

    filters['years'] = st.sidebar.multiselect(
        "Select Years",
        metadata['years'],
        default=[metadata['years'][-1]],
        key="year_filter"
    )

    filters['category'] = st.sidebar.selectbox(
        "Select Category",
        metadata['categories'],
        key="category_filter"
    )

    filters['city'] = st.sidebar.selectbox(
        "Select City",
        metadata['cities'],
        key="city_filter"
    )

    filters['payment_method'] = st.sidebar.multiselect(
        "Select Payment Methods",
        metadata['payment_methods'],
        default=metadata['payment_methods'][:3] if len(metadata['payment_methods']) >= 3 else metadata['payment_methods'],
        key="payment_filter"
    )

    filters['prime_status'] = st.sidebar.selectbox(
        "Prime Membership Status",
        ['All', 'Prime', 'Non-Prime'],
        key="prime_filter"
    )

    filters['festival'] = st.sidebar.checkbox(
        "Festival Sales Only",
        value=False,
        key="festival_filter"
    )

    return filters

def render_page_header(page_name):
    """Render consistent page header with title, subtitle, and metadata.
    
    This function is reusable across all dashboard pages.
    
    Args:
        page_name: str, e.g., "Executive Dashboard", "Revenue Analytics"
    
    """
    st.markdown(
        """
        <div style='text-align: center; padding-bottom: 20px;'>
            <h1 style='margin-bottom: 0px;'>📊 Amazon India Analytics</h1>
            <p style='margin-top: 5px; font-size: 16px; color: #666;'>Comprehensive e-commerce analytics platform</p>
            <p style='margin-top: 5px; font-size: 14px; color: #888;'>📅 Data Period: 2015–2025</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    st.markdown(f"## {page_name}", unsafe_allow_html=True)
    st.markdown("")

def page_executive_dashboard():
    """Executive summary dashboard with KPIs."""
    render_page_header("📊 Executive Dashboard")
    
    metadata = load_filter_metadata()
    filters = create_sidebar_filters(metadata)

    kpis = get_kpi_metrics(filters)

    st.subheader("📈 Key Performance Indicators")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Revenue", format_currency(kpis['total_revenue']))

    with col2:
        st.metric("Total Orders", format_number(kpis['total_orders']))

    with col3:
        st.metric("Unique Customers", format_number(kpis['unique_customers']))

    with col4:
        st.metric("Avg Order Value", format_currency(kpis['avg_order_value']))

    st.divider()

    st.subheader("💹 Revenue Trend")

    monthly_data = get_monthly_revenue(filters)

    if not monthly_data.empty:
        fig_trend = px.area(monthly_data, x='month', y='revenue', title="Monthly Revenue Trend", labels={'x': 'Date', 'y': 'Revenue (₹)'})
        st.plotly_chart(fig_trend, use_container_width=True)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏆 Top Categories")
        cat_data = get_category_revenue(filters)
        if not cat_data.empty:
            fig_cat = px.bar(cat_data, x='revenue', y='category', orientation='h', title="Revenue by Category")
            st.plotly_chart(fig_cat, use_container_width=True)

    with col2:
        st.subheader("💳 Payment Methods")
        payment_data = get_payment_distribution(filters)
        if not payment_data.empty:
            fig_payment = px.pie(payment_data, values='count', names='payment_method', title="Payment Method Distribution")
            st.plotly_chart(fig_payment, use_container_width=True)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Year-over-Year Comparison")
        yearly_data = get_yearly_revenue(filters)
        if not yearly_data.empty:
            fig_yoy = px.bar(yearly_data, x='year', y='revenue', title="Annual Revenue")
            st.plotly_chart(fig_yoy, use_container_width=True)

    with col2:
        st.subheader("⭐ Customer Rating Distribution")
        rating_data = get_rating_distribution(filters)
        if not rating_data.empty:
            fig_rating = px.bar(rating_data, x='rating', y='count', title="Customer Rating Distribution")
            st.plotly_chart(fig_rating, use_container_width=True)

def page_revenue_analytics():
    """Detailed revenue analysis."""
    render_page_header("💰 Revenue Analytics")
    
    metadata = load_filter_metadata()
    filters = create_sidebar_filters(metadata)

    kpis = get_kpi_metrics(filters)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Revenue", format_currency(kpis['total_revenue']))

    with col2:
        st.metric("Average Order Value", format_currency(kpis['avg_order_value']))

    with col3:
        st.metric("Total Orders", format_number(kpis['total_orders']))

    st.divider()

    st.subheader("📊 Revenue by Category")
    cat_details = get_category_details(filters)
    if not cat_details.empty:
        fig_cat = px.bar(cat_details, x='category', y='total_revenue', color='orders', title="Revenue and Order Count by Category", text='total_revenue')
        st.plotly_chart(fig_cat, use_container_width=True)

    st.divider()

    st.subheader("📅 Seasonal Revenue Pattern")
    monthly_avg = get_monthly_average_revenue(filters)
    if not monthly_avg.empty:
        fig_seasonal = px.line(monthly_avg, x='month', y='avg_revenue', title="Average Revenue by Month", markers=True)
        st.plotly_chart(fig_seasonal, use_container_width=True)

def page_customer_analytics():
    """Customer segmentation and behavior analysis."""
    render_page_header("👥 Customer Analytics")
    
    metadata = load_filter_metadata()
    filters = create_sidebar_filters(metadata)

    kpis = get_kpi_metrics(filters)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Unique Customers", format_number(kpis['unique_customers']))

    with col2:
        st.metric("Prime Members %", "N/A")

    with col3:
        avg_purchases = kpis['total_orders'] / kpis['unique_customers'] if kpis['unique_customers'] > 0 else 0
        st.metric("Avg Purchases/Customer", f"{avg_purchases:.1f}")

    st.divider()

    st.subheader("🗺️ Geographic Customer Distribution")
    city_data = get_city_customer_distribution(filters)
    if not city_data.empty:
        fig_geo = px.bar(city_data, x='customer_city', y='customer_count', color='revenue', title="Top 15 Cities by Customer Count", text='customer_count')
        st.plotly_chart(fig_geo, use_container_width=True)

def page_product_analytics():
    """Product performance and inventory analysis."""
    render_page_header("📦 Product Analytics")
    
    metadata = load_filter_metadata()
    filters = create_sidebar_filters(metadata)

    metrics = get_product_metrics(filters)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Products Sold", format_number(metrics['unique_products']))

    with col2:
        st.metric("Avg Product Rating", f"{metrics['avg_rating']:.2f}⭐")

    with col3:
        st.metric("Overall Return Rate", f"{metrics['return_rate']:.1f}%")

    st.divider()

    st.subheader("🏆 Top 20 Products by Revenue")
    top_products = get_top_products(filters)
    if not top_products.empty:
        fig_products = px.bar(top_products, x='product_name', y='revenue', color='avg_rating', title="Top 20 Products by Revenue", text='order_count')
        fig_products.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_products, use_container_width=True)

def page_operations():
    """Operations, delivery, and payment analysis."""
    render_page_header("🚚 Operations & Logistics")
    
    metadata = load_filter_metadata()
    filters = create_sidebar_filters(metadata)

    ops_metrics = get_operations_metrics(filters)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Avg Delivery Days", f"{ops_metrics['avg_delivery_days']:.1f}")

    with col2:
        st.metric("On-time Delivery %", f"{ops_metrics['on_time_pct']:.1f}%")

    with col3:
        st.metric("Delivery Charges (Total)", format_currency(ops_metrics['total_delivery_charges']))

    st.divider()

    st.subheader("💳 Payment Method Analysis")

    col1, col2 = st.columns(2)

    with col1:
        payment_dist = get_payment_distribution(filters)
        if not payment_dist.empty:
            fig_payment = px.pie(payment_dist, values='count', names='payment_method', title="Payment Method Distribution")
            st.plotly_chart(fig_payment, use_container_width=True)

    with col2:
        payment_rev = get_payment_revenue(filters)
        if not payment_rev.empty:
            fig_payment_rev = px.bar(payment_rev, x='payment_method', y='revenue', title="Revenue by Payment Method")
            st.plotly_chart(fig_payment_rev, use_container_width=True)

def main():
    """Main app function with clean sidebar navigation."""
    # ============================================
    # SIDEBAR: Navigation Only
    # ============================================
    st.sidebar.markdown("### 🧭 Navigation")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Select Dashboard",
        ["Executive Dashboard", "Revenue Analytics", "Customer Analytics", "Product Analytics", "Operations"],
        index=0,
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("")
    
    # ============================================
    # MAIN CONTENT: Page-specific rendering
    # ============================================
    if page == "Executive Dashboard":
        page_executive_dashboard()
    elif page == "Revenue Analytics":
        page_revenue_analytics()
    elif page == "Customer Analytics":
        page_customer_analytics()
    elif page == "Product Analytics":
        page_product_analytics()
    elif page == "Operations":
        page_operations()

if __name__ == "__main__":
    main()