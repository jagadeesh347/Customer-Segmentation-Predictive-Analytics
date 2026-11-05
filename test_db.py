from app.db import get_connection

try:
    connection = get_connection()
    print("MySQL connected successfully!")
    connection.close()
    print("Connection closed.")

except Exception as e:
    print("Connection failed:", e)
