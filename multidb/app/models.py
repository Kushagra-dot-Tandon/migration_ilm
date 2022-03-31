from django.db import models
from jsonfield import JSONField
from .constants import *
from django.contrib.postgres.fields import ArrayField

from django.db import models
from jsonfield import JSONField
from django_extensions.db.fields import (
    RandomCharField
)
from .fields import EncryptedValueJsonField


# ILM DATABASE - ELASTIC_SEARCH
import datetime
from django.contrib.postgres.fields import ArrayField

class ClusterModel(models.Model):
    """
    model for Elasticsearch Clusters
    """
    id = models.AutoField(primary_key=True)

    create_timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    update_timestamp = models.DateTimeField(auto_now=True, blank=True)

    name = models.CharField(unique=True, max_length=128)

    version = models.CharField(max_length=20, null=False)

    host = models.CharField(max_length=20)
    port = models.IntegerField()
    protocol = models.CharField(max_length=128, default='http')

    username = models.CharField(max_length=128, null=True)
    password = EncryptedTextField(max_length=128, null=True)

    force_cleanup = models.BooleanField(default=True)
    system_created = models.BooleanField(default=False)

    connectivity_status = models.CharField(max_length=120, choices=ClusterConstants.ConnectivityStatus.choices)
    cluster_status = models.CharField(max_length=120, choices=ClusterConstants.State.choices)
    operation_mode = models.CharField(max_length=120, choices=ClusterConstants.OperatingModes.choices)

    metadata = models.JSONField(default=dict)
    latest_store_details = models.JSONField(default=dict)

    backup_enabled = models.BooleanField(default=True)
    backup_bucket_name = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        db_table = 'elasticsearch_cluster'

    def convert_to_dict(self) -> dict:
        """
        This function helps to convert model object to hashmap format which UI understands
        """
        cluster_details = {
            "id": self.pk,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "username": self.username,
            # Encrypt the password because this function is usually called when es details are being sent to UI etc.
            "password": crypt_utils.encrypt_value(self.password) if self.password else self.password,
            "summary": {
                "status": self.cluster_status,
                "indices": {
                    "docs": {
                        "count": self.latest_store_details["num_docs"],
                        "deleted": self.latest_store_details["num_deleted_docs"]
                    },
                    "count": self.latest_store_details["num_indices"],
                    "store": {
                        "size_in_bytes": self.latest_store_details["store_size_bytes"],
                        "store_size_bytes_reserved": self.latest_store_details["num_indices"]
                    }
                },
                "version": self.version,
                "cluster_name": self.metadata["cluster_name"]
            },
            "status": self.connectivity_status,
            "force_cleanup": self.force_cleanup,
            "system_created": self.system_created,
            "backup_enabled": self.backup_enabled,
            "backup_bucket_name": self.backup_bucket_name,
            "operating_mode": self.operation_mode,
            "apm_port": self.metadata['apm_port'],
            "jaeger_port": self.metadata['jaeger_port']
        }

        return cluster_details

    def get_elasticsearch_client(self):
        """
        This function helps to mimic a singleton class behaviour i.e., for each model of elasticsearch, we must create
        only 1 client via this function
        """
        if "client" in self.__dict__:
            return self.client

        auth_tuple = ()

        if self.username:
            auth_tuple = auth_tuple + (self.username,)
        if self.password:
            auth_tuple = auth_tuple + (self.password,)

        if get_major_version(str(self.version)) == ClusterConstants.Version.ES6:

            if self.protocol == "https":

                self.client: Elasticsearch6 = Elasticsearch6(["{}:{}".format(self.host, self.port)], use_ssl=True,
                                                             verify_certs=False, scheme="https", http_auth=auth_tuple,
                                                             connection_class=RequestsHttpConnection6, timeout=45)

            else:

                self.client: Elasticsearch6 = Elasticsearch6(["{}:{}".format(self.host, self.port)], timeout=45,
                                                             http_auth=auth_tuple)

        else:

            if self.protocol == "https":

                self.client: Elasticsearch7 = Elasticsearch7(["{}:{}".format(self.host, self.port)], use_ssl=True,
                                                             verify_certs=False, scheme="https", http_auth=auth_tuple,
                                                             connection_class=RequestsHttpConnection7, timeout=45)
            else:

                self.client: Elasticsearch7 = Elasticsearch7(["{}:{}".format(self.host, self.port)], timeout=45,
                                                             http_auth=auth_tuple)

        return self.client


class DatasourceModel(models.Model):
    """
    model for Elasticsearch Datasources
    This is much similar to https://www.elastic.co/guide/en/elasticsearch/reference/master/data-streams.html
    But ILM etc. is managed by snappyflow. We ought to consider to use ES ILM whenever possible
    """
    id = models.AutoField(primary_key=True)

    create_timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    update_timestamp = models.DateTimeField(auto_now=True, blank=True)

    name = models.CharField(unique=True, max_length=128)

    type = models.CharField(max_length=200,
                            choices=DatasourceConstants.Types.choices)

    parent_type = models.CharField(max_length=200, choices=DatasourceConstants.ParentTypes.choices)
    parent_id = models.CharField(max_length=20)

    cluster = models.ForeignKey(ClusterModel, on_delete=models.CASCADE)

    shard_count_template = models.JSONField(default=dict)

    class Meta:
        db_table = 'elasticsearch_datasource'


class IndexModel(models.Model):
    """
    Elasticsearch index model class which holds all ES indices info and other metadata that we needed
    e.g. boundary-timestamps etc.
    Size etc.
    """
    id = models.AutoField(primary_key=True)

    create_timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    update_timestamp = models.DateTimeField(auto_now=True, blank=True)
    delete_timestamp = models.DateTimeField(null=True)

    datasource = models.ForeignKey(DatasourceModel, on_delete=models.CASCADE)

    name = models.CharField(unique=True, max_length=400)

    creation_time_on_es = models.DateTimeField(help_text="Timestamp when index was created in elasticsearch")

    first_record_time = models.DateTimeField(help_text="Minimum value of record timestamp in whole index. "
                                                       "Helps to consider an index during time based queries")
    last_record_time = models.DateTimeField(help_text="Maximum value of record timestamp in whole index. "
                                                      "Helps to consider an index during time based queries")
    data_lag = models.BooleanField(default=False,
                                   help_text="Indicates wether index consists of data that arrived with a lag")

    doc_count = models.PositiveBigIntegerField(default=0)
    primary_store_size_bytes = models.PositiveBigIntegerField(default=0)
    store_size_bytes = models.PositiveBigIntegerField(default=0)

    write_phase_in_seconds = models.PositiveBigIntegerField(default=1,
                                                            help_text="Number of seconds spent in write phase")

    class Meta:
        db_table = 'elasticsearch_index'

    def hard_delete(self):
        """
        This function is meant to be used when you want this index and its lifecycle to get deleted from DB itself
        """
        self.delete()

    def soft_delete(self):
        """
        This function is meant to be used when you want to soft delete this index
        i.e., mark it as deleted but retain in DB
        This is needed in order to show state of index as DELETED/BACKED-UP etc.
        Also needed to retain indices in DB for 2 months for debugging purposes
        """
        self.delete_timestamp = datetime.datetime.now(datetime.timezone.utc)
        self.save(update_fields=['delete_timestamp', 'update_timestamp'])

    def revive(self):
        """
        This function is meant to be used when you want to restore this index
        """
        self.delete_timestamp = None
        self.save(update_fields=['delete_timestamp', 'update_timestamp'])


class IndexLifecycleModel(models.Model):
    """
    Elasticsearch index lifecycle model represents the lifecyce of all indices in our system
    """
    ALL_POSSIBLE_STATES = [IndexConstants.States.CREATED, IndexConstants.States.ROLLED, IndexConstants.States.WARMED,
                           IndexConstants.States.PURGED, IndexConstants.States.MERGED, IndexConstants.States.RESTORED,
                           IndexConstants.States.MERGED_AND_BACKED_UP, IndexConstants.States.DELETED_AND_BACKED_UP,
                           IndexConstants.States.RESTORED_AND_BACKED_UP]

    id = models.AutoField(primary_key=True)

    create_timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    update_timestamp = models.DateTimeField(auto_now=True, blank=True)

    index = models.ForeignKey(IndexModel, on_delete=models.CASCADE)

    current_state = models.CharField(max_length=200, choices=IndexConstants.States.choices)
    next_possible_states = ArrayField(models.CharField(max_length=100), size=5, blank=True, default=list)
    state_level_metadata = models.JSONField(null=True, default=dict)

    class Meta:
        db_table = 'elasticsearch_index_lifecycle'



# SNAPPYFLOW DATABASE USED FOR MIGRATION TO ILM DATABASE


# Create your models here.
class ESCluster(models.Model):
    """
    model for ES Cluster
    """
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, max_length=128)
    host = models.TextField()
    port = models.IntegerField()
    apm_port = models.IntegerField(null=True)
    jaeger_port = models.IntegerField(null=True)
    username = models.TextField(max_length=128, null=True)
    password = models.TextField(max_length=128, null=True)
    protocol = models.TextField(default='http')
    summary = JSONField(default={})
    status = models.TextField(default="Online")
    force_cleanup = models.BooleanField(default=True)
    system_created = models.BooleanField(default=False)

    class Meta:
        db_table = 'escluster'


class Datasource(models.Model):
    """
    Datasource model class
    """
    id = RandomCharField(length=10, primary_key=True)
    datasource_name = models.CharField(unique=True, max_length=255)
    type = models.TextField(null=True)
    default_ds = models.BooleanField(default=True)
    config = JSONField(null=True)
    connectivity = models.TextField(default="InProgress")
    isUsed = models.BooleanField(default=False)
    endpoints = JSONField(default=[])
    start_time_for_deletion_of_livedata = models.PositiveIntegerField(null=True)
    owner = models.TextField(null=True)
    public_access = models.TextField(null=True)
    indices_list = JSONField(null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_es_time = models.TextField(null=True, default="0")
    indices_metadata = JSONField(null=True)

    class Meta:
        db_table = 'datasource'


class Account(models.Model):
    """
    Account model for application
    """
    # id = RandomCharField(length=10, primary_key=True)
    id = models.AutoField(primary_key=True)
    acc_type = models.TextField(null=True)
    acc_name = models.TextField()
    credential = JSONField(null=True)
    acc_details = EncryptedValueJsonField(null=True)
    status = models.TextField(default="InActive")
    isActiveMonitoring = models.BooleanField(default=False)
    preferences = JSONField(null=True)
    billing = JSONField(null=True)
    owner = models.TextField(null=True)
    public_access = models.TextField(null=True)
    provision = models.BooleanField(default=True)
    monitor = models.BooleanField(default=False)
    visualization_template = models.TextField(null=True)
    notification = JSONField(null=True, default={})
    auto_discovery = models.BooleanField(default=False)
    cloudprofile_id = models.TextField(null=True)
    alerts = JSONField(null=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True)
    license = models.CharField(max_length=64, null=True)

    class Meta:
        db_table = 'accounts'
