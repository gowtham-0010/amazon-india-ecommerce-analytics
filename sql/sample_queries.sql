-- =====================================================
-- SAMPLE SQL QUERIES FOR DASHBOARD
-- =====================================================
-- Production-ready queries for analytics dashboards

USE amazon_india_analytics;

-- =====================================================
-- 1. EXECUTIVE DASHBOARD QUERIES
-- =====================================================

-- Query 1.1: Key Performance Indicators
SELECT 
    DATE_FORMAT(order_date, '%Y-%m') as month_year,
    SUM(final_amount_inr) as total_revenue,
    COUNT(DISTINCT transaction_id) as order_count,
    COUNT(DISTINCT customer_id) as unique_customers,
    ROUND(AVG(final_amount_inr), 2) as avg_order_value,
    ROUND(AVG(customer_rating), 2) as avg_rating,
    ROUND(SUM(CASE WHEN return_status = 'Returned' THEN 1 ELSE 0 END) / 
        COUNT(*) * 100, 2) as return_rate_percent
FROM transactions
WHERE order_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY month_year DESC;

-- Query 1.2: Year-over-Year Comparison
SELECT 
    YEAR(order_date) as year,
    MONTH(order_date) as month,
    SUM(final_amount_inr) as monthly_revenue,
    COUNT(DISTINCT transaction_id) as order_count
FROM transactions
WHERE order_date >= DATE_SUB(NOW(), INTERVAL 2 YEAR)
GROUP BY YEAR(order_date), MONTH(order_date)
ORDER BY year DESC, month DESC;

-- Query 1.3: Growth Rate Analysis
WITH monthly_revenue AS (
    SELECT 
        DATE_FORMAT(order_date, '%Y-%m') as month_year,
        SUM(final_amount_inr) as revenue
    FROM transactions
    GROUP BY DATE_FORMAT(order_date, '%Y-%m')
)
SELECT 
    month_year,
    revenue,
    LAG(revenue) OVER (ORDER BY month_year) as prev_month_revenue,
    ROUND(((revenue - LAG(revenue) OVER (ORDER BY month_year)) / 
        LAG(revenue) OVER (ORDER BY month_year) * 100), 2) as growth_percent
FROM monthly_revenue
ORDER BY month_year DESC;

-- =====================================================
-- 2. REVENUE ANALYTICS QUERIES
-- =====================================================

-- Query 2.1: Revenue by Category
SELECT 
    p.category,
    COUNT(t.transaction_id) as order_count,
    SUM(t.final_amount_inr) as total_revenue,
    ROUND(AVG(t.final_amount_inr), 2) as avg_order_value,
    ROUND(SUM(t.discount_percent * t.final_amount_inr / 100), 2) as total_discount,
    ROUND(AVG(t.product_rating), 2) as avg_rating,
    ROUND(SUM(CASE WHEN t.return_status = 'Returned' THEN 1 ELSE 0 END) / 
        COUNT(*) * 100, 2) as return_rate_percent
FROM transactions t
LEFT JOIN products p ON t.product_id = p.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;

-- Query 2.2: Seasonal Revenue Pattern
SELECT 
    MONTH(order_date) as month,
    MONTHNAME(order_date) as month_name,
    YEAR(order_date) as year,
    SUM(final_amount_inr) as revenue,
    COUNT(DISTINCT transaction_id) as orders,
    ROUND(AVG(final_amount_inr), 2) as avg_order_value
FROM transactions
GROUP BY YEAR(order_date), MONTH(order_date)
ORDER BY year DESC, month ASC;

-- Query 2.3: Top Products by Revenue
SELECT 
    p.product_name,
    p.category,
    p.brand,
    COUNT(t.transaction_id) as order_count,
    SUM(t.final_amount_inr) as total_revenue,
    ROUND(AVG(t.final_amount_inr), 2) as avg_price,
    ROUND(AVG(t.product_rating), 2) as avg_rating
FROM transactions t
LEFT JOIN products p ON t.product_id = p.product_id
GROUP BY t.product_id
ORDER BY total_revenue DESC
LIMIT 50;

-- Query 2.4: Discount Effectiveness
SELECT 
    CASE 
        WHEN discount_percent = 0 THEN 'No Discount'
        WHEN discount_percent <= 10 THEN '0-10%'
        WHEN discount_percent <= 25 THEN '10-25%'
        WHEN discount_percent <= 40 THEN '25-40%'
        ELSE '40%+'
    END as discount_range,
    COUNT(*) as order_count,
    SUM(final_amount_inr) as total_revenue,
    ROUND(AVG(final_amount_inr), 2) as avg_order_value,
    ROUND(AVG(discount_percent), 2) as avg_discount
FROM transactions
GROUP BY discount_range
ORDER BY FIELD(discount_range, 'No Discount', '0-10%', '10-25%', '25-40%', '40%+');

-- =====================================================
-- 3. CUSTOMER ANALYTICS QUERIES
-- =====================================================

-- Query 3.1: Customer Segmentation (RFM Analysis)
SELECT 
    c.customer_id,
    c.customer_name,
    COUNT(t.transaction_id) as purchase_frequency,
    ROUND(SUM(t.final_amount_inr), 2) as lifetime_value,
    DATEDIFF(NOW(), MAX(t.order_date)) as recency_days,
    CASE 
        WHEN DATEDIFF(NOW(), MAX(t.order_date)) <= 30 AND COUNT(t.transaction_id) >= 5 
            THEN 'Champion'
        WHEN COUNT(t.transaction_id) >= 10 THEN 'Loyal'
        WHEN DATEDIFF(NOW(), MAX(t.order_date)) > 90 AND COUNT(t.transaction_id) >= 3 
            THEN 'At-Risk'
        WHEN DATEDIFF(NOW(), MAX(t.order_date)) <= 30 THEN 'New'
        ELSE 'Dormant'
    END as customer_segment
FROM customers c
LEFT JOIN transactions t ON c.customer_id = t.customer_id
GROUP BY c.customer_id
ORDER BY lifetime_value DESC;

-- Query 3.2: Prime vs Non-Prime Comparison
SELECT 
    is_prime_member,
    COUNT(DISTINCT customer_id) as customer_count,
    COUNT(DISTINCT transaction_id) as order_count,
    ROUND(SUM(final_amount_inr), 2) as total_revenue,
    ROUND(AVG(final_amount_inr), 2) as avg_order_value,
    ROUND(AVG(delivery_days), 2) as avg_delivery_days,
    ROUND(AVG(customer_rating), 2) as avg_satisfaction,
    ROUND(AVG(CASE WHEN return_status = 'Returned' THEN 1 ELSE 0 END) * 100, 2) as return_rate_percent
FROM transactions
GROUP BY is_prime_member;

-- Query 3.3: Geographic Distribution
SELECT 
    customer_city,
    COUNT(DISTINCT customer_id) as unique_customers,
    COUNT(DISTINCT transaction_id) as order_count,
    ROUND(SUM(final_amount_inr), 2) as total_revenue,
    ROUND(AVG(final_amount_inr), 2) as avg_order_value,
    ROUND(AVG(delivery_days), 2) as avg_delivery_days
FROM transactions
GROUP BY customer_city
ORDER BY total_revenue DESC
LIMIT 30;

-- Query 3.4: Customer Retention & Churn
SELECT 
    cohort_year,
    COUNT(DISTINCT customer_id) as cohort_size,
    SUM(CASE WHEN year_1_purchase = 1 THEN 1 ELSE 0 END) as retained_y1,
    SUM(CASE WHEN year_2_purchase = 1 THEN 1 ELSE 0 END) as retained_y2,
    ROUND(SUM(CASE WHEN year_1_purchase = 1 THEN 1 ELSE 0 END) / 
        COUNT(DISTINCT customer_id) * 100, 2) as retention_rate_y1_percent
FROM (
    SELECT 
        YEAR(MIN(order_date)) as cohort_year,
        customer_id,
        MAX(CASE WHEN YEAR(order_date) = YEAR(MIN(order_date)) + 1 THEN 1 ELSE 0 END) as year_1_purchase,
        MAX(CASE WHEN YEAR(order_date) = YEAR(MIN(order_date)) + 2 THEN 1 ELSE 0 END) as year_2_purchase
    FROM transactions
    GROUP BY customer_id
) cohort_analysis
GROUP BY cohort_year
ORDER BY cohort_year DESC;

-- =====================================================
-- 4. PRODUCT & INVENTORY ANALYTICS
-- =====================================================

-- Query 4.1: Brand Performance
SELECT 
    p.brand,
    COUNT(DISTINCT t.transaction_id) as order_count,
    COUNT(DISTINCT t.customer_id) as customer_count,
    SUM(t.final_amount_inr) as total_revenue,
    ROUND(AVG(t.final_amount_inr), 2) as avg_price,
    ROUND(AVG(t.product_rating), 2) as avg_rating,
    ROUND(SUM(CASE WHEN t.return_status = 'Returned' THEN 1 ELSE 0 END) / 
        COUNT(*) * 100, 2) as return_rate_percent
FROM transactions t
LEFT JOIN products p ON t.product_id = p.product_id
WHERE p.brand IS NOT NULL
GROUP BY p.brand
ORDER BY total_revenue DESC
LIMIT 50;

-- Query 4.2: Product Lifecycle Analysis
SELECT 
    p.product_name,
    p.launch_year,
    YEAR(MAX(t.order_date)) as last_sale_year,
    DATEDIFF(MAX(t.order_date), MIN(t.order_date)) as product_lifespan_days,
    COUNT(t.transaction_id) as total_orders,
    SUM(t.final_amount_inr) as total_revenue
FROM products p
LEFT JOIN transactions t ON p.product_id = t.product_id
GROUP BY p.product_id
ORDER BY total_revenue DESC;

-- Query 4.3: Return Analysis
SELECT 
    p.category,
    p.brand,
    COUNT(*) as total_orders,
    SUM(CASE WHEN t.return_status = 'Returned' THEN 1 ELSE 0 END) as returned_orders,
    ROUND(SUM(CASE WHEN t.return_status = 'Returned' THEN 1 ELSE 0 END) / 
        COUNT(*) * 100, 2) as return_rate_percent,
    t.return_reason
FROM transactions t
LEFT JOIN products p ON t.product_id = p.product_id
WHERE t.return_status = 'Returned'
GROUP BY p.category, p.brand, t.return_reason
ORDER BY return_rate_percent DESC;

-- =====================================================
-- 5. OPERATIONS & LOGISTICS
-- =====================================================

-- Query 5.1: Delivery Performance
SELECT 
    customer_city,
    COUNT(*) as order_count,
    ROUND(AVG(delivery_days), 2) as avg_delivery_days,
    ROUND(STDDEV(delivery_days), 2) as delivery_std_dev,
    ROUND(SUM(CASE WHEN delivery_days <= 3 THEN 1 ELSE 0 END) / 
        COUNT(*) * 100, 2) as on_time_percent,
    MIN(delivery_days) as min_days,
    MAX(delivery_days) as max_days
FROM transactions
GROUP BY customer_city
ORDER BY avg_delivery_days ASC;

-- Query 5.2: Payment Method Analysis
SELECT 
    payment_method,
    COUNT(*) as transaction_count,
    SUM(final_amount_inr) as total_amount,
    ROUND(AVG(final_amount_inr), 2) as avg_transaction_value,
    ROUND(COUNT(*) / (SELECT COUNT(*) FROM transactions) * 100, 2) as market_share_percent,
    YEAR(order_date) as year
FROM transactions
GROUP BY payment_method, YEAR(order_date)
ORDER BY year DESC, transaction_count DESC;

-- Query 5.3: Return Reasons Analysis
SELECT 
    return_reason,
    COUNT(*) as return_count,
    ROUND(COUNT(*) / (SELECT COUNT(*) FROM transactions WHERE return_status = 'Returned') * 100, 2) as percent_of_returns,
    ROUND(AVG(final_amount_inr), 2) as avg_return_value
FROM transactions
WHERE return_status = 'Returned' AND return_reason IS NOT NULL
GROUP BY return_reason
ORDER BY return_count DESC;

-- =====================================================
-- 6. FESTIVAL & SEASONAL ANALYSIS
-- =====================================================

-- Query 6.1: Festival Sales Impact
SELECT 
    festival_name,
    is_festival_sale,
    COUNT(*) as order_count,
    SUM(final_amount_inr) as total_revenue,
    ROUND(AVG(final_amount_inr), 2) as avg_order_value,
    ROUND(COUNT(*) / (SELECT COUNT(*) FROM transactions) * 100, 2) as percent_of_sales
FROM transactions
WHERE festival_name IS NOT NULL OR is_festival_sale = TRUE
GROUP BY festival_name, is_festival_sale
ORDER BY total_revenue DESC;

-- Query 6.2: Seasonal Comparison (Festival vs Non-Festival)
SELECT 
    MONTH(order_date) as month,
    is_festival_sale,
    COUNT(*) as order_count,
    SUM(final_amount_inr) as total_revenue,
    ROUND(AVG(final_amount_inr), 2) as avg_order_value
FROM transactions
GROUP BY MONTH(order_date), is_festival_sale
ORDER BY month ASC, is_festival_sale DESC;

-- =====================================================
-- 7. INDEXES FOR QUERY OPTIMIZATION
-- =====================================================

-- Create indexes for frequently queried columns
CREATE INDEX idx_order_date ON transactions(order_date);
CREATE INDEX idx_customer_id ON transactions(customer_id);
CREATE INDEX idx_product_id ON transactions(product_id);
CREATE INDEX idx_category ON products(category);
CREATE INDEX idx_payment_method ON transactions(payment_method);
CREATE INDEX idx_is_prime ON transactions(is_prime_member);

-- =====================================================
-- 8. MATERIALIZED VIEW REFRESH
-- =====================================================

-- Procedure to refresh daily metrics
DELIMITER //

CREATE PROCEDURE refresh_daily_metrics()
BEGIN
    DELETE FROM daily_sales_aggregate WHERE sale_date >= DATE_SUB(NOW(), INTERVAL 1 DAY);
    
    INSERT INTO daily_sales_aggregate 
    SELECT 
        order_date,
        SUM(final_amount_inr),
        COUNT(*),
        COUNT(DISTINCT customer_id),
        AVG(final_amount_inr),
        SUM(CASE WHEN return_status = 'Returned' THEN 1 ELSE 0 END),
        ROUND(SUM(CASE WHEN return_status = 'Returned' THEN 1 ELSE 0 END) / 
            COUNT(*) * 100, 2)
    FROM transactions
    WHERE order_date >= DATE_SUB(NOW(), INTERVAL 1 DAY)
    GROUP BY order_date;
END //

DELIMITER ;

-- Call procedure
CALL refresh_daily_metrics();

-- =====================================================
-- 9. DATA QUALITY CHECKS
-- =====================================================

-- Check for data quality issues
SELECT 'Missing Order Dates' as issue, COUNT(*) as count FROM transactions WHERE order_date IS NULL
UNION ALL
SELECT 'Missing Prices', COUNT(*) FROM transactions WHERE final_amount_inr IS NULL OR final_amount_inr <= 0
UNION ALL
SELECT 'Invalid Ratings', COUNT(*) FROM transactions WHERE customer_rating < 1 OR customer_rating > 5
UNION ALL
SELECT 'Future Orders', COUNT(*) FROM transactions WHERE order_date > NOW()
UNION ALL
SELECT 'Unrealistic Delivery', COUNT(*) FROM transactions WHERE delivery_days < 0 OR delivery_days > 30;

-- =====================================================
-- END OF SAMPLE QUERIES
-- =====================================================
