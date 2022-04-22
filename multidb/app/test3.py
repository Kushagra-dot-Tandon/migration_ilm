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
        cursor = connection.cursor()
        logging.info("Connection successful")
        return cursor, error
    except Exception as err:
        error = True
        logging.error("Connection failed {}".format(err))
        return "", error


def get_details_from_db(query, database_name):
    cursor, error = connect_to_db(database_name)
    if not error:
        cursor.execute(query)
        es_clusters = cursor.fetchall()
        return es_clusters
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


def get_parent_details(cluster):
    print(cluster[4])
    # if 'project_id' in cluster.config:
    #     return 0, DatasourceConstants.ParentTypes.PROJECT
    # elif cluster.datasource_name.split("-")[0] in ["control", "profile", "trace"]:
    #     return 0, DatasourceConstants.ParentTypes.PROFILE
    # else:
    #     parent_id = get_parent_id_from_accounts(
    #         cluster.id, cluster.datasource_name.split("-")[0])
    #     return parent_id, DatasourceConstants.ParentTypes.ACCOUNT

def migrate_datasource_to_elasticsearch_datasource():
    datasources = get_details_from_db(query="select * from datasource", database_name="snappyflow")
    for datasource in datasources:
        parent_id, parent_type = get_parent_details(cluster=datasource)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error('specify the URL , Auth_Token and OperatingMode')
    else:
        migrate_escluster_to_elasticsearch_cluster(sys.argv[1], sys.argv[2], sys.argv[3])
