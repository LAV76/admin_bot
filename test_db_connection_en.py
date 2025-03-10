import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    try:
        # Get connection details from environment variables
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASS", "postgres")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        database = os.getenv("DB_NAME", "tgbot_admin")
        
        # Print connection info
        print(f"Connecting to database: {user}@{host}:{port}/{database}")
        
        # Try to connect
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database
        )
        
        # Check connection with a query
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"Connection successful!")
        print(f"PostgreSQL version: {version}")
        
        # List all tables in the database
        cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        """)
        
        tables = cursor.fetchall()
        print("Tables in database:")
        for table in tables:
            print(f"- {table[0]}")
        
        # Close connection
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Connection error: {str(e)}")

if __name__ == "__main__":
    test_connection() 