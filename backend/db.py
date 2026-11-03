
import os
import mysql.connector
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "calibration_management")
        )

        return connection

    except mysql.connector.Error as error:
        print("Database connection failed:", error)
        return None
