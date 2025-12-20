"""
CONFIGURATION MODULE
==================

Central configuration for the Amazon India analytics project.
Includes database settings, paths, and constants.

Author: Data Engineering Team
Version: 1.0
"""

import os
from pathlib import Path
from typing import Dict
from urllib.parse import quote

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from project root .env file
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")

# =========================================
# PROJECT STRUCTURE PATHS
# =========================================

PROJECT_ROOT = Path(__file__).parent.parent

# Data paths
DATA_DIR = PROJECT_ROOT / "data"
CLEANED_DATA_DIR = PROJECT_ROOT / "cleaned_data"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
SQL_DIR = PROJECT_ROOT / "sql"
STREAMLIT_DIR = PROJECT_ROOT / "streamlit_app"
REPORTS_DIR = PROJECT_ROOT / "reports"
VISUALS_DIR = PROJECT_ROOT / "visuals"

# Input files
RAW_TRANSACTIONS_FILE = DATA_DIR / "amazon_india_complete_2015_2025.csv"
RAW_PRODUCTS_FILE = DATA_DIR / "amazon_india_products_catalog.csv"

# Output files
CLEANED_TRANSACTIONS_FILE = CLEANED_DATA_DIR / "transactions_cleaned.csv"
CLEANED_PRODUCTS_FILE = CLEANED_DATA_DIR / "products_cleaned.csv"
CLEANED_CUSTOMERS_FILE = CLEANED_DATA_DIR / "customers_cleaned.csv"

# =========================================
# DATABASE CONFIGURATION (ENV-BASED)
# =========================================

# Read from environment variables with fallbacks
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')  # Will be read from .env
DB_NAME = os.getenv('DB_NAME', 'amazon_sales_db')
DB_DRIVER = 'mysql+pymysql'

# Build DATABASE_CONFIG dictionary
DATABASE_CONFIG = {
    'host': DB_HOST,
    'port': DB_PORT,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME,
    'driver': DB_DRIVER
}

# ✅ CRITICAL FIX: URL-encode password to handle special characters (@, :, /, etc.)
# This ensures passwords with special characters are properly handled by SQLAlchemy
ENCODED_PASSWORD = quote(DB_PASSWORD, safe='')

# SQLAlchemy connection URL (properly encoded for special characters)
DATABASE_URL = f"{DB_DRIVER}://{DB_USER}:{ENCODED_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLite Configuration (for testing)
SQLITE_DB_PATH = CLEANED_DATA_DIR / "amazon_analytics.db"

# =========================================
# DATA CLEANING PARAMETERS
# =========================================

CLEANING_CONFIG = {
    # Date parameters
    'date_columns': ['order_date'],
    'date_format': '%Y-%m-%d',
    'valid_year_range': (2015, 2025),
    
    # Price parameters
    'price_columns': ['original_price_inr', 'final_amount_inr', 'delivery_charges'],
    'min_price': 0.01,
    'max_price': 999999,
    
    # Rating parameters
    'rating_columns': ['customer_rating', 'product_rating'],
    'rating_min': 1.0,
    'rating_max': 5.0,
    'rating_default': 3.5,
    
    # Delivery parameters
    'min_delivery_days': 0,
    'max_delivery_days': 30,
    'default_delivery_days': 5,
    
    # Boolean columns
    'boolean_columns': ['is_prime_member', 'is_prime_eligible', 'is_festival_sale'],
    
    # Text normalization
    'normalize_text': True,
    'lowercase': True,
    
    # Outlier detection
    'outlier_method': 'iqr',  # Options: iqr, zscore
    'outlier_threshold': 1.5,
}

# =========================================
# STANDARDIZATION MAPPINGS
# =========================================

# City standardization mapping
CITY_MAPPINGS = {
    'bangalore': 'Bengaluru',
    'bengaluru': 'Bengaluru',
    'blr': 'Bengaluru',
    'mumbai': 'Mumbai',
    'bombay': 'Mumbai',
    'delhi': 'Delhi',
    'new delhi': 'Delhi',
    'hyderabad': 'Hyderabad',
    'pune': 'Pune',
    'chennai': 'Chennai',
    'kolkata': 'Kolkata',
    'gurgaon': 'Gurugram',
    'gurugram': 'Gurugram',
    'noida': 'Noida',
    'jaipur': 'Jaipur',
    'indore': 'Indore',
    'lucknow': 'Lucknow',
    'surat': 'Surat',
    'ahmedabad': 'Ahmedabad',
    'coimbatore': 'Coimbatore',
    'kochi': 'Kochi',
    'trivandrum': 'Thiruvananthapuram',
}

# Geographic tier mapping
CITY_TIER_MAPPING = {
    'Mumbai': 'Metro',
    'Delhi': 'Metro',
    'Bengaluru': 'Metro',
    'Hyderabad': 'Metro',
    'Pune': 'Tier1',
    'Ahmedabad': 'Tier1',
    'Jaipur': 'Tier1',
    'Lucknow': 'Tier2',
    'Surat': 'Tier2',
    'Indore': 'Tier2',
    'Kochi': 'Tier2',
    'Kolkata': 'Metro',
    'Chennai': 'Metro',
}

# Category standardization
CATEGORY_MAPPINGS = {
    'electronics': 'Electronics',
    'electronic': 'Electronics',
    'home': 'Home & Kitchen',
    'kitchen': 'Home & Kitchen',
    'beauty': 'Beauty & Personal Care',
    'sports': 'Sports & Outdoors',
    'books': 'Books & Media',
    'toys': 'Toys & Games',
    'fashion': 'Fashion',
}

# Payment method standardization
PAYMENT_MAPPINGS = {
    'upi': 'UPI',
    'phonepe': 'UPI',
    'googlepay': 'UPI',
    'paytm': 'UPI',
    'credit card': 'Credit Card',
    'visa': 'Credit Card',
    'mastercard': 'Credit Card',
    'debit card': 'Debit Card',
    'cash on delivery': 'Cash on Delivery',
    'cod': 'Cash on Delivery',
    'netbanking': 'Net Banking',
    'wallet': 'Digital Wallet',
}

# =========================================
# ANALYSIS PARAMETERS
# =========================================

ANALYSIS_CONFIG = {
    # RFM Analysis
    'rfm_recency_max_days': 365,
    'rfm_frequency_buckets': 4,
    'rfm_monetary_buckets': 4,
    
    # Customer segmentation
    'age_groups': ['Below 18', '18-24', '25-34', '35-44', '45-54', '55+'],
    'spending_tiers': ['Low', 'Medium', 'High', 'Premium'],
    'spending_thresholds': [5000, 15000, 50000, float('inf')],
    
    # Performance metrics
    'on_time_delivery_threshold': 3,  # days
    'good_rating_threshold': 4.0,  # out of 5
    'churn_days_threshold': 90,  # days without purchase
    
    # Seasonal indicators
    'festival_months': {
        'Diwali': [9, 10, 11],
        'Christmas': [12],
        'New Year': [1],
        'Summer Sale': [4, 5],
        'Prime Day': [7],
    }
}

# =========================================
# VISUALIZATION PARAMETERS
# =========================================

VISUALIZATION_CONFIG = {
    'color_palette': 'Set2',
    'figure_size': (14, 8),
    'dpi': 100,
    
    # Colors for categories
    'category_colors': {
        'Electronics': '#FF6B6B',
        'Home & Kitchen': '#4ECDC4',
        'Fashion': '#FFE66D',
        'Beauty & Personal Care': '#95E1D3',
        'Sports & Outdoors': '#F38181',
        'Books & Media': '#AA96DA',
        'Toys & Games': '#FCBAD3',
    },
    
    # Streamlit theme
    'streamlit_theme': 'light',
}

# =========================================
# LOGGING CONFIGURATION
# =========================================

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_file': REPORTS_DIR / 'app.log',
    'level': 'INFO',
}

# =========================================
# BUSINESS CONSTANTS
# =========================================

# Currency
CURRENCY_SYMBOL = '₹'
CURRENCY_CODE = 'INR'

# Indices and Benchmarks
BENCHMARK_KPIs = {
    'revenue_growth_target': 0.15,  # 15% YoY
    'avg_order_value_target': 5000,  # ₹5000
    'customer_retention_target': 0.85,  # 85%
    'return_rate_target': 0.05,  # 5%
    'on_time_delivery_target': 0.95,  # 95%
}

# =========================================
# HELPER FUNCTIONS
# =========================================

def get_database_url() -> str:
    """Get database connection URL."""
    return DATABASE_URL

def get_file_path(file_type: str) -> Path:
    """Get file path by type."""
    file_map = {
        'raw_transactions': RAW_TRANSACTIONS_FILE,
        'raw_products': RAW_PRODUCTS_FILE,
        'cleaned_transactions': CLEANED_TRANSACTIONS_FILE,
        'cleaned_products': CLEANED_PRODUCTS_FILE,
        'cleaned_customers': CLEANED_CUSTOMERS_FILE,
        'sqlite_db': SQLITE_DB_PATH,
    }
    return file_map.get(file_type)

def create_directories() -> None:
    """Create all necessary directories."""
    directories = [
        DATA_DIR,
        CLEANED_DATA_DIR,
        REPORTS_DIR,
        VISUALS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

def get_config_summary() -> Dict:
    """Get summary of current configuration."""
    return {
        'project_root': str(PROJECT_ROOT),
        'database_host': DATABASE_CONFIG['host'],
        'database_name': DATABASE_CONFIG['database'],
        'data_directory': str(DATA_DIR),
        'cleaned_data_directory': str(CLEANED_DATA_DIR),
    }

def verify_env_variables() -> bool:
    """Verify that all required environment variables are loaded."""
    required_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'DB_PORT']
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"⚠️  Missing environment variables: {', '.join(missing)}")
        print(f"   Please check your .env file")
        return False
    
    return True

if __name__ == "__main__":
    # Create directories on import
    create_directories()
    
    # Verify environment variables
    if verify_env_variables():
        print("✅ Configuration Loaded Successfully!")
        print("\n📋 Configuration Summary:")
        for key, value in get_config_summary().items():
            print(f"  {key}: {value}")
        
        print("\n🔒 Database Configuration:")
        print(f"  Host: {DATABASE_CONFIG['host']}")
        print(f"  User: {DATABASE_CONFIG['user']}")
        print(f"  Database: {DATABASE_CONFIG['database']}")
        print(f"  Driver: {DATABASE_CONFIG['driver']}")
        print("\n✅ Connection URL is properly configured with URL-encoded password")
    else:
        print("❌ Configuration verification failed!")