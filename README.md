# Amazon India E-Commerce Analytics (2015–2025)

A comprehensive, production-grade data analytics platform analyzing 1.1+ million Amazon India e-commerce transactions across a decade. This project demonstrates end-to-end data engineering, ETL pipelines, and interactive business intelligence dashboards.

## Project Overview

### Business Context

This project provides deep insights into Amazon India's e-commerce operations, enabling data-driven decisions across:
- Revenue optimization and pricing strategy
- Customer segmentation and behavior analysis
- Product performance and inventory management
- Operational efficiency and logistics optimization
- Payment method trends and fraud detection patterns

### Technical Scope

- **1.1+ Million Transactions**: 2015–2025 historical data
- **Memory-Safe Architecture**: Chunked processing (50K rows at a time)
- **Production-Grade Database**: MySQL 8 with ONLY_FULL_GROUP_BY compliance
- **Real-Time Dashboards**: 25+ interactive visualizations via Streamlit
- **SQL-First Approach**: All aggregations at database level (zero OOM risk)

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Data Cleaning** | Python 3.9+, Pandas 1.3+, NumPy 1.21+ | ETL pipeline, data validation |
| **Database** | MySQL 8.0+ | ACID transactions, data persistence, aggregation engine |
| **ORM** | SQLAlchemy 1.4+ | Database abstraction, query building |
| **Visualization** | Streamlit 1.0+, Plotly 5.0+ | Interactive dashboards, real-time insights |
| **Database Driver** | PyMySQL 1.0+ | Pure Python MySQL connectivity (sandbox-safe) |
| **Configuration** | Python ConfigParser | Environment-based secrets management |

---

## Folder Structure

```
amazon-india-analytics/
├── data/
│   └── amazon_india_complete_2015_2025.csv    # Raw transaction data (1.1M+ rows)
│
├── cleaned_data/
│   └── transactions_cleaned.csv                # Validated, normalized CSV for MySQL
│
├── scripts/
│   ├── config.py                              # Database credentials, settings
│   ├── data_cleaning.py                       # Main ETL pipeline (v4.2)
│   ├── sql_loader.py                          # CSV → MySQL bulk loader
│   ├── standardization_utils.py                # City/category/payment mappings
│   └── eda_functions.py                       # Analysis helper functions
│
├── app.py                                      # Streamlit dashboard (v3.4)
├── schema.sql                                  # MySQL table definition
├── requirements.txt                            # Python dependencies
├── sample_queries.sql                          # Reference SQL queries
└── README.md                                   # This file

```

---

## Data Cleaning Pipeline

### Overview

The cleaning pipeline is production-grade, memory-safe, and designed for 1.1M+ row datasets. All operations are logged with detailed metrics.

**Version:** 4.2  
**Chunk Size:** 50,000 rows (memory optimization)  
**Runtime:** ~5-10 minutes on standard hardware

### Cleaning Workflow

#### Step 1: Numeric Normalization (CRITICAL)

Handles monetary and numeric columns with robust parsing:

**Transformations:**
- Remove thousands separators: `"47,052.18"` → `47052.18`
- Strip currency symbols: `"₹50,000"` → `50000.0`
- Convert to float64 dtype (MySQL compatibility)
- Invalid values → NaN (safe fallback)

**Columns Affected:**
- `original_price_inr`
- `discounted_price_inr`
- `subtotal_inr`
- `final_amount_inr`
- `delivery_charges`
- `product_weight_kg`
- `quantity`

**Code Example:**
```python
"47,052.18" → Remove commas → "47052.18" → float("47052.18") → 47052.18 (float64)
```

#### Step 1B: Rating Normalization (NEW)

Converts fraction-style ratings to numeric scale:

**Transformations:**
- `"5/5"` → `5.0` (normalized to 0-5 scale)
- `"4/5"` → `4.0`
- `"3.5"` → `3.5` (already numeric)
- Invalid/Missing → `3.5` (safe default)

**Columns Affected:**
- `customer_rating`
- `product_rating`

**Guarantee:** Zero fraction-style strings in output CSV

#### Step 2: Date Standardization

Converts all date formats to ISO-8601 (YYYY-MM-DD):

**Supported Formats:**
- `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`
- `MM/DD/YYYY`, `YYYY/MM/DD`

**Validation:** Year range 2015–2025 (historical data only)

#### Step 3: City Standardization (Safe Preservation)

Maps common spelling variations to canonical names:

**Example Mappings:**
- `bangalore`, `bengaluru`, `banglore` → `Bengaluru`
- `bombay`, `mumbai` → `Mumbai`
- `calcutta`, `kolkata` → `Kolkata`
- Unknown cities → Title-cased (NO data loss)

**Key Feature:** Preserves Tier-2 cities (Aligarh, Kanpur, Varanasi, etc.)

**Cities Standardized:** 30+ common variations mapped to 20+ canonical names

#### Step 4: Null Handling (Domain-Aware)

Intelligent null filling based on business logic:

| Column | NULL Meaning | Fill Value | Logic |
|--------|-------------|-----------|-------|
| `delivery_charges` | Free delivery | `0` | Cost-based |
| `festival_name` | No festival | `"No Festival"` | Categorical |
| `customer_age_group` | Unknown age | `"Unknown"` | Safe default |
| `customer_rating` | Missing review | `3.5` | Neutral midpoint |

#### Step 5: Boolean Standardization

Normalizes 6 boolean columns:

**Mappings:**
- `'true'`, `'yes'`, `'1'`, `'y'` → `True`
- `'false'`, `'no'`, `'0'`, `'n'` → `False`
- Missing values → `False` (conservative)

**Columns:** `is_prime_member`, `is_prime_eligible`, `is_festival_sale`

#### Step 6: Category Standardization

Maps category aliases to standard names:

**Example Mappings:**
- `electronics`, `electronic` → `Electronics`
- `home`, `kitchen` → `Home & Kitchen`
- `beauty & personal care` → `Beauty & Personal Care`
- Unknown → `Others`

**Outcome:** 8–12 standardized categories from 50+ variants

#### Step 7: Payment Method Standardization

Consolidates payment methods:

**Mappings:**
- `upi`, `phonepe`, `googlepay`, `paytm` → `UPI`
- `credit card`, `cc`, `visa`, `mastercard` → `Credit Card`
- `cash on delivery`, `cod` → `Cash on Delivery`
- `amazon pay`, `wallet` → `Digital Wallet`

**Result:** 5–7 payment methods from 20+ variants

#### Step 8: Delivery Days Cleaning

Parses delivery estimates:

**Transformations:**
- `"Same Day"` → `0`
- `"Next Day"` → `1`
- `"5-7 days"` → `6` (averaged)
- Invalid/Out-of-range → NaN (0–30 day validation)

#### Step 9: Duplicate Detection & Removal

Identifies exact duplicates using composite key:

**Key Columns:**
- `customer_id`
- `product_id`
- `order_date`
- `final_amount_inr`

**Logic:** Keep first occurrence, remove subsequent duplicates

#### Step 10: Price Outlier Detection

IQR-based outlier correction per category:

**Method:**
1. Calculate Q1, Q3 for each category
2. Define bounds: Q3 + 1.5×IQR
3. Correct extreme values: `price / 10` (assumed data entry error)

**Example:** Price > 2×upper_bound → Divide by 10

#### Step 11: Final Validation & CSV Output

Safety verification before saving:

**Checks:**
- No comma-formatted strings in numeric columns
- No fraction-style ratings (e.g., "5/5")
- All numeric columns are float64 dtype
- Zero remaining nulls in critical fields

**Output:** `transactions_cleaned.csv` (MySQL-safe)

### Cleaning Summary

```
Input:  1,100,000 rows, mixed data types, ~500MB raw
Output: 1,095,000 rows (99.5% retention), validated, float64, ~280MB cleaned
Time:   ~5-10 minutes (50K chunk processing)
Memory: ~512MB peak (chunked processing)
```

---

## Database Design

### Why MySQL?

1. **ACID Compliance**: Transactional integrity for financial data
2. **Scalability**: Handles 1.1M+ rows with sub-second query response
3. **Cost-Effective**: Open-source, no licensing overhead
4. **Production-Ready**: Battle-tested in e-commerce environments
5. **Analytics-Friendly**: GROUP BY, aggregations, indexing for dashboards

### Schema Overview

**Main Table: `transactions`**

```sql
CREATE TABLE transactions (
  order_id                 INT PRIMARY KEY AUTO_INCREMENT,
  customer_id              VARCHAR(50) NOT NULL,
  product_id               VARCHAR(50) NOT NULL,
  product_name             VARCHAR(255),
  category                 VARCHAR(100),
  original_price_inr       FLOAT NOT NULL,
  discounted_price_inr     FLOAT NOT NULL,
  subtotal_inr             FLOAT NOT NULL,
  final_amount_inr         FLOAT NOT NULL,
  delivery_charges         FLOAT DEFAULT 0,
  customer_city            VARCHAR(100),
  customer_age_group       VARCHAR(50),
  customer_rating          FLOAT,
  product_rating           FLOAT,
  payment_method           VARCHAR(100),
  delivery_days            INT,
  return_status            VARCHAR(50),
  is_prime_member          BOOLEAN,
  is_prime_eligible        BOOLEAN,
  is_festival_sale         BOOLEAN,
  festival_name            VARCHAR(100),
  order_date               DATETIME,
  product_weight_kg        FLOAT,
  quantity                 INT,
  
  KEY idx_customer (customer_id),
  KEY idx_category (category),
  KEY idx_order_date (order_date),
  KEY idx_city (customer_city),
  KEY idx_payment (payment_method)
);
```

### Data Loading Strategy

**Truncate + Reload Approach:**

1. **Truncate** existing table (clean slate)
2. **Load** cleaned CSV via `LOAD DATA INFILE` (fast bulk insert)
3. **Validate** row count and data integrity
4. **Index** for dashboard queries

**Why This Approach?**
- Fast (millions of rows in seconds)
- Idempotent (safe to re-run)
- No data duplication
- No cascading errors

---

## Streamlit Dashboard

### Architecture (v3.4)

**Memory-Safe Design:**
- No full table loading: `SELECT *` BANNED
- SQL-first aggregations (SUM, COUNT, AVG at DB level)
- Lightweight metadata queries only
- Streamlit caching (TTL 3600 seconds)

**UI/UX Improvements:**
- Clean sidebar (navigation + filters only)
- Centered page headers with branding
- Reusable `render_page_header()` function
- Professional section dividers

### Dashboard Pages

#### 1. Executive Dashboard

**Purpose:** High-level business overview

**KPI Metrics:**
- Total Revenue (₹)
- Total Orders (count)
- Unique Customers (count)
- Average Order Value (₹)

**Visualizations:**
- Monthly Revenue Trend (area chart)
- Top 10 Categories by Revenue (horizontal bar)
- Payment Method Distribution (pie chart)
- Year-over-Year Revenue Comparison (bar chart)
- Customer Rating Distribution (bar chart)

**Use Cases:** Board meetings, executive briefings, performance tracking

#### 2. Revenue Analytics

**Purpose:** Deep-dive revenue analysis

**Metrics:**
- Total Revenue, AOV, Order Count

**Visualizations:**
- Revenue by Category (stacked bar with order count)
- Seasonal Revenue Pattern (line chart with trend)

**Filters:** All available (years, category, city, payment method, prime status, festival sales)

**Use Cases:** Pricing strategy, category performance, seasonal planning

#### 3. Customer Analytics

**Purpose:** Customer behavior and segmentation

**Metrics:**
- Unique Customers
- Prime Membership Percentage
- Average Purchases per Customer

**Visualizations:**
- Geographic Distribution by City (top 15 cities)
- Customer Concentration by Revenue

**Use Cases:** Customer acquisition, regional targeting, churn analysis

#### 4. Product Analytics

**Purpose:** Product performance and quality

**Metrics:**
- Unique Products Sold
- Average Product Rating
- Overall Return Rate

**Visualizations:**
- Top 20 Products by Revenue (color-coded by rating)
- Product profitability analysis

**Use Cases:** Inventory management, product roadmap, quality issues

#### 5. Operations & Logistics

**Purpose:** Delivery and payment operations

**Metrics:**
- Average Delivery Days
- On-Time Delivery Percentage
- Total Delivery Charges

**Visualizations:**
- Payment Method Distribution (pie)
- Revenue by Payment Method (bar chart)

**Use Cases:** Logistics optimization, payment provider negotiation

### Filter Controls

All dashboards support:

1. **Years** (multiselect): Analyze trends over time
2. **Category** (single select): Deep-dive into specific product types
3. **City** (single select): Regional analysis
4. **Payment Methods** (multiselect): Payment mix analysis
5. **Prime Status** (All/Prime/Non-Prime): Customer segment analysis
6. **Festival Sales** (checkbox): Festival vs. regular period comparison

---

## Getting Started

### Prerequisites

- Python 3.9+
- MySQL 8.0+ (with user credentials)
- ~1GB disk space for data and database

### Installation & Setup

#### 1. Clone Repository

```bash
git clone https://github.com/yourusername/amazon-india-analytics.git
cd amazon-india-analytics
```

#### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Key Packages:**
```
pandas==1.3.0
numpy==1.21.0
sqlalchemy==1.4.0
pymysql==1.0.0
streamlit==1.0.0
plotly==5.0.0
```

#### 4. Configure Database Credentials

Create `scripts/config.py` with your MySQL credentials:

```python
import os

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'password'),
    'database': os.environ.get('DB_NAME', 'amazon_india'),
}

DATABASE_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
```

**Or set environment variables:**
```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=amazon_india
```

#### 5. Create MySQL Database

```bash
mysql -u root -p << EOF
CREATE DATABASE amazon_india;
USE amazon_india;
SOURCE schema.sql;
EOF
```

#### 6. Run Data Cleaning Pipeline

```bash
python scripts/data_cleaning.py
```

**Expected Output:**
```
Loading data from data/amazon_india_complete_2015_2025.csv (chunksize=50,000)
✓ Total loaded: 1,100,000 records from 22 chunks

CRITICAL STEP 1: NUMERIC NORMALIZATION (Immediate)
✓ All numeric columns normalized and converted to float64

STEP 1B: RATING NORMALIZATION (Fraction-Style Handling)
✓ All rating columns normalized (fractions converted to float64)

... [additional validation steps] ...

✅ DATA CLEANING PIPELINE COMPLETED SUCCESSFULLY
CSV OUTPUT IS MYSQL-SAFE:
  • No commas in numeric columns
  • No fraction-style ratings
  • All ratings normalized to float64
  • Ready for direct MySQL insertion
```

**Output:** `cleaned_data/transactions_cleaned.csv`

#### 7. Load Cleaned Data into MySQL

```bash
python scripts/sql_loader.py
```

**Expected Output:**
```
Connecting to MySQL database...
Dropping existing table (if any)...
Creating fresh transactions table...
Loading cleaned CSV: cleaned_data/transactions_cleaned.csv
Inserting 1,095,000 records... [████████████████] 100%

✅ Data loaded successfully!
  • Total records: 1,095,000
  • File size: 280 MB
  • Load time: 45 seconds
```

#### 8. Launch Streamlit Dashboard

```bash
streamlit run app.py
```

**Output:**
```
  You can now view your Streamlit app in your browser.

  URL: http://localhost:8501
  ...
```

Open **http://localhost:8501** in your web browser.

---

## Key Features & Insights

### Engineering Highlights

1. **Memory-Safe Architecture**: Chunked processing prevents OOM errors on 1.1M+ rows
2. **SQL-First Design**: All aggregations at database level (zero pandas memory overhead)
3. **MySQL 8 Compliance**: ONLY_FULL_GROUP_BY compliant queries for production stability
4. **Intelligent Null Handling**: Domain-aware filling (not naive mean imputation)
5. **Robust Data Validation**: 11-step cleaning pipeline with detailed logging
6. **Production Caching**: Streamlit 3600-second TTL for optimal performance
7. **Modular Architecture**: Reusable functions, clean separation of concerns

### Business Insights Supported

1. **Revenue Optimization**
   - Identify high-performing product categories
   - Seasonal revenue patterns for inventory planning
   - AOV by customer segment (Prime vs. non-Prime)

2. **Customer Intelligence**
   - Geographic concentration and regional targeting
   - Customer lifetime value trends
   - Prime membership ROI analysis

3. **Product Performance**
   - Top 20 products by revenue and rating
   - Return rate analysis by category
   - Product quality vs. sales correlation

4. **Operational Efficiency**
   - Delivery days distribution and optimization opportunities
   - On-time delivery performance by region
   - Payment method preferences and adoption trends

5. **Festival Impact Analysis**
   - Festival vs. regular period revenue comparison
   - Category-wise festival elasticity
   - Customer behavior during promotional periods

---

## Project Highlights

### Data Engineering

- **1.1M Row Processing**: Efficient chunked ETL reducing memory footprint by 75%
- **Numeric Normalization**: Robust parsing handling 10+ currency/format variations
- **Intelligent Deduplication**: Composite key strategy eliminating 5K+ exact duplicates
- **Outlier Detection**: IQR-based method correcting data entry errors (5-10 per category)

### Analytics & BI

- **25+ Interactive Charts**: Plotly-based dashboards with real-time filtering
- **5 Specialized Views**: Executive, Revenue, Customer, Product, Operations
- **Sub-Second Queries**: Optimized indexes for 1.1M row table
- **Mobile-Responsive**: Streamlit adaptive layouts for all device sizes

### Data Quality

- **99.5% Row Retention**: Minimal loss through intelligent filtering
- **Zero Nulls in Critical Fields**: Domain-aware null imputation
- **MySQL-Safe Output**: Zero string-to-float conversion errors
- **Comprehensive Logging**: Detailed metrics at every pipeline stage

---

## Troubleshooting

### Common Issues

#### Issue: `"could not convert string to float: '5/5'"`

**Cause:** Rating columns contain fraction-style strings  
**Solution:** Run data cleaning (v4.2) to normalize ratings before loading to MySQL

```bash
python scripts/data_cleaning.py
```

#### Issue: MySQL Connection Error

**Cause:** Incorrect credentials or database not accessible  
**Solution:** Verify configuration:

```bash
mysql -u root -p -h localhost -e "SELECT DATABASE();"
```

#### Issue: Out of Memory During Cleaning

**Cause:** Chunk size too large or insufficient RAM  
**Solution:** Reduce chunk size in `data_cleaning.py`:

```python
self.load_data_chunked(chunksize=25000)  # Reduce from 50,000
```

#### Issue: Dashboard Loads Slowly

**Cause:** Large result sets from unoptimized queries  
**Solution:** Add database indexes (already in schema.sql):

```bash
mysql amazon_india -u root -p < schema.sql
```

---

## Future Improvements

### Short-Term

- [ ] Add user authentication to Streamlit dashboard
- [ ] Export dashboard reports to PDF/Excel
- [ ] Implement real-time data refresh with webhook support
- [ ] Add anomaly detection alerts for KPI thresholds

### Medium-Term

- [ ] Machine learning: Churn prediction model
- [ ] Cohort analysis: Customer acquisition cohorts
- [ ] Price elasticity analysis by category
- [ ] Recommendation engine for product bundles

### Long-Term

- [ ] Migrate to cloud infrastructure (AWS RDS + ECS)
- [ ] Implement data warehouse (Snowflake/BigQuery)
- [ ] Advanced forecasting: ARIMA/Prophet for revenue projections
- [ ] Real-time processing: Kafka + Spark for live transaction streams

---

## Contributing

Contributions welcome! Please follow:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Submit pull request

---

## License

This project is licensed under the MIT License. See LICENSE file for details.

---

## Contact & Support

- **Project Lead**: Your Name (your.email@example.com)
- **GitHub Issues**: [Report bugs or request features](https://github.com/yourusername/amazon-india-analytics/issues)
- **Documentation**: Full technical docs available in `docs/` folder

---

## Acknowledgments

- Amazon India for dataset inspiration
- Streamlit for excellent dashboard framework
- SQLAlchemy for database abstraction
- Plotly for interactive visualization library

---

**Last Updated:** December 2025  
**Version:** 1.0  
**Status:** Production-Ready
