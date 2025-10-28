import pymysql
from src.config import DB_CONFIG

def create_database():
    connection = pymysql.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        port=DB_CONFIG['port']
    )
    cursor = connection.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS amazon_sales;")
    connection.commit()
    cursor.close()
    connection.close()
    print("✅ Database 'amazon_sales' is ready!")

def test_connection():
    try:
        connection = pymysql.connect(
            **DB_CONFIG
        )
        print("✅ Successfully connected to MySQL database!")
        connection.close()
    except Exception as e:
        print("❌ Error:", e)

if __name__ == "__main__":
    create_database()
    test_connection()
