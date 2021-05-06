#import the needed packages.
import os
import sys
import psycopg2

def execute_sql_queries(storage_name):
  """[To execute sql query in bareos database]

  Args:
    storage_name : [Restore storage name]
  """
  con = psycopg2.connect(host=os.environ['DB_HOST'], user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'], database="bareos", port=os.environ['DB_PORT'])
  print("Database connected successfully")

  cur = con.cursor()
  cur.execute("INSERT INTO public.storage(name, autochanger) VALUES ('{}', 0);".format(storage_name))

  print("Restore storage created successfully")

  con.commit()
  con.close()

if __name__ == '__main__':
 # Retrieve the command_line inputs
  storage_name = sys.argv[1]
  execute_sql_queries(storage_name)