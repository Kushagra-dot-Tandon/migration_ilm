from constants import ClusterConstants, IndexConstants, DatasourceConstants


def get_possible_state_transitions(operating_mode: str, backup_enabled: bool, ds_type: str):
    """
    This function looks at the mode elasticsearch is operating in along with backup enabled flag and
    captures all possible state transitions
    """
    if operating_mode == ClusterConstants.OperatingModes.HOT_ONLY:

        if backup_enabled:

            return {
                IndexConstants.States.CREATED: [IndexConstants.States.ROLLED],
                IndexConstants.States.ROLLED: [IndexConstants.States.ROLLED_AND_BACKED_UP],
                IndexConstants.States.ROLLED_AND_BACKED_UP: [IndexConstants.States.DELETED_AND_BACKED_UP],
                IndexConstants.States.DELETED_AND_BACKED_UP: [IndexConstants.States.PURGED,
                                                              IndexConstants.States.RESTORED_AND_BACKED_UP],
                IndexConstants.States.RESTORED_AND_BACKED_UP: [IndexConstants.States.RESTORED,
                                                               IndexConstants.States.DELETED_AND_BACKED_UP],
                IndexConstants.States.RESTORED: [IndexConstants.States.PURGED]
            }

        else:

            return {
                IndexConstants.States.CREATED: [IndexConstants.States.ROLLED],
                IndexConstants.States.ROLLED: [IndexConstants.States.PURGED]
            }

    elif operating_mode == ClusterConstants.OperatingModes.HOT_WARM:

        if backup_enabled:

            if ds_type in (DatasourceConstants.Types.METRIC, DatasourceConstants.Types.LOG):

                return {
                    # Below 3 entries are for hot index
                    IndexConstants.States.CREATED: [IndexConstants.States.ROLLED],
                    IndexConstants.States.ROLLED: [IndexConstants.States.WARMED],
                    IndexConstants.States.WARMED: [IndexConstants.States.SHRINKED],
                    IndexConstants.States.SHRINKED: [IndexConstants.States.PURGED],

                    # Below entries are for warm index
                    IndexConstants.States.SHRINK_CREATED: [IndexConstants.States.MERGED],
                    IndexConstants.States.MERGED: [IndexConstants.States.MERGED_AND_BACKED_UP],
                    IndexConstants.States.MERGED_AND_BACKED_UP: [IndexConstants.States.DELETED_AND_BACKED_UP],
                    IndexConstants.States.DELETED_AND_BACKED_UP: [IndexConstants.States.PURGED,
                                                                  IndexConstants.States.RESTORED_AND_BACKED_UP],
                    IndexConstants.States.RESTORED_AND_BACKED_UP: [IndexConstants.States.RESTORED,
                                                                   IndexConstants.States.DELETED_AND_BACKED_UP],
                    IndexConstants.States.RESTORED: [IndexConstants.States.PURGED]
                }

            else:

                # This would be exactly same as hot-only mode with back-ups
                return get_possible_state_transitions(ClusterConstants.OperatingModes.HOT_ONLY, backup_enabled, ds_type)

        else:

            if ds_type in (DatasourceConstants.Types.METRIC, DatasourceConstants.Types.LOG):

                return {
                    # Below 3 entries are for hot index
                    IndexConstants.States.CREATED: [IndexConstants.States.ROLLED],
                    IndexConstants.States.ROLLED: [IndexConstants.States.WARMED],
                    IndexConstants.States.WARMED: [IndexConstants.States.SHRINKED],
                    IndexConstants.States.SHRINKED: [IndexConstants.States.PURGED],

                    # Below entries are for warm index
                    IndexConstants.States.SHRINK_CREATED: [IndexConstants.States.MERGED],
                    IndexConstants.States.MERGED: [IndexConstants.States.PURGED]
                }

            else:

                # This would be exactly same as hot-only mode without back-ups
                return get_possible_state_transitions(ClusterConstants.OperatingModes.HOT_ONLY, backup_enabled, ds_type)

    elif operating_mode == ClusterConstants.OperatingModes.HOT_OPTIMIZED:

        if backup_enabled:

            if ds_type in (DatasourceConstants.Types.METRIC, DatasourceConstants.Types.LOG):

                return {
                    # Below 3 lines are for un-shrinked index i.e. normal flow
                    IndexConstants.States.CREATED: [IndexConstants.States.ROLLED],
                    IndexConstants.States.ROLLED: [IndexConstants.States.SHRINKED],
                    IndexConstants.States.SHRINKED: [IndexConstants.States.PURGED],

                    # Below lines represent life of new index which is derived by shrinking above index
                    IndexConstants.States.SHRINK_CREATED: [IndexConstants.States.MERGED],
                    IndexConstants.States.MERGED: [IndexConstants.States.MERGED_AND_BACKED_UP],
                    IndexConstants.States.MERGED_AND_BACKED_UP: [IndexConstants.States.DELETED_AND_BACKED_UP],
                    IndexConstants.States.DELETED_AND_BACKED_UP: [IndexConstants.States.PURGED,
                                                                  IndexConstants.States.RESTORED_AND_BACKED_UP],
                    IndexConstants.States.RESTORED_AND_BACKED_UP: [IndexConstants.States.RESTORED,
                                                                   IndexConstants.States.DELETED_AND_BACKED_UP],
                    IndexConstants.States.RESTORED: [IndexConstants.States.PURGED]
                }

            else:

                # This would be exactly same as hot-only mode with back-ups
                return get_possible_state_transitions(ClusterConstants.OperatingModes.HOT_ONLY, backup_enabled, ds_type)

        else:

            if ds_type in (DatasourceConstants.Types.METRIC, DatasourceConstants.Types.LOG):

                return {
                    # Below 3 lines are for un-shrinked index i.e. normal flow
                    IndexConstants.States.CREATED: [IndexConstants.States.ROLLED],
                    IndexConstants.States.ROLLED: [IndexConstants.States.SHRINKED],
                    IndexConstants.States.SHRINKED: [IndexConstants.States.PURGED],

                    # Below lines represent life of new index which is derived by shrinking above index
                    IndexConstants.States.SHRINK_CREATED: [IndexConstants.States.MERGED],
                    IndexConstants.States.MERGED: [IndexConstants.States.PURGED]
                }

            else:

                # This would be exactly same as hot-only mode without back-ups
                return get_possible_state_transitions(ClusterConstants.OperatingModes.HOT_ONLY, backup_enabled, ds_type)
