from .models import *
import requests
from requests.auth import HTTPBasicAuth
# from elasticsearch_manager.cluster_ops import ClusterOperations
# from elasticsearch_manager.possible_state_transitions import get_possible_state_transitions

def migrate_escluster_to_elasticsearch_cluster():
    esClusters = ESCluster.objects.all().using('snappyflow')
    for esCluster in esClusters:
        if ClusterModel.objects.using('local').filter(name=esCluster.name).exists():
            print("Already Exists")
        else:
            cluster_summary, error = ClusterOperations(
                ClusterModel(name=esCluster.name, host=esCluster.host, port=esCluster.port,
                             username=esCluster.username, password=esCluster.password, protocol=esCluster.protocol,
                             version="6.8.0")).get_cluster_summary()
            print(cluster_summary, error)
            clustermodel = ClusterModel.objects.create(
                name=esCluster.name,
                host=esCluster.host,
                port=esCluster.port,
                protocol=esCluster.protocol,
                username=esCluster.username,
                password=esCluster.password,
                force_cleanup=esCluster.force_cleanup,
                system_created=esCluster.system_created,
                connectivity_status=ClusterConstants.ConnectivityStatus.ONLINE if esCluster.status == "Online" else ClusterConstants.ConnectivityStatus.OFFLINE,
                version=cluster_summary['nodes']['versions'][0],
                cluster_status=esCluster.summary['status'],
                backup_enabled=False,
                operation_mode=ClusterConstants.OperatingModes.HOT_ONLY,
                metadata={"apm_port": esCluster.apm_port, "jaeger_port": esCluster.jaeger_port,
                          "cluster_name": esCluster.summary['cluster_name']},
                latest_store_details={
                    "num_indices": cluster_summary["indices"]["count"],
                    "num_primary_shards": cluster_summary["indices"]["shards"]["primaries"],
                    "num_total_shards": cluster_summary["indices"]["shards"]["total"],
                    "num_docs": cluster_summary["indices"]["docs"]["count"],
                    "num_deleted_docs": cluster_summary["indices"]["docs"]["deleted"],
                    "store_size_bytes": cluster_summary["indices"]["store"]["size_in_bytes"],
                    "store_size_bytes_reserved": cluster_summary["indices"]["store"].get("reserved_in_bytes", 0)
                }
            )
            clustermodel.save(using='local')
        print("Migration to escluster to elasticsearch_cluster completed successfully")





def generate_foregin_cluster_id(cluster_name):
    esClusters = ClusterModel.objects.using("local").get(name=cluster_name)
    return esClusters.id


def get_parent_id_from_accounts(cluster_id, cluster_name):
    accounts = Account.objects.all().using('snappyflow')
    for account in accounts:
        if cluster_name == 'log':
            if account.acc_details['log_datasource_id'] == cluster_id:
                return account.id
        else:
            if account.acc_details['datasource_id'] == cluster_id:
                return account.id


def get_parent_details(cluster):
    # print(cluster.config)
    if 'project_id' in cluster.config:
        return 0, DatasourceConstants.ParentTypes.PROJECT
    elif cluster.datasource_name.split("-")[0] in ["control", "profile", "trace"]:
        return 0, DatasourceConstants.ParentTypes.PROFILE
    else:
        parent_id = get_parent_id_from_accounts(
            cluster.id, cluster.datasource_name.split("-")[0])
        return parent_id, DatasourceConstants.ParentTypes.ACCOUNT


def migrate_datasource_to_elasticsearch_datasource():
    datasources = Datasource.objects.all().using("snappyflow")
    for datasource in datasources:
        parent_id, parent_type = get_parent_details(cluster=datasource)
        type = datasource.config['store_type']
        datasourceModel = DatasourceModel.objects.create(
            name=datasource.datasource_name,
            type=DatasourceConstants.Types.MANAGEMENT if type == 'metric' and parent_type == DatasourceConstants.ParentTypes.PROFILE else type,
            parent_type=parent_type,
            parent_id=parent_id,
            shard_count_template={"primary_count": 3, "replica_count": 1},
            cluster_id=generate_foregin_cluster_id(
                datasource.config['escluster_name']),
        )
        datasourceModel.save(using='local')
    print('Migration of datasource to elasticsearch_datasource completed successfull')


def convert_epochtime(epoch_timestamp):
    timestamp = int(epoch_timestamp) / 1000.0
    return (datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f'))[:-3]


def create_elasticsearch_url(cluster_details):
    es_url = "http://" + cluster_details.host + ":" + str(cluster_details.port) + "/"
    return es_url


def connect_to_elasticsearch(indice_name, cluster_details):
    es_query = '?h=index,creation.date,docs.count,pri.store.size,store.size&format=json&pretty&bytes=b'
    url = create_elasticsearch_url(cluster_details) + '_cat/indices/' + indice_name + es_query
    response = requests.request("GET", url, auth=HTTPBasicAuth(cluster_details.username, cluster_details.password))
    if response.ok:
        return response.json()[0]
    else:
        return {'lag': False, 'docs.count': 0, 'pri.store.size': 0, 'store.size': 0}


def create_indexModel(indices_metadata, datasource_name):
    datasource = DatasourceModel.objects.using('local').get(name=datasource_name)
    cluster_details = ClusterModel.objects.using('local').get(id=datasource.cluster_id)
    if indices_metadata == 'Null':
        print("null field encountered , rejecting")
    else:
        for indice in list(indices_metadata):
            indice_detail = connect_to_elasticsearch(indice, cluster_details)
            index_model = IndexModel.objects.create(
                datasource_id=datasource.id,
                name=indice,
                creation_time_on_es=convert_epochtime(indices_metadata[indice]['creationTime']),
                first_record_time=convert_epochtime(indices_metadata[indice]['firstDocTime']),
                last_record_time=convert_epochtime(indices_metadata[indice]['lastDocTime']),
                data_lag=indices_metadata[indice]['lag'],
                doc_count=int(indice_detail['docs.count']),
                primary_store_size_bytes=int(indice_detail['pri.store.size']),
                store_size_bytes=int(indice_detail['store.size'])
            )
            index_model.save(using='local')

# Function to Create IndexModel
def migrate_indexModel():
    datasources = Datasource.objects.all().using('snappyflow')
    for datasource in datasources:
        if datasource.indices_metadata == None:
            create_indexModel('Null', datasource.datasource_name)
        else:
            create_indexModel(datasource.indices_metadata, datasource.datasource_name)
    print("Creation of indexModel done successfully")




# Function to call elasticsearch
def call_elasticsearch(url, cluster_details):
    response = requests.request("GET", url, auth=HTTPBasicAuth(cluster_details.username, cluster_details.password))
    return response


# Function to check if the index is having read_write aliases
def check_shards_count(index_name: str, ElasticSearch_URL, cluster_details) -> int:
    url = ElasticSearch_URL + index_name + '_settings'
    response = call_elasticsearch(url, cluster_details)
    if response.ok:
        return int(list(response.json().values())[0]['settings']['index']['number_of_shards'])
    else:
        print('Error in checking %s shards count', index_name)


# Function to check if the particular index is Merged , Shrinked , Warm
def check_index_smw_state(index_name: str, ElasticSearch_URL, cluster_details) -> IndexConstants.States:
    url = ElasticSearch_URL + index_name + '_cat/segments'
    response = call_elasticsearch(url, cluster_details)
    if response.ok:
        if len(response.json()) == 2:
            return IndexConstants.States.MERGED
        elif check_shards_count(index_name, ElasticSearch_URL) == 1:
            # TODO: check the state of index => shrinking or done etc.
            # check_shrinking_index_status(index_name)=> _cat/shards(2) => started
            return IndexConstants.States.SHRINKED
        else:
            return IndexConstants.States.WARMED
    else:
        print('Error in checking if particular index %s is merged , shrinked or warm', index_name)
        raise Exception

# Function to check Index Aliases States
def check_index_aliases_state(index_name: str, ElasticSearch_URL, cluster_details) -> IndexConstants.States:
    url = ElasticSearch_URL + index_name
    response = call_elasticsearch(url, cluster_details)
    if response.ok:
        index_res = list(list(response.json().values())[0]['aliases'].keys())
        if len(index_res) == 2:
            return IndexConstants.States.CREATED, {"op_complete": True}
        else:
            return IndexConstants.States.ROLLED, {"op_complete": True}
    else:
        print('Error in checking %s index_name aliases state', index_name)
        raise Exception


# Function to check if particular index is HOT or WARM
def check_index_allocation_state(index_name: str, elasticsearch_info) -> IndexConstants.States:
    cluster_details = ClusterModel.objects.get(id=elasticsearch_info)
    ElasticSearch_URL = "http://" + cluster_details.host + ":" + str(cluster_details.port) + "/"
    url = ElasticSearch_URL + index_name + '/_settings'
    print(url)
    response = call_elasticsearch(url, cluster_details)
    if response.ok:
        try:
            index_response = (
            list(response.json().values())[0]['settings']['index']['routing']['allocation']['include']['data'])
        except KeyError:
            print("default")
            index_response = "hot"
        if index_response == 'hot':
            index_state, state_level_metadata = check_index_aliases_state(index_name, ElasticSearch_URL,
                                                                          cluster_details)
            return index_state, state_level_metadata
        else:
            index_state = check_index_smw_state(index_name, ElasticSearch_URL)
            return index_state, {"op_complete": False}
    else:
        print('Error in checking index_state %s response_body %s', index_name)
        return IndexConstants.States.DELETED, {"Error_Encountered": 'Index_Not_Found'}

# Function to create IndexLifecycleModel 
def migrate_index_lifecycle_model():
    index_models = IndexModel.objects.all().using('local')
    for index_model in index_models:
        datasource = DatasourceModel.objects.using('local').get(id=index_model.datasource_id)
        current_state, state_level_metadata = check_index_allocation_state(index_name=index_model.name,
                                                                           elasticsearch_info=datasource.cluster_id)
        if current_state == IndexConstants.States.DELETED:
            print('Error')
        else:
            index_lifecycle_model = IndexLifecycleModel.objects.create(
                index=index_model,
                current_state=current_state,
                next_possible_states=get_possible_state_transitions("hot", False, datasource.type)[current_state],
                state_level_metadata=state_level_metadata
            )
            index_lifecycle_model.save(using='local')




if __name__ == "__main__":
    migrate_escluster_to_elasticsearch_cluster()
    migrate_datasource_to_elasticsearch_datasource()
    migrate_indexModel()
    migrate_index_lifecycle_model()