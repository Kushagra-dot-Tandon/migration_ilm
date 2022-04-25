import sys
import logging
import requests
import psycopg2
from datetime import datetime
from requests.auth import HTTPBasicAuth

logging.basicConfig(
    level=logging.INFO,
    format="{asctime} {levelname:<10} {message}",
    style='{')
logging.getLogger(__name__)


def connect_to_db(database_name):
    error = False
    try:
        connection = psycopg2.connect(
            host="10.100.86.143",
            database=database_name,
            user="snappyflow",
            password="maplelabs")
        logging.info(f"Connection to database {database_name} is successful")
        return connection, error
    except Exception as err:
        error = True
        logging.error(f"Unable to Connect to {database_name} database with error {err} ")
        return "", error


def get_details_from_db(query, database_name):
    connection, error = connect_to_db(database_name)
    cursor = connection.cursor()
    if not error:
        try:
            cursor.execute(query)
            es_clusters = cursor.fetchall()
            return es_clusters
        except Exception as err:
            logging.error(f"Error in getting details from {database_name} with query {query} with error {err}")
    else:
        sys.exit(1)


def generate_foreign_key(table_name, cluster_name):
    connection, error = connect_to_db(database_name="elasticsearch_manager")
    cursor = connection.cursor()
    if not error:
        query = f"Select * from {table_name} where name like %s"
        try:
            cursor.execute(query, (cluster_name,))
            cluster_model = cursor.fetchone()
            return cluster_model
        except Exception as err:
            logging.error(f"Error in generating foreign key for table {table_name} , {cluster_name} with error {err}")
    else:
        sys.exit(1)


def call_elasticsearch(url, cluster_details):
    response = requests.request("GET", url, auth=HTTPBasicAuth(cluster_details[8], cluster_details[9]))
    return response


def check_shards_count(index_name: str, es_url, cluster_details) -> int:
    url = es_url + index_name + '_settings'
    response = call_elasticsearch(url, cluster_details)
    if response.ok:
        return int(list(response.json().values())[0]['settings']['index']['number_of_shards'])
    else:
        logging.error(f'Error in checking shards count for {index_name} : {response.text}')


# Function to check if the particular index is Merged , Shrinked , Warm
def check_index_smw_state(index_name: str, es_url, cluster_details):
    url = es_url + index_name + '_cat/segments'
    response = call_elasticsearch(url, cluster_details)
    if response.ok:
        if len(response.json()) == 2:
            return "MERGED"
        elif check_shards_count(index_name, es_url) == 1:
            # TODO: check the state of index => shrinking or done etc.
            # check_shrinking_index_status(index_name)=> _cat/shards(2) => started
            return "SHRINKED"
        else:
            return "MOVED-TO-WARM"
    else:
        logging.error('Error in checking if particular index %s is merged , shrinked or warm', index_name)


# Function to check Index Aliases States
def check_index_aliases_state(index_name: str, es_url, cluster_details):
    url = es_url + index_name
    response = call_elasticsearch(url, cluster_details)
    if response.ok:
        index_res = list(list(response.json().values())[0]['aliases'].keys())
        if len(index_res) == 2:
            return "CREATED", {"op_complete": True}
        else:
            return "ROLLED-OVER", {"op_complete": True}
    else:
        logging.error(f'Error in checking  {index_name} aliases state : {response.text}')


def create_elasticsearch_url(cluster_details):
    es_url = "http://" + cluster_details[5] + ":" + str(cluster_details[6]) + "/"
    return es_url


# Function to check if particular index is HOT or WARM
def check_index_allocation_state(index_name: str, datasource_cluster_id: int):
    cluster_details = get_details_from_db(query=f"select * from elasticsearch_cluster where id={datasource_cluster_id}",
                                          database_name="elasticsearch_manager")[0]

    url = create_elasticsearch_url(cluster_details) + index_name + '/_settings'
    print(url)
    response = call_elasticsearch(url, cluster_details)
    if response.ok:
        try:
            index_response = (
                list(response.json().values())[0]['settings']['index']['routing']['allocation']['include']['data'])
        except KeyError:
            logging.info("Using Default Index_Response => HOT")
            index_response = "hot"
        if index_response == 'hot':
            index_state, state_level_metadata = check_index_aliases_state(index_name,
                                                                          create_elasticsearch_url(cluster_details),
                                                                          cluster_details)
            return index_state, state_level_metadata
        else:
            index_state = check_index_smw_state(index_name, create_elasticsearch_url(cluster_details))
            return index_state, {"op_complete": False}
    else:
        logging.info(f'Error in checking allocation state for {index_name} {response.text}')
        return "DELETED", {"Error_Encountered": 'Index_Not_Found'}


def create_index_lifecycle_model():
    index_models = get_details_from_db(query="select * from elasticsearch_index",
                                       database_name="elasticsearch_manager")
    for index_model in index_models:
        datasource = get_details_from_db(query=f"select * from elasticsearch_datasource where id={index_model[9]}",
                                         database_name="elasticsearch_manager")[0]
        current_state, state_level_metadata = check_index_allocation_state(index_name=index_model[1],
                                                                           datasource_cluster_id=datasource[8])
        if current_state == "DELETED":
            logging.info(f"Current state for {index_model[1]} is deleted, check above logs for debug ")
        else:

            insert_query = "INSERT INTO elasticsearch_index_lifecycle (create_timestamp,update_timestamp,index_id," \
                           "current_state,next_possible_states,state_level_metadata) VALUES (%s,%s,%s,%s,%s,%s)"

            values = (datetime.now(), datetime.now(), index_model[0], current_state, "", state_level_metadata)
            logging.info(f"SQL Command :- {insert_query} {values}")
            # insert_data_into_db(insert_query, values)


if __name__ == '__main__':
    # migrate_escluster_to_elasticsearch_cluster(sys.argv[1], sys.argv[2], sys.argv[3])
    # migrate_datasource_to_elasticsearch_datasource()
    # create_index_model()
    create_index_lifecycle_model()
