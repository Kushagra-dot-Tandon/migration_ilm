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
        # Below segment indicates the end states that index can go into
        CREATED = "CURRENT"  # Index in in Read-Write mode
        SHRINK_CREATED = "CREATED_BY-SHRINK"  # Index came into life by cloning + shrinking from some other index
        SHRINKED = "SHRINK_ENABLED_CLONE"  # Index is being cloned + shrinked. This operation results in a new index
        ROLLED = "ROLLED-OVER"  # Index is in Read mode
        WARMED = "MOVED-TO-WARM"  # Index has been moved to warm node as it isn't being queried much
        PURGED = "PURGED"  # Index has been deleted from entire system i.e., backup has been deleted as well
        MERGED = "MERGED"  # Index has been merged i.e., Segments have been reduced to 2 or 3
        ROLLED_AND_BACKED_UP = "ROLLED/BACKED-UP"  # Index is in Read mode and it's snapshot has been taken
        MERGED_AND_BACKED_UP = "MERGED/BACKED-UP"  # Index has been merged and it's snapshot has been taken
        DELETED_AND_BACKED_UP = "DELETED/BACKED-UP"  # Index has been deleted from cluster but it's snapshot exists
        RESTORED_AND_BACKED_UP = "RESTORED/BACKED-UP"  # Index was restored and it's snapshot still exists
        RESTORED = "RESTORED"  # Index was restored but it's snapshot doesn't exist

        # Below segment indicates the operations that can be performed on an index
        # resultant state's name might be different depending on index's current state
        BACKED_UP = "BACKED-UP"  # Index needs to be backed-up
        DELETED = "DELETED"  # Index needs to be deleted from cluster
        RESTORED_DELETED = "RESTORE_DELETED"  # Restored index needs to be deleted from cluster
        BACKUP_DELETED = "BACKUP_DELETED"  # Snapshot of an index needs to be deleted
        MERGING = "MERGING"  # Index is being merged
        SHRINKING = "SHRINK_ENABLED_CLONING"  # Index is being cloned with shrink option enabled
        BACKING_UP = "BACKING-UP"  # Index is being backed-up
        RESTORING = "RESTORING"  # Index is being RESTORED
        MARKED_FOR_RESTORE = "MARKED_FOR_RESTORE"  # Index has been marked for restore by UI
        WARMING = "MOVING-TO-WARM"  # Index is being moved to warm node

    class ShardStates(models.TextChoices):
        STARTED = "STARTED"
        RELOCATING = "RELOCATING"

    class Alias(models.TextChoices):
        READ_ALIAS_SUFFIX = "_read"
        WRITE_ALIAS_SUFFIX = "_write"


class HotWarmConstants(object):
    """
    All hot-warm related constants
    """

    class Nodes(object):
        ATTR_KEY = "data"
        HOT_ATTR = "hot"
        WARM_ATTR = "warm"

    class Shrink(object):
        SHRINK_SUFFIX = "-shrink"
        MAX_DOC_LIMIT = 2147483519
        POST_OP_SHARD_COUNT = 2

    class Merge(object):
        POST_OP_SEGMENT_COUNT = 2

    class Rules(object):
        WARM_RULE_PATH = '/apps/snappyflow/elasticsearch_manager/core_application/rules/warm_movement.yaml'
        THRESHOLD = "thresholds"
        PRE_REQ = "prerequisites"
        GREATER_THAN = "gt"
        LESSER_THAN = "lt"
        EQUAL = "eq"
        NOT_EQUAL = "neq"
        BOOL = "bool"


class UrlTemplates(object):
    """
    This class comprises of all the URLs that elasticsearch-manager will need while getting info from APM service
    """
    RETENTION_CONFIG = "/internal/escluster/{}/dependents-retention-details"
    USER_PERMITTED_OBJS = "/internal/userdata/{}"
    FETCH_PROJECT_PROFILE_ID = "/internal/projects/{}?getProfileID=True"
    FETCH_ACCOUNT_PROFILE_ID = "/internal/accounts/{}?getProfileID=True"
    USER_ACCESS_TO_PROFILE = "/internal/userdata/{}?profile_id={}"
    USER_ACCESS_TO_PROJECT = "/internal/userdata/{}?project_id={}"
    USER_ACCESS_TO_ACCOUNT = "/internal/userdata/{}?account_id={}"
    LICENSE_VALIDITY = "/internal/license-validation"