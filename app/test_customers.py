
import pandas as pd
from db import get_connection

connection = get_connection()

query = "SELECT * FROM customers"
df = pd.read_sql(query, connection)

print("Customer Data:")
print(df)

connection.close()
