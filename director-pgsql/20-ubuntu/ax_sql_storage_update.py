#import the needed packages.
import psycopg2
import os
import time
import sys

def execute_query(cur, query):
  cur.execute(query)
  storage_names = cur.fetchall()
  return storage_names

def retry_with_backoff(cur, query, retries = 3, backoff_in_seconds = 1):
  x = 0
  while True:
    storage_names = execute_query(cur, query)
    if storage_names != []:
      return storage_names
    else:
      if x >= retries:
        return storage_names
      else:
        sleep = (backoff_in_seconds * 2 ** x )
        time.sleep(sleep)
        x += 1

def execute_sql_queries(jobid_list):
  """[To execute sql query in bareos database]

  Args:
    job_id : [Job ID of the completed job]
  """
  con = psycopg2.connect(host=os.environ['DB_HOST'], user=os.environ['DB_USER'],\
       password=os.environ['DB_PASSWORD'], database="bareos", port=os.environ['DB_PORT'])
  print("Database connected successfully")

  cur = con.cursor()
  for job_id in jobid_list:

    select_query = "SELECT name from public.storage where storageid in \
      (SELECT storageid FROM public.media WHERE mediaid IN \
        (SELECT mediaid FROM public.jobmedia where jobid = {}))".format(job_id)
    storage_names = execute_query(cur, select_query)

    for storage_name in storage_names:

      storagename = storage_name[0]
      if 'Restore-' not in storagename:
        cur.execute("SELECT storageId from public.storage WHERE name = '{}';".format('Restore-'+storagename))

        id_list = cur.fetchall()
        for id in id_list:
          storageid = id[0]
          update_query = "UPDATE public.media SET volstatus = 'Full', storageid={0} WHERE mediaid IN \
            (SELECT mediaid FROM public.media WHERE mediaid IN \
              (SELECT mediaid FROM public.jobmedia where jobid = {1}) );".format(storageid,job_id)

          cur.execute(update_query)
          con.commit()

  con.close()
  print("Restore storage created successfully")


if __name__ == '__main__':
  jobid_list = sys.argv[1].split(',')
  execute_sql_queries(jobid_list)
