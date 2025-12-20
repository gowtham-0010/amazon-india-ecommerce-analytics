"""
EDA FUNCTIONS MODULE
==================
Reusable functions for Exploratory Data Analysis visualizations.
Includes 20 comprehensive visualization functions for business intelligence.

Author: Data Engineering Team
Version: 1.0
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)


class EDAFunctions:
    """Collection of EDA visualization functions."""
    
    # ============= CHALLENGE 1: REVENUE TRENDS =============
    @staticmethod
    def revenue_trends(df: pd.DataFrame, date_col: str = 'order_date',
                      revenue_col: str = 'final_amount_inr',
                      freq: str = 'M') -> go.Figure:
        """
        Create revenue trend analysis with growth rates.
        
        Args:
            df: Input DataFrame
            date_col: Date column name
            revenue_col: Revenue column name
            freq: Frequency ('D', 'W', 'M', 'Q', 'Y')
            
        Returns:
            Plotly figure
        """
        df[date_col] = pd.to_datetime(df[date_col])
        trend = df.set_index(date_col)[revenue_col].resample(freq).sum()
        
        # Calculate growth rate
        growth_rate = trend.pct_change() * 100
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(
            go.Scatter(x=trend.index, y=trend.values, name='Revenue',
                      mode='lines+markers', line=dict(color='#2E86AB', width=3)),
            secondary_y=False
        )
        
        fig.add_trace(
            go.Scatter(x=growth_rate.index, y=growth_rate.values, name='Growth %',
                      mode='lines', line=dict(color='#A23B72', width=2, dash='dash')),
            secondary_y=True
        )
        
        fig.update_layout(
            title='Revenue Trend Analysis (2015-2025)',
            xaxis_title='Date',
            yaxis_title='Revenue (₹)',
            hovermode='x unified',
            height=500
        )
        
        return fig
    
    # ============= CHALLENGE 2: SEASONAL HEATMAPS =============
    @staticmethod
    def seasonal_heatmap(df: pd.DataFrame, date_col: str = 'order_date',
                        revenue_col: str = 'final_amount_inr') -> go.Figure:
        """
        Create monthly sales heatmap by year and month.
        
        Args:
            df: Input DataFrame
            date_col: Date column
            revenue_col: Revenue column
            
        Returns:
            Plotly heatmap figure
        """
        df[date_col] = pd.to_datetime(df[date_col])
        df['year'] = df[date_col].dt.year
        df['month'] = df[date_col].dt.month
        
        pivot_data = df.pivot_table(
            values=revenue_col,
            index='month',
            columns='year',
            aggfunc='sum'
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:len(pivot_data)],
            colorscale='YlOrRd'
        ))
        
        fig.update_layout(
            title='Monthly Sales Heatmap (Seasonality Pattern)',
            xaxis_title='Year',
            yaxis_title='Month',
            height=500
        )
        
        return fig
    
    # ============= CHALLENGE 3: RFM SEGMENTATION =============
    @staticmethod
    def rfm_segmentation(df: pd.DataFrame, customer_col: str = 'customer_id',
                        date_col: str = 'order_date',
                        revenue_col: str = 'final_amount_inr') -> Tuple[pd.DataFrame, go.Figure]:
        """
        Perform RFM (Recency, Frequency, Monetary) analysis.
        
        Args:
            df: Input DataFrame
            customer_col: Customer ID column
            date_col: Date column
            revenue_col: Revenue column
            
        Returns:
            RFM DataFrame and scatter plot figure
        """
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Calculate RFM
        now = df[date_col].max()
        rfm = df.groupby(customer_col).agg({
            date_col: lambda x: (now - x.max()).days,  # Recency
            customer_col: 'count',  # Frequency
            revenue_col: 'sum'  # Monetary
        })
        
        rfm.columns = ['Recency', 'Frequency', 'Monetary']
        
        # Create segments
        rfm['R_Score'] = pd.qcut(rfm['Recency'], 4, labels=[4, 3, 2, 1], duplicates='drop')
        rfm['F_Score'] = pd.qcut(rfm['Frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
        rfm['M_Score'] = pd.qcut(rfm['Monetary'], 4, labels=[1, 2, 3, 4], duplicates='drop')
        rfm['RFM_Score'] = rfm['R_Score'].astype(int).astype(str) + \
                          rfm['F_Score'].astype(int).astype(str) + \
                          rfm['M_Score'].astype(int).astype(str)
        
        # Visualization
        fig = px.scatter(rfm.reset_index(), x='Frequency', y='Monetary',
                        size='Recency', color='RFM_Score',
                        title='RFM Customer Segmentation',
                        labels={'Frequency': 'Purchase Frequency', 'Monetary': 'Total Spending (₹)'})
        fig.update_layout(height=500)
        
        return rfm, fig
    
    # ============= CHALLENGE 4: PAYMENT METHOD EVOLUTION =============
    @staticmethod
    def payment_evolution(df: pd.DataFrame, date_col: str = 'order_date',
                         payment_col: str = 'payment_method') -> go.Figure:
        """
        Visualize payment method evolution over time.
        
        Args:
            df: Input DataFrame
            date_col: Date column
            payment_col: Payment method column
            
        Returns:
            Stacked area chart figure
        """
        df[date_col] = pd.to_datetime(df[date_col])
        df['year'] = df[date_col].dt.year
        
        payment_trend = df.groupby(['year', payment_col]).size().unstack(fill_value=0)
        payment_pct = payment_trend.div(payment_trend.sum(axis=1), axis=0) * 100
        
        fig = go.Figure()
        
        for method in payment_pct.columns:
            fig.add_trace(go.Scatter(
                x=payment_pct.index,
                y=payment_pct[method],
                mode='lines',
                name=method,
                stackgroup='one',
                fillcolor='rgba(135, 206, 250, 0.5)'
            ))
        
        fig.update_layout(
            title='Payment Method Evolution (2015-2025)',
            xaxis_title='Year',
            yaxis_title='Market Share (%)',
            hovermode='x unified',
            height=500
        )
        
        return fig
    
    # ============= CHALLENGE 5: CATEGORY PERFORMANCE =============
    @staticmethod
    def category_performance(df: pd.DataFrame, category_col: str = 'category',
                            revenue_col: str = 'final_amount_inr',
                            units_col: str = None) -> Tuple[go.Figure, go.Figure]:
        """
        Create category performance visualizations.
        
        Args:
            df: Input DataFrame
            category_col: Category column
            revenue_col: Revenue column
            units_col: Units column (optional)
            
        Returns:
            Two Plotly figures (treemap and bar chart)
        """
        category_stats = df.groupby(category_col).agg({
            revenue_col: 'sum',
            'transaction_id': 'count'
        }).sort_values(revenue_col, ascending=False)
        
        # Treemap
        fig1 = px.treemap(
            values=category_stats[revenue_col],
            labels=category_stats.index,
            title='Category Performance - Revenue Share',
            color=category_stats[revenue_col],
            color_continuous_scale='RdYlGn'
        )
        
        # Bar chart
        fig2 = px.bar(
            category_stats.reset_index(),
            x='category',
            y=revenue_col,
            title='Revenue by Category',
            color='transaction_id',
            text='transaction_id'
        )
        
        return fig1, fig2
    
    # ============= CHALLENGE 6: PRIME VS NON-PRIME =============
    @staticmethod
    def prime_analysis(df: pd.DataFrame, prime_col: str = 'is_prime_member',
                      revenue_col: str = 'final_amount_inr') -> go.Figure:
        """
        Compare Prime vs Non-Prime customer behavior.
        
        Args:
            df: Input DataFrame
            prime_col: Prime member column
            revenue_col: Revenue column
            
        Returns:
            Comparison figure
        """
        prime_stats = df.groupby(prime_col).agg({
            'transaction_id': 'count',
            revenue_col: ['sum', 'mean'],
            'customer_rating': 'mean',
            'delivery_days': 'mean'
        }).round(2)
        
        metrics = pd.DataFrame({
            'Prime': [
                (df[df[prime_col] == True]['transaction_id'].count()),
                (df[df[prime_col] == True][revenue_col].mean()),
                (df[df[prime_col] == True]['delivery_days'].mean())
            ],
            'Non-Prime': [
                (df[df[prime_col] == False]['transaction_id'].count()),
                (df[df[prime_col] == False][revenue_col].mean()),
                (df[df[prime_col] == False]['delivery_days'].mean())
            ]
        }, index=['Orders', 'Avg Order Value', 'Avg Delivery Days'])
        
        fig = go.Figure(data=[
            go.Bar(name='Prime', x=metrics.index, y=metrics['Prime']),
            go.Bar(name='Non-Prime', x=metrics.index, y=metrics['Non-Prime'])
        ])
        
        fig.update_layout(
            title='Prime vs Non-Prime Member Comparison',
            barmode='group',
            height=500
        )
        
        return fig
    
    # ============= CHALLENGE 7: GEOGRAPHIC ANALYSIS =============
    @staticmethod
    def geographic_analysis(df: pd.DataFrame, city_col: str = 'customer_city',
                           revenue_col: str = 'final_amount_inr') -> go.Figure:
        """
        Create geographic sales distribution.
        
        Args:
            df: Input DataFrame
            city_col: City column
            revenue_col: Revenue column
            
        Returns:
            Bar chart figure
        """
        city_revenue = df.groupby(city_col)[revenue_col].agg(['sum', 'count']).sort_values('sum', ascending=False).head(15)
        
        fig = px.bar(
            city_revenue.reset_index().rename(columns={'sum': 'Revenue', 'count': 'Transactions'}),
            x=city_col,
            y='Revenue',
            color='Transactions',
            title='Top 15 Cities by Revenue',
            text='Revenue'
        )
        
        fig.update_layout(height=500, xaxis_tickangle=-45)
        
        return fig
    
    # ============= CHALLENGE 8: FESTIVAL SALES IMPACT =============
    @staticmethod
    def festival_impact(df: pd.DataFrame, festival_col: str = 'is_festival_sale',
                       date_col: str = 'order_date',
                       revenue_col: str = 'final_amount_inr') -> go.Figure:
        """
        Analyze festival sales impact.
        
        Args:
            df: Input DataFrame
            festival_col: Festival flag column
            date_col: Date column
            revenue_col: Revenue column
            
        Returns:
            Figure showing festival impact
        """
        df[date_col] = pd.to_datetime(df[date_col])
        df['month'] = df[date_col].dt.month
        
        festival_stats = df.groupby(['month', festival_col])[revenue_col].mean().unstack()
        
        fig = go.Figure(data=[
            go.Bar(name='Non-Festival', x=festival_stats.index, y=festival_stats[False]),
            go.Bar(name='Festival', x=festival_stats.index, y=festival_stats[True])
        ])
        
        fig.update_layout(
            title='Festival vs Non-Festival Sales by Month',
            xaxis_title='Month',
            yaxis_title='Average Order Value (₹)',
            barmode='group',
            height=500
        )
        
        return fig
    
    # ============= CHALLENGE 9: AGE GROUP ANALYSIS =============
    @staticmethod
    def age_group_analysis(df: pd.DataFrame, age_col: str = 'age_group',
                          revenue_col: str = 'final_amount_inr',
                          category_col: str = 'category') -> go.Figure:
        """
        Analyze age group behavior and preferences.
        
        Args:
            df: Input DataFrame
            age_col: Age group column
            revenue_col: Revenue column
            category_col: Category column
            
        Returns:
            Figure showing age group analysis
        """
        age_stats = df.groupby(age_col).agg({
            revenue_col: ['sum', 'mean', 'count']
        }).round(2)
        
        fig = px.bar(
            age_stats.reset_index(),
            x=age_col,
            y=('final_amount_inr', 'sum'),
            color=('final_amount_inr', 'count'),
            title='Revenue by Age Group',
            labels={'final_amount_inr': 'Revenue (₹)'}
        )
        
        fig.update_layout(height=500)
        
        return fig
    
    # ============= CHALLENGE 10: PRICE VS DEMAND =============
    @staticmethod
    def price_demand_analysis(df: pd.DataFrame, price_col: str = 'original_price_inr',
                             category_col: str = 'category') -> go.Figure:
        """
        Analyze correlation between price and demand.
        
        Args:
            df: Input DataFrame
            price_col: Price column
            category_col: Category column
            
        Returns:
            Scatter plot figure
        """
        price_demand = df.groupby(category_col).agg({
            price_col: 'mean',
            'transaction_id': 'count'
        }).reset_index()
        
        fig = px.scatter(
            price_demand,
            x=price_col,
            y='transaction_id',
            size='transaction_id',
            color='category',
            title='Price vs Demand by Category',
            labels={'transaction_id': 'Number of Orders', 'original_price_inr': 'Avg Price (₹)'},
            text='category'
        )
        
        fig.update_layout(height=500)
        
        return fig
    
    # ============= CHALLENGE 11: DELIVERY PERFORMANCE =============
    @staticmethod
    def delivery_performance(df: pd.DataFrame, delivery_col: str = 'delivery_days',
                            city_col: str = 'customer_city') -> go.Figure:
        """
        Analyze delivery performance metrics.
        
        Args:
            df: Input DataFrame
            delivery_col: Delivery days column
            city_col: City column
            
        Returns:
            Figure showing delivery metrics
        """
        delivery_stats = df.groupby(city_col)[delivery_col].agg(['mean', 'std', 'count']).sort_values('mean').head(15)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=delivery_stats.index,
            y=delivery_stats['mean'],
            error_y=dict(type='data', array=delivery_stats['std']),
            name='Avg Delivery Days'
        ))
        
        fig.update_layout(
            title='Delivery Performance by City (Top 15)',
            xaxis_title='City',
            yaxis_title='Days',
            height=500,
            xaxis_tickangle=-45
        )
        
        return fig
    
    # ============= CHALLENGE 12: RETURN ANALYSIS =============
    @staticmethod
    def return_analysis(df: pd.DataFrame, return_col: str = 'return_status',
                       category_col: str = 'category',
                       price_col: str = 'final_amount_inr') -> Tuple[go.Figure, pd.DataFrame]:
        """
        Analyze return patterns and rates.
        
        Args:
            df: Input DataFrame
            return_col: Return status column
            category_col: Category column
            price_col: Price column
            
        Returns:
            Figure and return statistics
        """
        return_stats = df.groupby(category_col)[return_col].apply(
            lambda x: (x == 'Returned').sum() / len(x) * 100
        ).sort_values(ascending=False)
        
        fig = px.bar(
            x=return_stats.index,
            y=return_stats.values,
            title='Return Rate by Category (%)',
            labels={'y': 'Return Rate (%)', 'x': 'Category'},
            text=return_stats.values.round(2)
        )
        
        fig.update_layout(height=500)
        
        return fig, return_stats
    
    # ============= CHALLENGE 13: BRAND ANALYSIS =============
    @staticmethod
    def brand_analysis(df: pd.DataFrame, brand_col: str = 'brand',
                      revenue_col: str = 'final_amount_inr') -> go.Figure:
        """
        Analyze brand performance and market share.
        
        Args:
            df: Input DataFrame
            brand_col: Brand column
            revenue_col: Revenue column
            
        Returns:
            Figure showing brand analysis
        """
        brand_stats = df.groupby(brand_col)[revenue_col].agg(['sum', 'count']).sort_values('sum', ascending=False).head(15)
        
        fig = px.bar(
            brand_stats.reset_index().rename(columns={'sum': 'Revenue', 'count': 'Orders'}),
            x='brand',
            y='Revenue',
            color='Orders',
            title='Top 15 Brands by Revenue',
            text='Revenue'
        )
        
        fig.update_layout(height=500, xaxis_tickangle=-45)
        
        return fig
    
    # ============= CHALLENGE 14: CUSTOMER LIFETIME VALUE =============
    @staticmethod
    def clv_analysis(df: pd.DataFrame, customer_col: str = 'customer_id',
                    revenue_col: str = 'final_amount_inr') -> go.Figure:
        """
        Analyze customer lifetime value distribution.
        
        Args:
            df: Input DataFrame
            customer_col: Customer ID column
            revenue_col: Revenue column
            
        Returns:
            Figure showing CLV distribution
        """
        clv = df.groupby(customer_col)[revenue_col].sum().reset_index()
        clv.columns = ['customer_id', 'CLV']
        
        fig = px.histogram(
            clv,
            x='CLV',
            title='Customer Lifetime Value Distribution',
            nbins=50,
            labels={'CLV': 'Lifetime Value (₹)'}
        )
        
        fig.update_layout(height=500)
        
        return fig
    
    # ============= CHALLENGE 15: DISCOUNT EFFECTIVENESS =============
    @staticmethod
    def discount_effectiveness(df: pd.DataFrame, discount_col: str = 'discount_percent',
                              revenue_col: str = 'final_amount_inr') -> go.Figure:
        """
        Analyze discount effectiveness.
        
        Args:
            df: Input DataFrame
            discount_col: Discount percentage column
            revenue_col: Revenue column
            
        Returns:
            Figure showing discount impact
        """
        df['discount_range'] = pd.cut(df[discount_col], bins=[0, 10, 20, 30, 40, 50, 100])
        
        discount_stats = df.groupby('discount_range', observed=True).agg({
            'transaction_id': 'count',
            revenue_col: 'mean'
        }).reset_index()
        
        fig = px.bar(
            discount_stats,
            x='discount_range',
            y='transaction_id',
            color=revenue_col,
            title='Sales Volume by Discount Range',
            labels={'transaction_id': 'Orders', revenue_col: 'Avg Value (₹)'}
        )
        
        fig.update_layout(height=500)
        
        return fig
    
    # ============= REMAINING CHALLENGES: SUMMARY FUNCTIONS =============
    @staticmethod
    def rating_impact_analysis(df: pd.DataFrame, rating_col: str = 'product_rating',
                              revenue_col: str = 'final_amount_inr') -> go.Figure:
        """Challenge 16: Analyze product ratings and sales impact."""
        rating_stats = df.groupby(pd.cut(df[rating_col], bins=5))[revenue_col].agg(['count', 'mean'])
        
        fig = px.bar(
            x=rating_stats.index.astype(str),
            y=rating_stats['count'],
            color=rating_stats['mean'],
            title='Sales by Product Rating',
            labels={'y': 'Number of Sales', 'color': 'Avg Revenue (₹)'}
        )
        
        return fig
    
    @staticmethod
    def product_lifecycle(df: pd.DataFrame, product_col: str = 'product_name',
                         date_col: str = 'order_date',
                         revenue_col: str = 'final_amount_inr') -> pd.DataFrame:
        """Challenge 18: Analyze product lifecycle patterns."""
        df[date_col] = pd.to_datetime(df[date_col])
        
        lifecycle = df.groupby([product_col, df[date_col].dt.year]).agg({
            revenue_col: 'sum',
            'transaction_id': 'count'
        }).reset_index()
        
        return lifecycle
    
    @staticmethod
    def get_data_quality_dashboard(df: pd.DataFrame) -> Dict:
        """
        Generate data quality summary for dashboard.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Dictionary with quality metrics
        """
        return {
            'total_records': len(df),
            'total_columns': len(df.columns),
            'missing_values': df.isnull().sum().to_dict(),
            'duplicates': df.duplicated().sum(),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024**2
        }


if __name__ == "__main__":
    print("EDA Functions module loaded successfully")
