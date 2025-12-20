"""
SQL LOADER MODULE
================

Database connectivity and data loading utilities.
Handles bulk inserts, connection management, and data validation.

Author: Data Engineering Team
Version: 1.1 (FIXED: Removed method='multi' parameter explosion)
"""

import pandas as pd
import logging
from typing import Optional, Tuple
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import config

logger = logging.getLogger(__name__)

class DatabaseLoader:
    """Handle database operations for Amazon India analytics."""

    def __init__(self, db_url: str = None, batch_size: int = 5000):
        """
        Initialize database loader.

        Args:
            db_url: Database connection URL
            batch_size: Records per batch insert
        """
        self.db_url = db_url or config.DATABASE_URL
        self.batch_size = batch_size
        self.engine = None
        self.session = None
        self.connection_status = False

    def connect(self) -> bool:
        """
        Establish database connection.

        Returns:
            Connection status
        """
        try:
            self.engine = create_engine(self.db_url, echo=False)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.connection_status = True
            logger.info(f"✓ Connected to database: {self.db_url.split('@')[1] if '@' in self.db_url else 'SQLite'}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"✗ Database connection failed: {e}")
            self.connection_status = False
            return False

    def disconnect(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            self.connection_status = False
            logger.info("Database connection closed")

    def create_tables(self, schema_sql: str) -> bool:
        """
        Create database schema from SQL script.

        Args:
            schema_sql: SQL schema script

        Returns:
            Success status
        """
        if not self.connection_status:
            logger.error("Database not connected")
            return False

        try:
            with self.engine.connect() as conn:
                for statement in schema_sql.split(';'):
                    if statement.strip():
                        conn.execute(text(statement))
                conn.commit()
            logger.info("✓ Database schema created successfully")
            return True
        except SQLAlchemyError as e:
            logger.error(f"✗ Error creating schema: {e}")
            return False

    def bulk_insert_dataframe(self, df: pd.DataFrame, table_name: str,
                             if_exists: str = 'append',
                             validate_schema: bool = True) -> Tuple[int, bool]:
        """
        Insert DataFrame into database in batches.

        Uses standard parameter binding (executemany protocol).
        FIXED: Removed method='multi' which caused query explosion.

        Args:
            df: DataFrame to insert
            table_name: Target table name
            if_exists: 'fail', 'replace', or 'append'
            validate_schema: Validate schema before insert

        Returns:
            Tuple of (inserted_rows, success_status)
        """
        if not self.connection_status:
            logger.error("Database not connected")
            return 0, False

        try:
            if validate_schema:
                expected_cols = self._get_table_columns(table_name)
                if expected_cols and not set(df.columns).issubset(set(expected_cols)):
                    logger.warning(f"Column mismatch for {table_name}")

            df = self._clean_dataframe(df)

            rows_inserted = 0
            total_batches = len(df) // self.batch_size + (1 if len(df) % self.batch_size else 0)

            for i in range(0, len(df), self.batch_size):
                batch = df.iloc[i:i + self.batch_size].copy()
                try:
                    batch.to_sql(
                        table_name,
                        self.engine,
                        if_exists=if_exists if i == 0 else 'append',
                        index=False,
                        chunksize=self.batch_size
                    )

                    rows_inserted += len(batch)
                    batch_num = i // self.batch_size + 1
                    logger.info(f" Batch {batch_num}/{total_batches}: {len(batch)} rows inserted")

                except SQLAlchemyError as e:
                    logger.error(f" Batch {i//self.batch_size + 1} failed: {e}")
                    return rows_inserted, False

            logger.info(f"✓ Inserted {rows_inserted} rows into {table_name}")
            return rows_inserted, True

        except Exception as e:
            logger.error(f"✗ Error inserting data: {e}")
            return 0, False

    def execute_query(self, query: str) -> Optional[pd.DataFrame]:
        """
        Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query

        Returns:
            Result DataFrame or None
        """
        if not self.connection_status:
            logger.error("Database not connected")
            return None

        try:
            with self.engine.connect() as conn:
                result = pd.read_sql(query, conn)
                logger.info(f"✓ Query executed: {len(result)} rows returned")
                return result
        except SQLAlchemyError as e:
            logger.error(f"✗ Query execution failed: {e}")
            return None

    def get_table_stats(self, table_name: str) -> dict:
        """
        Get statistics for a table.

        Args:
            table_name: Table name

        Returns:
            Statistics dictionary
        """
        if not self.connection_status:
            return {}

        try:
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            result = self.execute_query(count_query)
            if result is not None:
                return {
                    'table_name': table_name,
                    'row_count': result['count'].values[0],
                    'status': 'OK'
                }
        except:
            pass

        return {'table_name': table_name, 'row_count': 0, 'status': 'ERROR'}

    def _get_table_columns(self, table_name: str) -> list:
        """Get column names for a table."""
        try:
            inspector = inspect(self.engine)
            return [col['name'] for col in inspector.get_columns(table_name)]
        except:
            return []

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean DataFrame before database insert.

        Args:
            df: Input DataFrame

        Returns:
            Cleaned DataFrame
        """
        df = df.copy()

        df = df.replace([float('inf'), float('-inf')], None)

        for col in df.columns:
            if 'date' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col])
                except:
                    pass

        for col in df.select_dtypes(include=['object']).columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str[:255]

        return df

    def backup_table(self, table_name: str, backup_name: str) -> bool:
        """
        Create backup of a table.

        Args:
            table_name: Source table
            backup_name: Backup table name

        Returns:
            Success status
        """
        if not self.connection_status:
            return False

        try:
            query = f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}"
            with self.engine.connect() as conn:
                conn.execute(text(query))
                conn.commit()
            logger.info(f"✓ Table backed up: {table_name} -> {backup_name}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"✗ Backup failed: {e}")
            return False


class DataValidator:
    """Validate data before database insertion."""

    @staticmethod
    def validate_dataframe(df: pd.DataFrame, schema: dict) -> Tuple[bool, list]:
        """
        Validate DataFrame against schema.

        Args:
            df: DataFrame to validate
            schema: Expected schema (column -> type mapping)

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        for col, dtype in schema.items():
            if col not in df.columns:
                errors.append(f"Missing column: {col}")
            elif df[col].isna().sum() > len(df) * 0.5:
                errors.append(f"High null count in {col}: {df[col].isna().sum()}")

        if df.duplicated().any():
            dup_count = df.duplicated().sum()
            errors.append(f"Found {dup_count} duplicate rows")

        return len(errors) == 0, errors

    @staticmethod
    def validate_numeric(series: pd.Series, min_val: float = None,
                        max_val: float = None) -> Tuple[bool, list]:
        """Validate numeric column."""
        errors = []

        if min_val is not None:
            violators = (series < min_val).sum()
            if violators > 0:
                errors.append(f"{violators} values below minimum ({min_val})")

        if max_val is not None:
            violators = (series > max_val).sum()
            if violators > 0:
                errors.append(f"{violators} values above maximum ({max_val})")

        return len(errors) == 0, errors


if __name__ == "__main__":

    loader = DatabaseLoader()

    if loader.connect():
        try:
            csv_path = config.CLEANED_DATA_DIR / "transactions_cleaned.csv"
            print(f"\n📥 Loading data from: {csv_path}")

            if csv_path.exists():
                df_transactions = pd.read_csv(
                    csv_path,
                    dtype={
                        'order_date': 'object',
                        'original_price_inr': 'float64',
                        'final_amount_inr': 'float64',
                        'delivery_charges': 'float64',
                        'customer_rating': 'float32',
                        'product_rating': 'float32',
                        'is_prime_member': 'bool',
                        'is_prime_eligible': 'bool',
                        'is_festival_sale': 'bool',
                    }
                )

                print(f"✓ Loaded {len(df_transactions):,} rows from CSV")
                print(f"📊 DataFrame shape: {df_transactions.shape}")
                print(f"💾 Approximate memory usage: {df_transactions.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

                print(f"\n🔄 Inserting data into 'transactions' table...")
                rows_inserted, success = loader.bulk_insert_dataframe(
                    df_transactions,
                    'transactions',
                    if_exists='append',
                    validate_schema=True
                )

                if success:
                    print(f"\n✅ Successfully inserted {rows_inserted:,} rows")

                    stats = loader.get_table_stats('transactions')
                    print(f"\n📈 Table Statistics:")
                    print(f"   Table: {stats['table_name']}")
                    print(f"   Total rows: {stats['row_count']:,}")
                    print(f"   Status: {stats['status']}")
                else:
                    print(f"\n❌ Data insertion failed or incomplete")
                    print(f"   Rows inserted: {rows_inserted:,}")

            else:
                print(f"❌ CSV file not found: {csv_path}")

        except Exception as e:
            print(f"❌ Error during data loading: {e}")
            import traceback
            traceback.print_exc()

        finally:
            loader.disconnect()

    else:
        print("❌ Failed to connect to database")