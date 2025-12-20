"""
STANDARDIZATION UTILITIES MODULE
===============================
Reusable utility functions for data standardization and transformation.
Provides helper functions used across the data cleaning pipeline.

Author: Data Engineering Team
Version: 1.0
"""

import pandas as pd
import numpy as np
import re
from typing import List, Dict, Tuple, Union, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StandardizationUtils:
    """Utility functions for data standardization."""
    
    # ========== DATE UTILITIES ==========
    @staticmethod
    def standardize_date(date_str: str, target_format: str = '%Y-%m-%d') -> str:
        """
        Standardize date to target format.
        
        Args:
            date_str: Input date string
            target_format: Output format
            
        Returns:
            Standardized date string
        """
        if pd.isna(date_str):
            return None
        
        # List of common date formats
        formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y',
            '%d/%m/%y', '%d-%m-%y', '%Y/%m/%d', '%m-%d-%Y'
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(str(date_str).strip(), fmt)
                if 2015 <= parsed.year <= 2025:
                    return parsed.strftime(target_format)
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def add_time_features(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        """
        Add derived time features from date column.
        
        Args:
            df: DataFrame with date column
            date_col: Name of date column
            
        Returns:
            DataFrame with added time features
        """
        df[date_col] = pd.to_datetime(df[date_col])
        
        df['year'] = df[date_col].dt.year
        df['month'] = df[date_col].dt.month
        df['quarter'] = df[date_col].dt.quarter
        df['week'] = df[date_col].dt.isocalendar().week
        df['day_of_week'] = df[date_col].dt.day_name()
        df['is_weekend'] = df[date_col].dt.dayofweek >= 5
        
        return df
    
    # ========== PRICE UTILITIES ==========
    @staticmethod
    def extract_numeric_price(price_str: str) -> float:
        """
        Extract numeric value from price string.
        Handles currency symbols, commas, and various formats.
        
        Args:
            price_str: Price string (e.g., '₹1,25,000', '$1,250')
            
        Returns:
            Numeric price or NaN
        """
        if pd.isna(price_str):
            return np.nan
        
        price_str = str(price_str).strip()
        
        # Remove currency symbols
        price_str = re.sub(r'[₹$€£¥]', '', price_str)
        
        # Remove commas
        price_str = price_str.replace(',', '')
        
        # Extract first numeric value
        match = re.search(r'\d+\.?\d*', price_str)
        if match:
            try:
                return float(match.group())
            except:
                return np.nan
        
        return np.nan
    
    @staticmethod
    def calculate_price_percentiles(series: pd.Series, 
                                    exclude_zeros: bool = True) -> Dict[str, float]:
        """
        Calculate price percentiles for outlier detection.
        
        Args:
            series: Price series
            exclude_zeros: Whether to exclude zero prices
            
        Returns:
            Dictionary with percentiles
        """
        if exclude_zeros:
            series = series[series > 0]
        
        return {
            'p10': series.quantile(0.10),
            'p25': series.quantile(0.25),
            'p50': series.quantile(0.50),  # Median
            'p75': series.quantile(0.75),
            'p90': series.quantile(0.90),
            'iqr': series.quantile(0.75) - series.quantile(0.25)
        }
    
    @staticmethod
    def detect_price_outliers(series: pd.Series, method: str = 'iqr',
                             threshold: float = 1.5) -> pd.Series:
        """
        Detect price outliers using specified method.
        
        Args:
            series: Price series
            method: 'iqr' or 'zscore'
            threshold: Detection threshold
            
        Returns:
            Boolean series indicating outliers
        """
        if method == 'iqr':
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - threshold * IQR
            upper = Q3 + threshold * IQR
            return (series < lower) | (series > upper)
        
        elif method == 'zscore':
            from scipy import stats
            z_scores = np.abs(stats.zscore(series.dropna()))
            return z_scores > threshold
        
        return pd.Series([False] * len(series))
    
    # ========== CATEGORY UTILITIES ==========
    @staticmethod
    def fuzzy_match_category(category: str, valid_categories: List[str],
                            threshold: float = 0.8) -> str:
        """
        Fuzzy match category name to valid category list.
        
        Args:
            category: Input category name
            valid_categories: List of valid categories
            threshold: Matching threshold (0-1)
            
        Returns:
            Matched category name
        """
        from difflib import SequenceMatcher
        
        if category in valid_categories:
            return category
        
        scores = [
            SequenceMatcher(None, category.lower(), vc.lower()).ratio()
            for vc in valid_categories
        ]
        
        max_score = max(scores)
        if max_score >= threshold:
            return valid_categories[scores.index(max_score)]
        
        return 'Others'
    
    @staticmethod
    def create_category_hierarchy(df: pd.DataFrame,
                                 category_col: str,
                                 subcategory_col: str = None) -> Dict:
        """
        Create category hierarchy mapping.
        
        Args:
            df: DataFrame
            category_col: Main category column
            subcategory_col: Sub-category column (optional)
            
        Returns:
            Hierarchy dictionary
        """
        hierarchy = {}
        
        if subcategory_col:
            grouped = df.groupby(category_col)[subcategory_col].unique()
            hierarchy = {cat: list(subs) for cat, subs in grouped.items()}
        else:
            hierarchy = {cat: [] for cat in df[category_col].unique()}
        
        return hierarchy
    
    # ========== TEXT UTILITIES ==========
    @staticmethod
    def normalize_text(text: str, lowercase: bool = True,
                       remove_special: bool = False) -> str:
        """
        Normalize text by removing extra spaces and special characters.
        
        Args:
            text: Input text
            lowercase: Convert to lowercase
            remove_special: Remove special characters
            
        Returns:
            Normalized text
        """
        if pd.isna(text):
            return np.nan
        
        text = str(text).strip()
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        if remove_special:
            text = re.sub(r'[^\w\s]', '', text)
        
        if lowercase:
            text = text.lower()
        
        return text
    
    @staticmethod
    def extract_numeric(text: str, multiple: bool = False) -> Union[float, List[float]]:
        """
        Extract numeric values from text.
        
        Args:
            text: Input text
            multiple: Return all numbers or just first
            
        Returns:
            Numeric value(s) or NaN
        """
        if pd.isna(text):
            return np.nan
        
        numbers = re.findall(r'\d+\.?\d*', str(text))
        
        if not numbers:
            return np.nan if not multiple else []
        
        if multiple:
            return [float(n) for n in numbers]
        else:
            return float(numbers[0])
    
    # ========== BOOLEAN UTILITIES ==========
    @staticmethod
    def to_boolean(value, true_values: List = None,
                   false_values: List = None,
                   default: bool = False) -> bool:
        """
        Convert value to boolean.
        
        Args:
            value: Input value
            true_values: List of truthy values
            false_values: List of falsy values
            default: Default for unknown values
            
        Returns:
            Boolean value
        """
        if true_values is None:
            true_values = ['true', 'yes', '1', 'y', 'on', 'active']
        if false_values is None:
            false_values = ['false', 'no', '0', 'n', 'off', 'inactive']
        
        if pd.isna(value):
            return default
        
        val_lower = str(value).strip().lower()
        
        if val_lower in true_values:
            return True
        elif val_lower in false_values:
            return False
        else:
            return default
    
    # ========== CITY/LOCATION UTILITIES ==========
    @staticmethod
    def standardize_location(location: str, mapping: Dict = None) -> str:
        """
        Standardize location name using mapping.
        
        Args:
            location: Input location
            mapping: Mapping dictionary
            
        Returns:
            Standardized location
        """
        if mapping is None:
            mapping = {}
        
        if pd.isna(location):
            return np.nan
        
        location_lower = str(location).strip().lower()
        location_clean = re.sub(r'[^\w\s]', '', location_lower)
        
        return mapping.get(location_clean, location.title())
    
    @staticmethod
    def add_geo_tier(city: str, tier_mapping: Dict = None) -> str:
        """
        Assign geographic tier (Metro/Tier1/Tier2/Tier3/Rural).
        
        Args:
            city: City name
            tier_mapping: City to tier mapping
            
        Returns:
            Geographic tier
        """
        if tier_mapping is None:
            tier_mapping = {
                'mumbai': 'Metro',
                'delhi': 'Metro',
                'bengaluru': 'Metro',
                'hyderabad': 'Metro',
                'pune': 'Tier1',
                'ahmedabad': 'Tier1',
                'jaipur': 'Tier1',
                'lucknow': 'Tier2',
                'surat': 'Tier2',
                'indore': 'Tier2',
            }
        
        city_lower = str(city).strip().lower()
        return tier_mapping.get(city_lower, 'Tier3')
    
    # ========== CUSTOMER UTILITIES ==========
    @staticmethod
    def segment_by_age(age: int) -> str:
        """
        Segment customer by age group.
        
        Args:
            age: Customer age
            
        Returns:
            Age group label
        """
        if pd.isna(age) or age < 0:
            return 'Unknown'
        
        if age < 18:
            return 'Below 18'
        elif age < 25:
            return '18-24'
        elif age < 35:
            return '25-34'
        elif age < 45:
            return '35-44'
        elif age < 55:
            return '45-54'
        else:
            return '55+'
    
    @staticmethod
    def segment_by_value(value: float, breaks: List[float] = None,
                        labels: List[str] = None) -> str:
        """
        Segment customer by spending value.
        
        Args:
            value: Spending amount
            breaks: Value thresholds
            labels: Segment labels
            
        Returns:
            Segment label
        """
        if breaks is None:
            breaks = [0, 5000, 15000, 50000, float('inf')]
        if labels is None:
            labels = ['Low', 'Medium', 'High', 'Premium']
        
        for i, break_val in enumerate(breaks[:-1]):
            if break_val <= value < breaks[i + 1]:
                return labels[i]
        
        return labels[-1]
    
    # ========== VALIDATION UTILITIES ==========
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, str(email)))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number (Indian format)."""
        pattern = r'^[6-9]\d{9}$'
        phone_digits = re.sub(r'\D', '', str(phone))
        return bool(re.match(pattern, phone_digits))
    
    @staticmethod
    def get_data_quality_score(df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate data quality metrics.
        
        Args:
            df: DataFrame to assess
            
        Returns:
            Quality metrics dictionary
        """
        total_cells = df.shape[0] * df.shape[1]
        null_cells = df.isnull().sum().sum()
        
        completeness = ((total_cells - null_cells) / total_cells) * 100
        
        duplicates = df.duplicated().sum()
        uniqueness = ((len(df) - duplicates) / len(df)) * 100 if len(df) > 0 else 0
        
        return {
            'completeness_percent': round(completeness, 2),
            'uniqueness_percent': round(uniqueness, 2),
            'null_cells': null_cells,
            'duplicate_rows': duplicates,
            'total_rows': len(df),
            'total_columns': len(df.columns)
        }


class BatchProcessor:
    """Batch processing utility for large datasets."""
    
    @staticmethod
    def process_in_batches(df: pd.DataFrame, func: Callable,
                          batch_size: int = 10000, **kwargs) -> pd.DataFrame:
        """
        Process DataFrame in batches to manage memory.
        
        Args:
            df: Input DataFrame
            func: Processing function
            batch_size: Batch size
            **kwargs: Additional arguments for func
            
        Returns:
            Processed DataFrame
        """
        result = []
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size].copy()
            processed = func(batch, **kwargs)
            result.append(processed)
        
        return pd.concat(result, ignore_index=True)


if __name__ == "__main__":
    # Example usage
    utils = StandardizationUtils()
    
    # Test date standardization
    print("Date standardization:", utils.standardize_date("25/12/2020"))
    
    # Test price extraction
    print("Price extraction:", utils.extract_numeric_price("₹1,25,000"))
    
    # Test age segmentation
    print("Age segment:", utils.segment_by_age(28))
    
    # Test value segmentation
    print("Value segment:", utils.segment_by_value(35000))
