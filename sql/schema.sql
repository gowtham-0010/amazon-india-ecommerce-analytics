-- =====================================================
-- AMAZON INDIA E-COMMERCE DATABASE SCHEMA
-- =====================================================
-- Optimized schema for analytics with ~1M transaction records

-- Create database
CREATE DATABASE IF NOT EXISTS amazon_india_analytics;
USE amazon_india_analytics;

-- =====================================================
-- TABLE 1: CUSTOMERS
-- =====================================================
CREATE TABLE IF NOT EXISTS customers (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(255),
    customer_email VARCHAR(255) UNIQUE,
    customer_city VARCHAR(100),
    customer_state VARCHAR(100),
    customer_tier VARCHAR(50),
    is_prime_member BOOLEAN DEFAULT FALSE,
    customer_since DATE,
    total_orders INT DEFAULT 0,
    lifetime_value DECIMAL(15, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_customer_city (customer_city),
    INDEX idx_is_prime (is_prime_member),
    INDEX idx_customer_tier (customer_tier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE 2: PRODUCTS
-- =====================================================
CREATE TABLE IF NOT EXISTS products (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(500),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    brand VARCHAR(100),
    base_price_2015 DECIMAL(12, 2),
    weight_kg DECIMAL(8, 2),
    is_prime_eligible BOOLEAN DEFAULT TRUE,
    launch_year INT,
    model VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_category (category),
    INDEX idx_brand (brand),
    INDEX idx_launch_year (launch_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE 3: TIME DIMENSION
-- =====================================================
CREATE TABLE IF NOT EXISTS time_dimension (
    date_id INT PRIMARY KEY,
    full_date DATE UNIQUE,
    year INT,
    quarter INT,
    month INT,
    week INT,
    day_of_week INT,
    day_name VARCHAR(20),
    month_name VARCHAR(20),
    is_weekend BOOLEAN,
    is_holiday BOOLEAN DEFAULT FALSE,
    festival_name VARCHAR(100),
    
    INDEX idx_year (year),
    INDEX idx_month (month),
    INDEX idx_festival (festival_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE 4: TRANSACTIONS (MAIN FACT TABLE)
-- =====================================================
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id BIGINT PRIMARY KEY,
    customer_id INT NOT NULL,
    product_id INT NOT NULL,
    order_date DATE NOT NULL,
    order_month INT,
    order_quarter INT,
    order_year INT,
    
    -- Pricing
    original_price_inr DECIMAL(12, 2),
    discount_percent DECIMAL(5, 2),
    final_amount_inr DECIMAL(12, 2),
    delivery_charges DECIMAL(10, 2),
    tax_amount DECIMAL(10, 2),
    
    -- Operations
    payment_method VARCHAR(50),
    delivery_days INT,
    return_status VARCHAR(50),
    return_reason VARCHAR(255),
    
    -- Customer Info
    customer_rating DECIMAL(3, 1),
    product_rating DECIMAL(3, 1),
    
    -- Business
    is_prime_member BOOLEAN,
    is_prime_eligible BOOLEAN,
    is_festival_sale BOOLEAN,
    festival_name VARCHAR(100),
    customer_spending_tier VARCHAR(50),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    
    -- Indexes
    INDEX idx_customer_id (customer_id),
    INDEX idx_product_id (product_id),
    INDEX idx_order_date (order_date),
    INDEX idx_order_year (order_year),
    INDEX idx_payment_method (payment_method),
    INDEX idx_return_status (return_status),
    INDEX idx_festival (is_festival_sale),
    INDEX idx_final_amount (final_amount_inr)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE 5: ANALYTICS VIEWS & AGGREGATES
-- =====================================================
CREATE TABLE IF NOT EXISTS daily_sales_aggregate (
    aggregation_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_date DATE NOT NULL,
    total_revenue DECIMAL(15, 2),
    total_orders INT,
    unique_customers INT,
    avg_order_value DECIMAL(12, 2),
    return_count INT,
    return_rate DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_sale_date (sale_date),
    UNIQUE KEY unique_date (sale_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- INDEXES FOR PERFORMANCE OPTIMIZATION
-- =====================================================
CREATE INDEX idx_transactions_date_amount ON transactions(order_date, final_amount_inr);
CREATE INDEX idx_transactions_customer_date ON transactions(customer_id, order_date);
CREATE INDEX idx_transactions_product_category ON transactions(product_id);
CREATE INDEX idx_transactions_payment_date ON transactions(payment_method, order_date);

-- =====================================================
-- MATERIALIZED VIEWS (Using Tables)
-- =====================================================

-- Revenue by Category
CREATE TABLE IF NOT EXISTS revenue_by_category (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(100),
    month_year VARCHAR(10),
    total_revenue DECIMAL(15, 2),
    order_count INT,
    unique_customers INT,
    avg_rating DECIMAL(3, 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_category_month (category, month_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Customer Segmentation
CREATE TABLE IF NOT EXISTS customer_segmentation (
    segment_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    rfm_score VARCHAR(3),
    recency_days INT,
    frequency_purchases INT,
    monetary_value DECIMAL(15, 2),
    segment_name VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    INDEX idx_customer_id (customer_id),
    INDEX idx_segment_name (segment_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Geographic Performance
CREATE TABLE IF NOT EXISTS geographic_performance (
    geo_id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(100),
    state VARCHAR(100),
    tier VARCHAR(20),
    total_revenue DECIMAL(15, 2),
    order_count INT,
    unique_customers INT,
    avg_delivery_days DECIMAL(5, 2),
    return_rate DECIMAL(5, 2),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_city_state (city, state)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Payment Method Analytics
CREATE TABLE IF NOT EXISTS payment_analytics (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    payment_method VARCHAR(50),
    month_year VARCHAR(10),
    transaction_count INT,
    total_amount DECIMAL(15, 2),
    success_rate DECIMAL(5, 2),
    market_share DECIMAL(5, 2),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_payment_month (payment_method, month_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- STORED PROCEDURES FOR COMMON QUERIES
-- =====================================================

DELIMITER //

-- Procedure to calculate daily metrics
CREATE PROCEDURE IF NOT EXISTS calculate_daily_metrics(IN p_date DATE)
BEGIN
    INSERT INTO daily_sales_aggregate (sale_date, total_revenue, total_orders, unique_customers, avg_order_value, return_count, return_rate)
    SELECT 
        p_date,
        SUM(final_amount_inr),
        COUNT(*),
        COUNT(DISTINCT customer_id),
        AVG(final_amount_inr),
        SUM(CASE WHEN return_status = 'Returned' THEN 1 ELSE 0 END),
        ROUND(SUM(CASE WHEN return_status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*) * 100, 2)
    FROM transactions
    WHERE order_date = p_date
    ON DUPLICATE KEY UPDATE
        total_revenue = VALUES(total_revenue),
        total_orders = VALUES(total_orders),
        unique_customers = VALUES(unique_customers),
        avg_order_value = VALUES(avg_order_value),
        return_count = VALUES(return_count),
        return_rate = VALUES(return_rate);
END //

-- Procedure to get top customers
CREATE PROCEDURE IF NOT EXISTS get_top_customers(IN p_limit INT)
BEGIN
    SELECT 
        c.customer_id,
        c.customer_name,
        COUNT(t.transaction_id) as total_orders,
        SUM(t.final_amount_inr) as total_spent,
        AVG(t.customer_rating) as avg_rating,
        c.is_prime_member
    FROM customers c
    LEFT JOIN transactions t ON c.customer_id = t.customer_id
    GROUP BY c.customer_id
    ORDER BY total_spent DESC
    LIMIT p_limit;
END //

DELIMITER ;

-- =====================================================
-- VIEWS FOR DASHBOARD QUERIES
-- =====================================================

-- Revenue Dashboard View
CREATE OR REPLACE VIEW v_revenue_dashboard AS
SELECT 
    t.order_date,
    t.order_year,
    t.order_month,
    t.order_quarter,
    p.category,
    c.customer_city,
    SUM(t.final_amount_inr) as daily_revenue,
    COUNT(t.transaction_id) as order_count,
    AVG(t.final_amount_inr) as avg_order_value,
    AVG(t.customer_rating) as avg_rating
FROM transactions t
LEFT JOIN products p ON t.product_id = p.product_id
LEFT JOIN customers c ON t.customer_id = c.customer_id
GROUP BY t.order_date, t.order_year, t.order_month, t.order_quarter, p.category, c.customer_city;

-- Customer Analytics View
CREATE OR REPLACE VIEW v_customer_analytics AS
SELECT 
    c.customer_id,
    c.customer_city,
    c.customer_tier,
    c.is_prime_member,
    COUNT(t.transaction_id) as total_purchases,
    SUM(t.final_amount_inr) as total_spending,
    AVG(t.final_amount_inr) as avg_purchase_value,
    MAX(t.order_date) as last_purchase_date,
    MIN(t.order_date) as first_purchase_date,
    DATEDIFF(NOW(), MAX(t.order_date)) as days_since_last_purchase
FROM customers c
LEFT JOIN transactions t ON c.customer_id = t.customer_id
GROUP BY c.customer_id;

-- Category Performance View
CREATE OR REPLACE VIEW v_category_performance AS
SELECT 
    p.category,
    t.order_year,
    COUNT(t.transaction_id) as order_count,
    SUM(t.final_amount_inr) as total_revenue,
    AVG(t.final_amount_inr) as avg_order_value,
    AVG(t.product_rating) as avg_rating,
    SUM(CASE WHEN t.return_status = 'Returned' THEN 1 ELSE 0 END) as return_count
FROM transactions t
LEFT JOIN products p ON t.product_id = p.product_id
GROUP BY p.category, t.order_year;

-- =====================================================
-- INITIAL DATA LOAD SETTINGS
-- =====================================================

-- Disable foreign key checks during bulk insert
-- SET FOREIGN_KEY_CHECKS=0;

-- After loading data:
-- SET FOREIGN_KEY_CHECKS=1;
-- ANALYZE TABLE transactions;
-- OPTIMIZE TABLE transactions;
