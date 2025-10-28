# src/config.py



# MySQL Database Configuration
DB_CONFIG = { 
    'host': 'localhost',
    'user': 'root',                 # <-- use same as Workbench
    'password': 'gowtham@0010',  # <-- replace with ACTUAL password 
    'database': 'amazon_sales',     # <-- will create this next
    'port': 3306
}

# File Paths
RAW_DATA_PATH = 'data/raw/'
PROCESSED_DATA_PATH = 'data/processed/'
INTERIM_DATA_PATH = 'data/interim/'
