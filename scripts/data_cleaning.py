"""
DATA CLEANING MODULE - AMAZON INDIA E-COMMERCE ANALYTICS (V4.2)
================================================================

PRODUCTION-GRADE CLEANING PIPELINE:
1. Memory-safe chunked loading (50,000 rows per chunk)
2. IMMEDIATE NUMERIC NORMALIZATION (STEP 1 - CRITICAL)
   - Remove commas from all numeric columns
   - Remove currency symbols
   - Convert to float64
   - Invalid values → NaN (safe)
3. RATING NORMALIZATION (NEW)
   - Convert fraction ratings: '5/5' → 5.0, '4/5' → 4.0, etc.
   - Handle numeric ratings as-is
   - Invalid/missing → 3.5 (safe default)
   - Final dtype: float64
4. Date standardization (2015-2025 validation)
5. City standardization (safe preservation, no mode-filling)
6. Null handling (delivery_charges=0, festival_name='No Festival', age='Unknown')
7. Category & payment standardization
8. Price outlier detection & correction
9. Duplicate detection & removal
10. Final validation & CSV output

NUMERIC & RATING NORMALIZATION - GUARANTEED CLEAN OUTPUT:
- Monetary: "47,052.18" → 47052.18 (float64)
- Ratings: "5/5" → 5.0 (float64), "4/5" → 4.0 (float64)
- All numeric columns are FLOAT64
- NO comma-formatted strings remain
- NO fraction-style ratings remain
- NO currency symbols remain
- MySQL-safe for direct insertion

Version: 4.2 (CRITICAL FIX: Rating normalization for fraction-style ratings)
"""

import pandas as pd
import numpy as np
import re
import logging
from typing import Tuple, List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCleaner:
    """Production-grade data cleaning for Amazon India e-commerce dataset."""
    
    def __init__(self, input_path: str, output_path: str = None):
        """Initialize cleaner with input/output paths."""
        self.input_path = input_path
        self.output_path = output_path or input_path.replace('.csv', '_cleaned.csv')
        self.df = None
        self.cleaning_report = {}
        self.original_row_count = 0
        self.original_cols = set()

    def load_data_chunked(self, chunksize: int = 50000) -> pd.DataFrame:
        """Memory-safe chunked loading for large CSV files."""
        logger.info(f"Loading data from {self.input_path} (chunksize={chunksize:,})")
        chunks = []
        total_rows = 0
        chunk_count = 0
        
        try:
            for chunk in pd.read_csv(self.input_path, chunksize=chunksize, low_memory=False):
                chunks.append(chunk)
                chunk_count += 1
                total_rows += len(chunk)
                logger.info(f" ✓ Chunk {chunk_count}: {len(chunk):,} rows (total: {total_rows:,})")
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            raise
        
        self.df = pd.concat(chunks, ignore_index=True)
        self.original_row_count = len(self.df)
        self.original_cols = set(self.df.columns)
        
        logger.info(f"✓ Total loaded: {len(self.df):,} records from {chunk_count} chunks")
        return self.df

    def normalize_numeric_column(self, col: str) -> None:
        """
        CRITICAL: Normalize numeric columns - remove commas and convert to float.
        
        This MUST happen immediately after loading.
        
        Examples:
            "47,052.18" → 47052.18 (float64)
            "1,000" → 1000.0 (float64)
            "₹50,000" → 50000.0 (float64)
            "$1,234.56" → 1234.56 (float64)
            Invalid → NaN
            
        All numeric columns saved to CSV will be FLOAT64 with no commas.
        """
        if col not in self.df.columns:
            return
        
        logger.info(f"  → Normalizing {col}")
        
        def clean_numeric(val):
            # Handle NaN/None
            if pd.isna(val):
                return np.nan
            
            val_str = str(val).strip()
            
            # Empty strings
            if not val_str or val_str.lower() in ['nan', 'null', 'none', 'na', '']:
                return np.nan
            
            # Remove currency symbols (₹, $, €, £)
            val_str = re.sub(r'[₹$€£]', '', val_str).strip()
            
            # CRITICAL FIX: Remove comma separators
            # "47,052.18" → "47052.18"
            val_str = val_str.replace(',', '')
            
            # Extract numeric value
            # Handles both integers and decimals, positive and negative
            match = re.search(r'-?\d+\.?\d*', val_str)
            
            if not match:
                return np.nan
            
            try:
                numeric_val = float(match.group())
                return numeric_val
            except (ValueError, TypeError):
                return np.nan
        
        before_count = self.df[col].notna().sum()
        before_nulls = self.df[col].isna().sum()
        
        # Apply cleaning
        self.df[col] = self.df[col].apply(clean_numeric)
        
        # Force float64 dtype
        self.df[col] = self.df[col].astype('float64')
        
        after_count = self.df[col].notna().sum()
        after_nulls = self.df[col].isna().sum()
        
        logger.info(f"    ✓ Type: float64")
        logger.info(f"    ✓ Valid: {before_count:,} → {after_count:,} values")
        logger.info(f"    ✓ Nulls: {before_nulls:,} → {after_nulls:,}")
        logger.info(f"    ✓ Range: [{self.df[col].min():.2f}, {self.df[col].max():.2f}]")

    def normalize_all_numeric_columns(self) -> None:
        """
        CRITICAL STEP 1: Normalize ALL monetary and numeric columns immediately.
        
        This MUST be the first cleaning operation (after loading).
        
        Guarantees:
        ✓ All numeric columns are float64
        ✓ No commas in any numeric value
        ✓ No currency symbols
        ✓ CSV output is MySQL-safe
        """
        logger.info("\n" + "="*70)
        logger.info("CRITICAL STEP 1: NUMERIC NORMALIZATION (Immediate)")
        logger.info("="*70)
        logger.info("Normalizing ALL monetary & numeric columns...")
        
        numeric_columns = [
            'original_price_inr',
            'discounted_price_inr',
            'subtotal_inr',
            'final_amount_inr',
            'delivery_charges',
            'product_weight_kg',
            'quantity'
        ]
        
        for col in numeric_columns:
            self.normalize_numeric_column(col)
        
        logger.info(f"\n✓ All numeric columns normalized and converted to float64")
        logger.info(f"✓ CSV output will be MySQL-safe (no commas or symbols)\n")

    def normalize_rating_column(self, col: str) -> None:
        """
        Normalize rating columns: convert fraction-style ratings to float.
        
        Examples:
            '5/5' → 5.0 (float64)
            '4/5' → 4.0 (float64)
            '3.5' → 3.5 (float64)
            '4' → 4.0 (float64)
            Invalid → 3.5 (safe default)
            NaN → 3.5 (safe default)
        
        Args:
            col: Column name (e.g., 'customer_rating', 'product_rating')
        """
        if col not in self.df.columns:
            return
        
        logger.info(f"  → Normalizing rating column: {col}")
        
        def clean_rating(val):
            # Handle NaN/None
            if pd.isna(val):
                return 3.5  # Safe default for missing ratings
            
            val_str = str(val).strip()
            
            # Empty strings
            if not val_str or val_str.lower() in ['nan', 'null', 'none', 'na', '']:
                return 3.5
            
            # Handle fraction-style ratings: '5/5', '4/5', etc.
            if '/' in val_str:
                try:
                    parts = val_str.split('/')
                    numerator = float(parts[0].strip())
                    denominator = float(parts[1].strip())
                    
                    if denominator == 0:
                        return 3.5
                    
                    # Normalize to 0-5 scale
                    rating = (numerator / denominator) * 5.0
                    
                    # Clamp to valid rating range [0, 5]
                    rating = max(0.0, min(5.0, rating))
                    return rating
                except (ValueError, ZeroDivisionError, IndexError):
                    return 3.5
            
            # Handle numeric ratings
            try:
                rating = float(val_str)
                # Clamp to valid rating range [0, 5]
                rating = max(0.0, min(5.0, rating))
                return rating
            except ValueError:
                return 3.5
        
        before_count = self.df[col].notna().sum()
        before_has_fraction = self.df[col].astype(str).str.contains('/').sum()
        
        # Apply cleaning
        self.df[col] = self.df[col].apply(clean_rating)
        
        # Force float64 dtype
        self.df[col] = self.df[col].astype('float64')
        
        after_count = self.df[col].notna().sum()
        after_nulls = self.df[col].isna().sum()
        
        logger.info(f"    ✓ Type: float64")
        logger.info(f"    ✓ Fraction ratings converted: {before_has_fraction:,}")
        logger.info(f"    ✓ Valid: {before_count:,} → {after_count:,} values")
        logger.info(f"    ✓ Nulls: {after_nulls:,} (filled with 3.5 default)")
        logger.info(f"    ✓ Range: [{self.df[col].min():.2f}, {self.df[col].max():.2f}]")
        logger.info(f"    ✓ Mean: {self.df[col].mean():.2f}")

    def normalize_all_rating_columns(self) -> None:
        """
        STEP 1B: Normalize ALL rating columns immediately after numeric normalization.
        
        Handles fraction-style ratings like '5/5', '4/5', etc.
        Ensures all ratings are float64 for MySQL insertion.
        
        Guarantees:
        ✓ All rating columns are float64
        ✓ No fraction-style strings remain
        ✓ Invalid ratings → 3.5 (safe default)
        ✓ CSV output is MySQL-safe
        """
        logger.info("="*70)
        logger.info("STEP 1B: RATING NORMALIZATION (Fraction-Style Handling)")
        logger.info("="*70)
        logger.info("Normalizing ALL rating columns...")
        
        rating_columns = [
            'customer_rating',
            'product_rating'
        ]
        
        for col in rating_columns:
            self.normalize_rating_column(col)
        
        logger.info(f"\n✓ All rating columns normalized (fractions converted to float64)")
        logger.info(f"✓ CSV output will be MySQL-safe (no '5/5' or similar strings)\n")

    def clean_order_dates(self) -> None:
        """Standardize order dates to consistent format (YYYY-MM-DD)."""
        logger.info("="*70)
        logger.info("STEP: DATE STANDARDIZATION (YYYY-MM-DD)")
        logger.info("="*70)
        
        if 'order_date' not in self.df.columns:
            logger.warning("Column 'order_date' not found, skipping date cleaning")
            return
        
        def parse_date(date_str):
            if pd.isna(date_str):
                return pd.NaT
            
            date_str = str(date_str).strip()
            formats = [
                '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y',
                '%d-%m-%Y', '%d-%m-%y', '%m/%d/%Y', '%Y/%m/%d'
            ]
            
            for fmt in formats:
                try:
                    parsed = pd.to_datetime(date_str, format=fmt)
                    if 2015 <= parsed.year <= 2025:
                        return parsed
                except:
                    continue
            
            try:
                parsed = pd.to_datetime(date_str)
                if 2015 <= parsed.year <= 2025:
                    return parsed
            except:
                pass
            
            return pd.NaT
        
        before_nulls = self.df['order_date'].isna().sum()
        self.df['order_date'] = self.df['order_date'].apply(parse_date)
        after_nulls = self.df['order_date'].isna().sum()
        
        logger.info(f"✓ Date cleaning: {before_nulls:,} → {after_nulls:,} nulls\n")

    def clean_delivery_charges(self) -> None:
        """Fix delivery_charges: NaN means FREE delivery (fill with 0)."""
        if 'delivery_charges' not in self.df.columns:
            return
        
        before_nulls = self.df['delivery_charges'].isna().sum()
        self.df['delivery_charges'] = self.df['delivery_charges'].fillna(0)
        after_nulls = self.df['delivery_charges'].isna().sum()
        
        logger.info(f"✓ Delivery charges: {before_nulls:,} NaN → {after_nulls:,} (filled with 0)")
        assert after_nulls == 0, f"Failed to fill delivery_charges nulls: {after_nulls}"

    def clean_festival_name(self) -> None:
        """Fix festival_name: NaN means NO FESTIVAL (fill with 'No Festival')."""
        if 'festival_name' not in self.df.columns:
            return
        
        before_nulls = self.df['festival_name'].isna().sum()
        self.df['festival_name'] = self.df['festival_name'].fillna('No Festival')
        after_nulls = self.df['festival_name'].isna().sum()
        
        logger.info(f"✓ Festival name: {before_nulls:,} NaN → {after_nulls:,} (filled with 'No Festival')")
        assert after_nulls == 0, f"Failed to fill festival_name nulls: {after_nulls}"

    def clean_customer_age_group(self) -> None:
        """Fix customer_age_group: NaN means UNKNOWN (fill with 'Unknown', NO inference)."""
        if 'customer_age_group' not in self.df.columns:
            return
        
        before_nulls = self.df['customer_age_group'].isna().sum()
        self.df['customer_age_group'] = self.df['customer_age_group'].fillna('Unknown')
        after_nulls = self.df['customer_age_group'].isna().sum()
        
        logger.info(f"✓ Age group: {before_nulls:,} NaN → {after_nulls:,} (filled with 'Unknown')")
        assert after_nulls == 0, f"Failed to fill customer_age_group nulls: {after_nulls}"

    def standardize_cities(self, city_col: str = 'customer_city') -> None:
        """
        Standardize city names (SAFE - preserves ALL valid cities).
        
        CRITICAL: Unknown cities are preserved (title-cased), NOT converted to NaN.
        """
        logger.info("="*70)
        logger.info("STEP: CITY STANDARDIZATION (Safe, No Data Loss)")
        logger.info("="*70)
        
        if city_col not in self.df.columns:
            logger.warning(f"Column '{city_col}' not found, skipping city standardization")
            return
        
        city_mappings = {
            'bangalore': 'Bengaluru', 'bengaluru': 'Bengaluru', 'banglore': 'Bengaluru',
            'blr': 'Bengaluru', 'bengalore': 'Bengaluru',
            'mumbai': 'Mumbai', 'bombay': 'Mumbai', 'mumba': 'Mumbai',
            'delhi': 'Delhi', 'new delhi': 'Delhi', 'nd': 'Delhi', 'delhi ncr': 'Delhi',
            'hyderabad': 'Hyderabad', 'hyd': 'Hyderabad', 'hyderabadi': 'Hyderabad',
            'pune': 'Pune', 'poona': 'Pune',
            'chennai': 'Chennai', 'chenai': 'Chennai', 'madras': 'Chennai',
            'kolkata': 'Kolkata', 'calcutta': 'Kolkata',
            'gurgaon': 'Gurugram', 'gurugram': 'Gurugram',
            'noida': 'Noida',
            'jaipur': 'Jaipur',
            'indore': 'Indore',
            'lucknow': 'Lucknow',
            'surat': 'Surat',
            'ahmedabad': 'Ahmedabad',
            'coimbatore': 'Coimbatore',
            'kochi': 'Kochi', 'cochin': 'Kochi',
            'visakhapatnam': 'Visakhapatnam', 'vizag': 'Visakhapatnam',
            'nagpur': 'Nagpur',
            'chandigarh': 'Chandigarh',
            'thiruvananthapuram': 'Thiruvananthapuram', 'trivandrum': 'Thiruvananthapuram',
            'aligarh': 'Aligarh', 'kanpur': 'Kanpur', 'varanasi': 'Varanasi',
            'meerut': 'Meerut', 'gorakhpur': 'Gorakhpur', 'patna': 'Patna',
            'bhubaneswar': 'Bhubaneswar', 'ludhiana': 'Ludhiana',
        }
        
        def standardize_city(city_val):
            if pd.isna(city_val):
                return np.nan
            
            city_str = str(city_val).strip()
            
            if not city_str or city_str.lower() in ['', 'nan', 'null', 'none']:
                return np.nan
            
            city_lower = city_str.lower()
            
            # If in mapping, use mapped value
            if city_lower in city_mappings:
                return city_mappings[city_lower]
            
            # CRITICAL: If NOT in mapping, PRESERVE as valid city (title-case)
            # This prevents loss of Tier-2 cities (Aligarh, Kanpur, etc.)
            return city_str.title()
        
        original_unique = self.df[city_col].nunique()
        before_nulls = self.df[city_col].isna().sum()
        
        self.df[city_col] = self.df[city_col].apply(standardize_city)
        
        final_unique = self.df[city_col].nunique()
        after_nulls = self.df[city_col].isna().sum()
        
        logger.info(f"✓ City standardization: {original_unique} → {final_unique} unique cities")
        logger.info(f"✓ Nulls: {before_nulls:,} → {after_nulls:,}")
        logger.info(f"✓ Canonical cities: {sorted([c for c in self.df[city_col].unique() if pd.notna(c)])[:10]}...\n")

    def standardize_booleans(self, bool_cols: List[str] = None) -> None:
        """Standardize boolean columns."""
        logger.info("="*70)
        logger.info("STEP: BOOLEAN STANDARDIZATION")
        logger.info("="*70)
        
        if bool_cols is None:
            bool_cols = ['is_prime_member', 'is_prime_eligible', 'is_festival_sale']
        
        bool_mappings = {
            'true': True, 'yes': True, '1': True, 'y': True,
            'false': False, 'no': False, '0': False, 'n': False,
            '1.0': True, '0.0': False
        }
        
        def convert_boolean(val):
            if pd.isna(val):
                return False
            val_str = str(val).strip().lower()
            return bool_mappings.get(val_str, False)
        
        for col in bool_cols:
            if col in self.df.columns:
                self.df[col] = self.df[col].apply(convert_boolean)
                true_count = (self.df[col] == True).sum()
                logger.info(f" ✓ {col}: {true_count:,} True values")
        
        logger.info("")

    def standardize_categories(self, cat_col: str = 'category') -> None:
        """Standardize product categories."""
        logger.info("="*70)
        logger.info("STEP: CATEGORY STANDARDIZATION")
        logger.info("="*70)
        
        if cat_col not in self.df.columns:
            logger.warning(f"Column '{cat_col}' not found, skipping category standardization")
            return
        
        category_mappings = {
            'electronics': 'Electronics', 'electronic': 'Electronics',
            'home': 'Home & Kitchen', 'home & kitchen': 'Home & Kitchen', 'kitchen': 'Home & Kitchen',
            'beauty': 'Beauty & Personal Care', 'beauty & personal care': 'Beauty & Personal Care',
            'sports': 'Sports & Outdoors', 'sports & outdoors': 'Sports & Outdoors',
            'books': 'Books & Media', 'books & media': 'Books & Media',
            'toys': 'Toys & Games', 'toys & games': 'Toys & Games',
            'fashion': 'Fashion', 'apparel': 'Fashion', 'clothing': 'Fashion',
        }
        
        def standardize_category(cat_val):
            if pd.isna(cat_val):
                return 'Others'
            cat_str = str(cat_val).strip().lower()
            return category_mappings.get(cat_str, 'Others')
        
        self.df[cat_col] = self.df[cat_col].apply(standardize_category)
        logger.info(f"✓ Categories standardized: {self.df[cat_col].nunique()} unique\n")

    def clean_delivery_days(self, delivery_col: str = 'delivery_days') -> None:
        """Standardize delivery days to numeric format."""
        logger.info("="*70)
        logger.info("STEP: DELIVERY DAYS CLEANING")
        logger.info("="*70)
        
        if delivery_col not in self.df.columns:
            logger.warning(f"Column '{delivery_col}' not found, skipping delivery days cleaning")
            return
        
        def parse_delivery_days(val):
            if pd.isna(val):
                return np.nan
            
            val_str = str(val).strip().lower()
            
            if 'same' in val_str:
                return 0
            elif 'next' in val_str:
                return 1
            
            numbers = re.findall(r'\d+', val_str)
            if numbers:
                avg_days = sum(int(n) for n in numbers) / len(numbers)
                days = int(avg_days)
            else:
                try:
                    days = int(float(val_str))
                except:
                    return np.nan
            
            return days if 0 <= days <= 30 else np.nan
        
        self.df[delivery_col] = self.df[delivery_col].apply(parse_delivery_days)
        logger.info(f"✓ Delivery days: Avg={self.df[delivery_col].mean():.1f} days\n")

    def detect_duplicates(self, subset_cols: List[str] = None) -> pd.DataFrame:
        """Detect duplicate records."""
        logger.info("="*70)
        logger.info("STEP: DUPLICATE DETECTION")
        logger.info("="*70)
        
        if subset_cols is None:
            subset_cols = ['customer_id', 'product_id', 'order_date', 'final_amount_inr']
        
        self.df['is_duplicate'] = self.df.duplicated(subset=subset_cols, keep='first')
        duplicate_count = self.df['is_duplicate'].sum()
        
        logger.info(f"✓ Duplicates detected: {duplicate_count:,}\n")
        
        return self.df[self.df.duplicated(subset=subset_cols, keep=False)]

    def detect_price_outliers(self, price_col: str = 'original_price_inr', category_col: str = 'category') -> None:
        """Detect and fix price outliers using IQR method."""
        logger.info("="*70)
        logger.info("STEP: PRICE OUTLIER DETECTION & CORRECTION")
        logger.info("="*70)
        
        if price_col not in self.df.columns or category_col not in self.df.columns:
            logger.warning(f"Required columns for outlier detection not found, skipping")
            return
        
        outliers_fixed = 0
        
        for category in self.df[category_col].unique():
            if pd.isna(category):
                continue
            
            cat_data = self.df[self.df[category_col] == category][price_col]
            
            if len(cat_data) > 10:
                Q1, Q3 = cat_data.quantile(0.25), cat_data.quantile(0.75)
                IQR = Q3 - Q1
                upper_bound = Q3 + 1.5 * IQR
                
                mask = (self.df[category_col] == category) & (self.df[price_col] > upper_bound * 2)
                
                if mask.any():
                    self.df.loc[mask, price_col] = self.df.loc[mask, price_col] / 10
                    outliers_fixed += mask.sum()
        
        logger.info(f"✓ Outliers corrected: {outliers_fixed:,}\n")

    def standardize_payment_methods(self, payment_col: str = 'payment_method') -> None:
        """Standardize payment methods."""
        logger.info("="*70)
        logger.info("STEP: PAYMENT METHOD STANDARDIZATION")
        logger.info("="*70)
        
        if payment_col not in self.df.columns:
            logger.warning(f"Column '{payment_col}' not found, skipping payment standardization")
            return
        
        payment_mappings = {
            'upi': 'UPI', 'phonepe': 'UPI', 'googlepay': 'UPI', 'paytm': 'UPI',
            'credit card': 'Credit Card', 'cc': 'Credit Card', 'visa': 'Credit Card', 'mastercard': 'Credit Card',
            'debit card': 'Debit Card', 'dc': 'Debit Card',
            'cash on delivery': 'Cash on Delivery', 'cod': 'Cash on Delivery',
            'netbanking': 'Net Banking', 'net banking': 'Net Banking',
            'wallet': 'Digital Wallet', 'amazon pay': 'Digital Wallet',
        }
        
        def standardize_payment(payment_val):
            if pd.isna(payment_val):
                return 'Unknown'
            payment_str = str(payment_val).strip().lower()
            return payment_mappings.get(payment_str, 'Others')
        
        self.df[payment_col] = self.df[payment_col].apply(standardize_payment)
        logger.info(f"✓ Payment methods standardized: {self.df[payment_col].nunique()} unique\n")

    def verify_numeric_columns_clean(self) -> None:
        """
        VERIFICATION: Ensure no numeric columns contain commas or strings.
        
        This is a SAFETY CHECK before saving to CSV.
        """
        logger.info("="*70)
        logger.info("VERIFICATION: Numeric Columns Clean Check")
        logger.info("="*70)
        
        numeric_columns = [
            'original_price_inr', 'discounted_price_inr', 'subtotal_inr',
            'final_amount_inr', 'delivery_charges', 'product_weight_kg', 'quantity'
        ]
        
        all_clean = True
        
        for col in numeric_columns:
            if col not in self.df.columns:
                logger.info(f"  ⊘ {col}: column not present")
                continue
            
            # Check dtype
            is_numeric = pd.api.types.is_numeric_dtype(self.df[col])
            
            # Check for any remaining commas in non-null values
            if is_numeric:
                has_comma = False
            else:
                has_comma = self.df[col].astype(str).str.contains(',').any()
            
            if is_numeric and not has_comma:
                logger.info(f"  ✓ {col}: dtype={self.df[col].dtype}, NO commas, safe for MySQL")
            else:
                logger.info(f"  ✗ {col}: dtype={self.df[col].dtype}, contains strings/commas - PROBLEM!")
                all_clean = False
        
        if all_clean:
            logger.info(f"\n✓ All numeric columns verified CLEAN for MySQL insertion")
        else:
            logger.warning(f"\n⚠ Some numeric columns may have issues - review carefully")

    def verify_rating_columns_clean(self) -> None:
        """
        VERIFICATION: Ensure no rating columns contain fraction-style strings.
        
        This is a SAFETY CHECK before saving to CSV.
        """
        logger.info("="*70)
        logger.info("VERIFICATION: Rating Columns Clean Check")
        logger.info("="*70)
        
        rating_columns = ['customer_rating', 'product_rating']
        
        all_clean = True
        
        for col in rating_columns:
            if col not in self.df.columns:
                logger.info(f"  ⊘ {col}: column not present")
                continue
            
            # Check dtype
            is_numeric = pd.api.types.is_numeric_dtype(self.df[col])
            
            # Check for any remaining fraction-style strings (e.g., '5/5')
            if is_numeric:
                has_fraction = False
            else:
                has_fraction = self.df[col].astype(str).str.contains('/').any()
            
            # Check for any remaining commas
            if is_numeric:
                has_comma = False
            else:
                has_comma = self.df[col].astype(str).str.contains(',').any()
            
            if is_numeric and not has_fraction and not has_comma:
                col_mean = self.df[col].mean()
                logger.info(f"  ✓ {col}: dtype={self.df[col].dtype}, NO fractions/commas")
                logger.info(f"    Range: [{self.df[col].min():.2f}, {self.df[col].max():.2f}], Mean: {col_mean:.2f}")
            else:
                if has_fraction:
                    logger.info(f"  ✗ {col}: contains fraction-style strings (e.g., '5/5') - PROBLEM!")
                if has_comma:
                    logger.info(f"  ✗ {col}: contains commas - PROBLEM!")
                all_clean = False
        
        if all_clean:
            logger.info(f"\n✓ All rating columns verified CLEAN for MySQL insertion\n")
        else:
            logger.warning(f"\n⚠ Some rating columns may have issues - review carefully\n")

    def run_full_pipeline(self) -> Tuple[pd.DataFrame, Dict]:
        """Execute complete data cleaning pipeline."""
        logger.info("\n" + "="*70)
        logger.info("AMAZON INDIA E-COMMERCE DATA CLEANING PIPELINE (V4.2)")
        logger.info("="*70 + "\n")
        
        # Load data
        self.load_data_chunked(chunksize=50000)
        logger.info("")
        
        # CRITICAL STEP 1: Normalize all numeric columns IMMEDIATELY after loading
        self.normalize_all_numeric_columns()
        
        # CRITICAL STEP 1B: Normalize all rating columns (fraction-style handling)
        self.normalize_all_rating_columns()
        
        # Cleaning operations
        self.clean_order_dates()
        
        self.standardize_cities()
        
        self.clean_delivery_charges()
        self.clean_festival_name()
        self.clean_customer_age_group()
        logger.info("")
        
        self.standardize_booleans()
        
        self.standardize_categories()
        
        self.clean_delivery_days()
        
        self.detect_duplicates()
        
        self.detect_price_outliers()
        
        self.standardize_payment_methods()
        
        # Remove duplicates
        if 'is_duplicate' in self.df.columns:
            duplicates_removed = self.df['is_duplicate'].sum()
            self.df = self.df[~self.df['is_duplicate']].drop(columns=['is_duplicate'])
            logger.info(f"✓ Removed {duplicates_removed:,} duplicate records\n")
        
        # Fill remaining ratings with default (should be none after normalization)
        if 'customer_rating' in self.df.columns:
            remaining_nulls = self.df['customer_rating'].isna().sum()
            if remaining_nulls > 0:
                self.df['customer_rating'].fillna(3.5, inplace=True)
        if 'product_rating' in self.df.columns:
            remaining_nulls = self.df['product_rating'].isna().sum()
            if remaining_nulls > 0:
                self.df['product_rating'].fillna(3.5, inplace=True)
        if 'delivery_days' in self.df.columns:
            self.df['delivery_days'].fillna(int(self.df['delivery_days'].median()), inplace=True)
        
        # CRITICAL: Verify numeric columns are clean before saving
        self.verify_numeric_columns_clean()
        
        # CRITICAL: Verify rating columns are clean before saving
        self.verify_rating_columns_clean()
        
        # Save cleaned data
        logger.info("="*70)
        logger.info("SAVING CLEANED DATA")
        logger.info("="*70)
        
        logger.info(f"Writing cleaned data to {self.output_path}...")
        self.df.to_csv(self.output_path, index=False)
        logger.info(f"✓ Cleaned data saved successfully\n")
        
        # Final validation summary
        logger.info("="*70)
        logger.info("DATA CLEANING VALIDATION SUMMARY")
        logger.info("="*70)
        
        logger.info(f"✓ Row preservation: {self.original_row_count:,} → {len(self.df):,} rows")
        logger.info(f"  Retention rate: {(len(self.df)/self.original_row_count)*100:.2f}%")
        
        logger.info(f"✓ Columns preserved: {len(self.original_cols)} → {len(self.df.columns)}")
        
        if 'customer_city' in self.df.columns:
            unique_cities = self.df['customer_city'].nunique()
            city_nulls = self.df['customer_city'].isna().sum()
            logger.info(f"✓ Cities: {unique_cities} unique, {city_nulls} nulls")
        
        logger.info(f"✓ Null handling:")
        if 'delivery_charges' in self.df.columns:
            logger.info(f"  - delivery_charges: {self.df['delivery_charges'].isna().sum()} nulls")
        if 'festival_name' in self.df.columns:
            logger.info(f"  - festival_name: {self.df['festival_name'].isna().sum()} nulls")
        if 'customer_age_group' in self.df.columns:
            logger.info(f"  - customer_age_group: {self.df['customer_age_group'].isna().sum()} nulls")
        
        logger.info(f"✓ Numeric columns (float64, MySQL-safe):")
        numeric_cols = ['original_price_inr', 'discounted_price_inr', 'final_amount_inr', 'delivery_charges']
        for col in numeric_cols:
            if col in self.df.columns:
                col_dtype = self.df[col].dtype
                col_nulls = self.df[col].isna().sum()
                logger.info(f"  - {col}: dtype={col_dtype}, nulls={col_nulls}")
        
        logger.info(f"✓ Rating columns (float64, fraction-style normalized):")
        rating_cols = ['customer_rating', 'product_rating']
        for col in rating_cols:
            if col in self.df.columns:
                col_dtype = self.df[col].dtype
                col_nulls = self.df[col].isna().sum()
                col_mean = self.df[col].mean()
                logger.info(f"  - {col}: dtype={col_dtype}, nulls={col_nulls}, mean={col_mean:.2f}")
        
        logger.info("\n" + "="*70)
        logger.info("✅ DATA CLEANING PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("CSV OUTPUT IS MYSQL-SAFE:")
        logger.info("  • No commas in numeric columns")
        logger.info("  • No fraction-style ratings (e.g., '5/5')")
        logger.info("  • All ratings normalized to float64")
        logger.info("  • Ready for direct MySQL insertion")
        logger.info("="*70 + "\n")
        
        return self.df, self.cleaning_report


def main(input_csv: str, output_csv: str, chunksize: int = 50000) -> pd.DataFrame:
    """Main entry point for data cleaning pipeline."""
    cleaner = DataCleaner(input_csv, output_csv)
    cleaned_df, report = cleaner.run_full_pipeline()
    return cleaned_df


if __name__ == "__main__":
    input_file = "data/amazon_india_complete_2015_2025.csv"
    output_file = "cleaned_data/transactions_cleaned.csv"
    
    cleaned_data = main(input_file, output_file, chunksize=50000)
    
    print("\n✅ Cleaning completed!")
    print(f"Output file: {output_file}")
    print(f"Total rows: {len(cleaned_data):,}")