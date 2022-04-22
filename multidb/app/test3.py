from .models import *
import json
import sys
import requests
import logging
import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="{asctime} {levelname:<10} {message}",
    style='{')
logging.getLogger(__name__)


def connect_to_db():
    connection = psycopg2.connect(
        host="localhost",
        database="snappyflow",
        user="snappyflow",
        password="maplelabs")
    cursor = connection.cursor()
    return cursor


def get_all_esCluster():
    cursor = connect_to_db()
    get_all_esCluster = "select * from application_escluster"
    cursor.excute(get_all_esCluster)
    es_clusters = cursor.fetchall()
    return es_clusters


def migrate_escluster_to_elasticsearch_cluster(URL, AUTH_TOKEN, OperatingMode):
    # esClusters = ESCluster.objects.all().using('snappyflow')
    esClusters = get_all_esCluster()
    for esCluster in esClusters:
        payload = json.dumps({
            "name": esCluster.name,
            "host": esCluster.host,
            "port": esCluster.port,
            "username": esCluster.username,
            "password": esCluster.password,
            "force_cleanup": esCluster.force_cleanup,
            "system_created": esCluster.system_created,
            "operating_mode": OperatingMode,
        })
        headers = {
            'Authorization': AUTH_TOKEN,
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", URL + "/es-manager/cluster", headers=headers, data=payload)
        if response.ok:
            logging.info("Es cluster with name {} created successfully {}".format(esCluster.name, response.text))
        else:
            logging.error("Es cluster with name {} creation failed {}".format(esCluster.name, response.text))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error('specify the URL , Auth_Token and OperatingMode')
    else:
        migrate_escluster_to_elasticsearch_cluster(sys.argv[1], sys.argv[2], sys.argv[3])
