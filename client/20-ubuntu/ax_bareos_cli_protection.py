#import the needed packages.
from google.cloud import pubsub_v1
import bareos.bsock
import os
import json
import sys
import logging
import psycopg2
import time

# def read_env_vars_file(job_id):

#   """[To read the env variables file]

#   Args:
#     Job_ID ([String]): [The Job_id of the running job]

#   Returns:
#       [String]: [The Bareos Director Environment Values]
#   """
#   logging.debug("Read the env vars file")
#   env_vars_file = open("env-vars-{}.txt".format(job_id), "r")
#   logging.debug("Env vars file: {}".format(env_vars_file))
#   return env_vars_file.read()

# def write_env_vars_to_file(job_id):

#   """[To get the Bareos director password in env vars and write into file]

#   Args:
#     Job_ID ([String]): [The Job_id of the running job]

#   """
#   logging.debug("Getting bareos director env vars")
#   director_password = os.environ['BAREOS_DIRECTOR_PASSWORD']
#   env_vars_file = open("env-vars-{}.txt".format(job_id), 'w')
#   logging.debug("Writing the bareos director password to file")
#   env_vars_file.write(director_password)
#   env_vars_file.close()

# def remove_env_vars_file(action, job_id):

#   """[To remove the bareos director env_vars file]

#   Args:
#     Action ([String]): [The action which is mentioned in the runscript]
#     Job_ID ([String]): [The Job_id of the running job]

#   """
#   # Remove the password text file
#   logging.debug("Remove the bareos director env vars file")
#   if os.path.exists("env-vars-{}.txt".format(job_id)):
#     os.remove("env-vars-{}.txt".format(job_id))
#     logging.debug("Remove the bareos director env vars file successfully")

def create_bareos_director_connection(director_password):

  """[To create the connection for Bareos director]

  Args:
    Director_password ([String]): [The password of the Bareos Director]

  Returns:
      [String]: [The Bareos Director Connection]
  """
  password = bareos.bsock.Password(director_password)
  try:
    logging.debug("Establishing the director connection")
    director_console_connection = bareos.bsock.DirectorConsoleJson(address=os.environ['BAREOS_DIRECTOR_HOST'], \
                      port=9101, password=password, protocolversion=1, tls_psk_enable=False, \
                      tls_psk_require=False)

    #   logging.debug("Establishing the director connection")
    #   director_console_connection = bareos.bsock.DirectorConsoleJson(address='0.0.0.0', \
    #                     port=9101, password=password, protocolversion=1, tls_psk_enable=False, \
    #                     tls_psk_require=False)
  except Exception as e:
    logging.debug("Bareos connection issue: {}".format(e))
    raise
  logging.debug("Bareos director connected successfully")
  return director_console_connection

def execute_query(cur, query):
  cur.execute(query)
  storage_names = cur.fetchall()
  return storage_names

def retry_with_backoff(cur, query, retries = 10, backoff_in_seconds = 1):
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

def execute_sql_queries(job_id):
  """[To execute sql query in bareos database]

  Args:
    job_id : [Job ID of the completed job]
  """
  con = psycopg2.connect(host=os.environ['DB_HOST'], user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'], database="bareos", port=os.environ['DB_PORT'])
  print("Database connected successfully")

  cur = con.cursor()
  query = "SELECT name from public.storage where storageid in ( SELECT storageid FROM public.media WHERE mediaid IN (SELECT mediaid FROM public.jobmedia where jobid = {}))".format(job_id)
  storage_names = retry_with_backoff(cur, query)

  if storage_names != []:
    for storage_name in storage_names:
        storagename = storage_name[0]

    cur.execute("SELECT storageId from public.storage WHERE name = '{}';".format('Restore-'+storagename))
    id_list = cur.fetchall()

    for id in id_list:
        storageid = id[0]
    time.sleep(30)
    cur.execute("UPDATE public.media SET volstatus = 'Full', storageid={0} WHERE mediaid IN (SELECT mediaid FROM public.media WHERE mediaid IN (SELECT mediaid FROM public.jobmedia where jobid = {1}) );".format(storageid,job_id))

    print("Restore storage created successfully")
  else:
    raise ValueError("Failed: Empty storageNames returned")

  con.commit()
  con.close()

def execute_bareos_director_commands(director_console_connection, command):

  """[To execute the Bareos Director Commands]

  Args:
    Director_console_connection : [The Connection of the Bareos Director]

  Returns:
      [JSON]: [The Bareos command output]
  """
  logging.debug("Executing the bareos commands using the bareos director connection")
  try:
    result_json = director_console_connection.call(command)
    logging.debug("Bareos command executed successfully")
  except Exception as e:
    logging.debug("Command execution issue: {}".format(e))
    raise
  return result_json

def prepare_job_json_data(action, job_id, director_console_connection):

  """[To prepare the each job json based on the runscript action]

  Args:
    Topic_path ([String]): [The action which is mentioned in the runscript]
    Job_ID ([String]): [The Job_id of the running job]

  Returns:
    [String]: [ The entire job details ]
  """
  # Get the job_details
  logging.debug("Getting the job details of the job: {} !!!!!!!!!!!".format(job_id))
  command = "llist jobid={}".format(job_id)
  result_json = execute_bareos_director_commands(director_console_connection, command)
  job_data = result_json['jobs'][0]
  #Adding required(default) parameters to the job json data
  job_data.update({'vmId': vm_id })
  job_data.update({'protectionPolicyId': policy_id })
  job_data.update({'bucketName': bucket_name })
  job_data.update({'tenantId': tenant_id })


  if action == "pre-action-job" and str(job_data['jobstatus']) == 'R':
    job_data['jobstatus'] = 'INPROGRESS'
  if str(job_data['jobstatus']) == 'f' or ( action == "post-action-job" and ( sys.argv[8] == 'Fatal' or sys.argv[8] == 'Canceled' or sys.argv[8] == 'Error' )):
    job_data['jobstatus'] = 'FAILED'
  if action == "post-action-job" and ( str(job_data['jobstatus']) == 'R' or str(job_data['jobstatus']) == 'T' ) and sys.argv[8] == 'OK':
    job_data['jobstatus'] = 'COMPLETED'

  #Update vmname and jobexitstatus values in cloud_assembly_vm_file_json
  job_data.update({'vmname': job_data['fileset'].split('-')[-1]})
  if action == "post-action-job":
    job_data.update({'jobexitstatus': sys.argv[8]})
  logging.debug("Job creation details: {}".format(job_data))

  #Update joblogs in cloud_assembly_vm_file_json
  logging.debug("Getting the job logs of this job: {} !!!!!!!!!!!!".format(job_id))
  command = "list joblog jobid={}".format(job_id)
  results_joblog = execute_bareos_director_commands(director_console_connection, command)

  job_data.update({'joblog': results_joblog['joblog'] })
  logging.debug("Job creation logs: {}".format(results_joblog['joblog']))

  #Update volumes in cloud_assembly_vm_file_json
  if action == "post-action-job":
    logging.debug("Getting the job volumes of this job: {} !!!!!!!!!!!!!!!!".format(job_id))
    command = "list volumes jobid={}".format(job_id)
    result_volumes = execute_bareos_director_commands(director_console_connection, command)
    job_data.update({'backupjobfiles': result_volumes['volumes'] })
  return job_data

def publish_job_json_to_pubsub(topic_path, job_data):

  """[To publish job json details to pubsub]

  Args:
    topic_path ([String]): [The topic_path is to publish the patricular topic]
    job_data ([Dict]): [The Job data contains the running job details and it's log]

  """
  try:
    logging.debug("Establishing the publisher client connection")
    publisher = pubsub_v1.PublisherClient()
    logging.debug("Connected {} pubsub".format(topic_path.split("/")[-1]))
  except Exception as e:
    logging.debug("Pubsub connection issue: {}".format(e))
    raise

  logging.debug("Converting dict into JSON String")
  #Convert messages dict into the JSON_String for encode
  messages = json.dumps(job_data)
  #Encode the sample messages before publish
  logging.debug("Encoding the messages before publish")
  messages = messages.encode("utf-8")
  #Publish the messages in the Pub/Sub topic
  logging.debug("Publishing data to this topic {}!!!!!!!!!!!!".format(topic_path.split("/")[-1]))
  try:
    topic = publisher.publish(topic_path, messages, eventName="INTENT_VMWARE_PROTECTION_JOB_STATUS_UPDATE")
    logging.debug("Published message id = {}. Published messages to {}.".format(topic.result(),messages))
  except Exception as e:
    logging.debug("Pubsub publish issue: {}".format(e))
    raise

if __name__ == '__main__':

 # Retrieve the command_line inputs

  action = sys.argv[1]
  topic_path = sys.argv[2] if len(sys.argv) >= 3 else 'None'
  job_id = sys.argv[3] if len(sys.argv) >= 4 else '000'
  # job_name = sys.argv[4] if len(sys.argv) >= 5 else 'None'
  vm_id = sys.argv[4] if len(sys.argv) >= 5 else '000'
  policy_id = sys.argv[5] if len(sys.argv) >= 6 else '000'
  bucket_name = sys.argv[6] if len(sys.argv) >= 7 else 'None'
  tenant_id = sys.argv[7] if len(sys.argv) >= 8 else 'None'

  # Enable the logging method
  logging.basicConfig(filename='/var/log/bareos/before_runscript.log', level=logging.DEBUG, \
    format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
  logging.debug("!!!!!!!!!!!!Runscript Action -{}!!!!!!!!!!!!".format(action))
  logging.debug("New Job is triggered now and the job_id is {}".format(job_id))

  logging.debug("Calling function to write the bareos director password in file")
  # if action != "pre-action-job" and action != "post-action-job":
  #   write_env_vars_to_file(job_id)

  # if action != "run-without-client":
  logging.debug("Getting the Bareos director password to connect the Bareos director")
    # director_password = read_env_vars_file(job_id)
  logging.debug("Read the password successfully")

  director_password = os.environ['BAREOS_DIRECTOR_PASSWORD']
  # Calling the function to create the bareos_director_connection
  logging.debug("Connecting to the Bareos director to getting the job details")
  director_console_connection = create_bareos_director_connection(director_password)

  logging.debug("Updating the storageid for the completed job")
  if action == "post-action-job" and sys.argv[8] == 'OK':
    execute_sql_queries(job_id)
  if action != "pre-action-job" and action != "post-action-job":
    logging.debug("Reloading the bareos director configuration")
    result_json = execute_bareos_director_commands(director_console_connection, action)
    logging.debug("Command result {}".format(result_json))

  else:
    # Execute the bareos commands and prepare the json job details
    logging.debug("Calling the function to preparing the json job details")
    job_data = prepare_job_json_data(action, job_id, director_console_connection)

    # Calling the pubsub to publish the message
    logging.debug("Calling the Pubsub function to publish the messages")
    publish_job_json_to_pubsub(topic_path, job_data)
    logging.debug("Published JSON successfully")

  # if action != "pre-action-job":
  #   logging.debug("Calling function to delete the bareos director password file")
  #   remove_env_vars_file(action, job_id)