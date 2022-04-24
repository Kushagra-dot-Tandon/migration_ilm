import json
import sys
import logging
import requests
import psycopg2
from .constants import *

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


def migrate_escluster_to_elasticsearch_cluster(URL, AUTH_TOKEN, OperatingMode):
    esClusters = get_details_from_db(query="select * from application_escluster", database_name="snappyflow")
    for esCluster in esClusters:
        payload = json.dumps({
            "name": esCluster[1],
            "host": esCluster[2],
            "port": esCluster[3],
            "username": esCluster[5],
            "password": esCluster[6],
            "force_cleanup": esCluster[10],
            "system_created": esCluster[11],
            "operating_mode": OperatingMode,
        })
        headers = {
            'Authorization': AUTH_TOKEN,
            'Content-Type': 'application/json'
        }
        print(payload)
        response = requests.request("POST", URL + "/es-manager/cluster", headers=headers, data=payload, verify=False)
        if response.ok:
            logging.info("Es cluster with name {} created successfully {}".format(esCluster[1], response.text))
        else:
            logging.error("Es cluster with name {} creation failed {}".format(esCluster[1], response.text))

# MIGRATION OF DATASOURCE TO ELASTICSEARCH DATASOURCE STARTS HERE ;

def generate_foreign_key(table_name, cluster_name):
    connection, error = connect_to_db(database_name="elasticsearch_manager")
    cursor = connection.cursor()
    if not error:
        query = f"Select * from {table_name} where name like %s"
        try:
            cursor.execute(query, (cluster_name,))
            cluster_model = cursor.fetchone()
            return cluster_model[0]
        except Exception as err:
            logging.error(f"Error in generating foreign key for table {table_name} , {cluster_name} with error {err}")
    else:
        sys.exit(1)


def get_parent_id_from_accounts(cluster_id, cluster_name):
    accounts = get_details_from_db(query="select * from accounts", database_name="snappyflow")
    for account in accounts:
        if cluster_name == 'log':
            if account[5]['log_datasource_id'] == cluster_id:
                return account.id
        else:
            if account[5]['datasource_id'] == cluster_id:
                return account.id


def get_parent_details(cluster):
    if 'project_id' in cluster[4]:
        return 0, "project"
    elif cluster[1].split("-")[0] in ["control", "profile", "trace"]:
        return 0, "profile"
    else:
        parent_id = get_parent_id_from_accounts(
            cluster[0], cluster[1].split("-")[0])
        return parent_id, "account"


def insert_data_into_db(insert_query, values):
    connection, error = connect_to_db(database_name="elasticsearch_manager")
    if not error:
        cursor = connection.cursor()
        try:
            cursor.execute(insert_query, values)
            connection.commit()
            cursor.close()
        except Exception as err:
            logging.error(f"Error while executing query error - {err}")
    else:
        sys.exit(1)


def migrate_datasource_to_elasticsearch_datasource():
    datasources = get_details_from_db(query="select * from datasource", database_name="snappyflow")
    for datasource in datasources:
        # populating the details to fill to elasticsearch_datasource database
        parent_id, parent_type = get_parent_details(cluster=datasource)
        datasource_type = "control" if datasource[4]['store_type'] == 'metric' and parent_type == "profile" else \
            datasource[4][
                'store_type']
        shard_count_template = json.dumps({"primary_count": 3, "replica_count": 1}, indent=3)
        cluster_id = generate_foreign_key(table_name="elasticsearch_cluster",
                                          cluster_name=datasource[4]['escluster_name'])

        insert_query = "INSERT INTO elasticsearch_datasource (name,type,parent_type,parent_id," \
                       "shard_count_template,cluster_id) VALUES (%s,%s,%s,%s,%s,%s) "
        values = (datasource[1], datasource_type, parent_type, parent_id, shard_count_template, cluster_id)

        logging.info(f"SQL Command :- {insert_query} with {values}")
        insert_data_into_db(insert_query, values)
    logging.info("Migration of datasource to elasticseach_datasource completed successfully ")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error('specify the URL , Auth_Token and OperatingMode')
    else:
        migrate_escluster_to_elasticsearch_cluster(sys.argv[1], sys.argv[2], sys.argv[3])
        migrate_datasource_to_elasticsearch_datasource()
