import json
import sys
import logging
from datetime import datetime
import time
from requests.auth import HTTPBasicAuth

import requests
import psycopg2

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
        logging.debug(f"Connection to database {database_name} is successful")
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
            return cluster_model
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

        insert_query = "INSERT INTO elasticsearch_datasource (create_timestamp,update_timestamp,name,type," \
                       "parent_type,parent_id," \
                       "shard_count_template,cluster_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);"
        values = (
            datetime.now(), datetime.now(), datasource[1], datasource_type, parent_type, parent_id,
            shard_count_template,
            cluster_id[0])

        logging.info(f"SQL Command :- {insert_query} {values}")
        insert_data_into_db(insert_query, values)

    logging.info("Migration of datasource to elasticsearch_datasource completed successfully ")


# MIGRATION OF ELASTICSEARCH INDEX

def epochtime_to_datetime(epoch_timestamp):
    timestamp = int(epoch_timestamp) / 1000.0
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def create_elasticsearch_url(cluster_details):
    es_url = "http://" + cluster_details[5] + ":" + str(cluster_details[6]) + "/"
    return es_url


def connect_to_elasticsearch(es_index_name, cluster_details):
    es_query = '?h=index,creation.date,docs.count,pri.store.size,store.size&format=json&pretty&bytes=b'
    url = create_elasticsearch_url(cluster_details) + '_cat/indices/' + es_index_name + es_query
    response = requests.request("GET", url, auth=HTTPBasicAuth(cluster_details[8], cluster_details[9]))
    if response.ok:
        return response.json()[0]
    else:
        logging.error(f'Failed to connect to server {url} reason {response.text}')
        return {'lag': False, 'docs.count': 0, 'pri.store.size': 0, 'store.size': 0}


def generate_write_phase_details(es_index_metadata):
    fmt = '%Y-%m-%d %H:%M:%S'
    indices_creation_time = []
    es_index_write_phase_details = {}
    for index_name in list(es_index_metadata):
        indices_creation_time.append(epochtime_to_datetime(es_index_metadata[index_name]['creationTime']))
    for i in range(len(indices_creation_time)):
        if i < len(indices_creation_time) - 1:
            td = datetime.strptime(indices_creation_time[i + 1], fmt) - datetime.strptime(indices_creation_time[i], fmt)
            data = {list(es_index_metadata)[i]: {"diff_sec": int(round(td.total_seconds()))}}
        else:
            current_time = epochtime_to_datetime(int(time.time() * 1000))
            td = datetime.strptime(current_time, fmt) - datetime.strptime(indices_creation_time[i], fmt)
            data = {list(es_index_metadata)[i]: {"diff_sec": int(round(td.total_seconds()))}}
        es_index_write_phase_details.update(data)
    return es_index_write_phase_details


def populate_index_model(index_metadata, datasource_name):
    datasource = generate_foreign_key(table_name="elasticsearch_datasource", cluster_name=datasource_name)
    cluster_details = get_details_from_db(query=f"select * from elasticsearch_cluster where id={datasource[8]}",
                                          database_name="elasticsearch_manager")[0]
    if index_metadata == 'Null':
        logging.info(f"index_metadata is empty for {datasource_name} check elasticsearch_datasource db")
    else:
        for es_index in list(index_metadata):
            index_details = connect_to_elasticsearch(es_index, cluster_details)
            write_phase_details = generate_write_phase_details(index_metadata)

            insert_query = "INSERT INTO elasticsearch_index (create_timestamp,update_timestamp,datasource_id,name," \
                           "creation_time_on_es,first_record_time,last_record_time,data_lag,doc_count," \
                           "primary_store_size_bytes,store_size_bytes,write_phase_in_seconds) VALUES (%s,%s,%s,%s,%s," \
                           "%s,%s,%s,%s,%s,%s,%s) "

            values = (datetime.now(), datetime.now(), datasource[0], es_index,
                      epochtime_to_datetime(index_metadata[es_index]['creationTime']),
                      epochtime_to_datetime(index_metadata[es_index]['firstDocTime']),
                      epochtime_to_datetime(index_metadata[es_index]['lastDocTime']), index_metadata[es_index]['lag'],
                      int(index_details['docs.count']), int(index_details['pri.store.size']),
                      int(index_details['store.size']), write_phase_details[es_index]['diff_sec'])

            logging.info(f"SQL Command :- {insert_query} {values}")
            insert_data_into_db(insert_query, values)


def create_index_model():
    datasources = get_details_from_db(query="select * from datasource",
                                      database_name="snappyflow")
    for datasource in datasources:
        if datasource[14] is None:
            populate_index_model('Null', datasource[1])
        else:
            populate_index_model(datasource[14], datasource[1])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error('specify the URL , Auth_Token and OperatingMode')
    else:
        # migrate_escluster_to_elasticsearch_cluster(sys.argv[1], sys.argv[2], sys.argv[3])
        #migrate_datasource_to_elasticsearch_datasource()
        create_index_model()
