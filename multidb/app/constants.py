from django.db import models

class ClusterConstants(object):
    """
    All constants related to the elasticsearch cluster itself
    """
    class ConnectivityStatus(models.TextChoices):
        """
        Represents the connectivity status to an elasticsearch status
        A socket connection is made to the cluster and it can either be offline or online
        """
        ONLINE = "Online"
        OFFLINE = "Offline"

    class State(models.TextChoices):
        """
        Represents an elasticsearch cluster's status as reported by Elasticsearch itself
        Call to /_cluster/stats gives the cluster's status. It can be red, green or yello
        """
        RED = "red"
        YELLOW = "yellow"
        GREEN = "green"

    class Version(models.TextChoices):
        """
        Represents all elasticsearch versions we support. Currently 6.x and 7.x
        """
        ES6 = "es_6x"
        ES7 = "es_7x"
        UNKNOWN = "unknown"

    class OperatingModes(models.TextChoices):
        """
        Represents all modes elasticsearch can operate. This determines indices' ILM, celery tasks to use etc.
        """
        HOT_ONLY = "hot"
        HOT_OPTIMIZED = "hot_optimized"
        HOT_WARM = "hot_warm"


class DatasourceConstants(object):
    """
    This is much similar to elasticsearch's datastreams concept.
    Only difference is that we're managing the ILM of underlying indices
    This class represents all related constants
    """

    class Types(models.TextChoices):
        """
        Represents all types of ES datasources that snappyflow currently uses
        """
        LOG = "logger"
        METRIC = "metric"
        TRACE = "stacktrace"
        PROFILING = "profile"
        MANAGEMENT = "control"

    class ParentTypes(models.TextChoices):
        """
        Represents all types of parent types a datasources can have
        """
        PROJECT = "project"
        ACCOUNT = "account"
        PROFILE = "profile"


class IndexConstants(object):
    """
    All constants related to an elasticsearch index
    """
    class States(models.TextChoices):
        CREATED = "CURRENT"
        ROLLED = "ROLLED-OVER"
        WARMED = "MOVED-TO-WARM"
        PURGED = "PURGED"
        MERGED = "MERGED"
        SHRINKED = "SHRINKED"
        BACKED_UP = "BACKED-UP"
        DELETED = "DELETED"
        SHRINK_CREATED = "SHRINK_CREATED"
        BACKUP_DELETED = "BACKUP_DELETED"
        ROLLED_AND_BACKED_UP = "ROLLED/BACKED-UP"
        MERGED_AND_BACKED_UP = "MERGED/BACKED-UP"
        DELETED_AND_BACKED_UP = "DELETED/BACKED-UP"
        RESTORED_AND_BACKED_UP = "RESTORED/BACKED-UP"
        RESTORED = "RESTORED"
