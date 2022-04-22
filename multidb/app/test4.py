import sys
import logging
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


def insert_details_to_db(query, database_name):
    cursor, error = connect_to_db(database_name)
    if not error:
        cursor.execute(query)
        cursor.commit()
        cursor.close()
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


def migrate_datasource_to_elasticsearch_datasource():
    datasources = get_details_from_db(query="select * from datasource", database_name="snappyflow")
    for datasource in datasources:
        parent_id, parent_type = get_parent_details(cluster=datasource)
        dstype = datasource[4]['store_type']
        cursor, error = connect_to_db(database_name="elasticsearch_datasource")
        if not error:
            cursor.execute(
                "INSERT TO elasticsearch_datasource (name,type,parent_type,parent_id,shard_count_template,cluster_id) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (datasource[1], "control" if dstype == 'metric' and parent_type == "profile" else dstype,
                 parent_type, parent_id, {"primary_count": 3, "replica_count": 1}
                 ,
                 ))


if __name__ == '__main__':
    migrate_datasource_to_elasticsearch_datasource()
