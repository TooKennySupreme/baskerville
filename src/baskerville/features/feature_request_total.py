# Copyright (c) 2020, eQualit.ie inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.


from baskerville.features.updateable_features import UpdaterTotal
from pyspark.sql import functions as F

from baskerville.features.helpers import update_total


class FeatureRequestTotal(UpdaterTotal):
    """
    For each IP compute the total number of requests.
    """
    DEFAULT_VALUE = 0.
    COLUMNS = ['@timestamp']
    DEPENDENCIES = []

    def __init__(self):
        super(FeatureRequestTotal, self).__init__()

        self.group_by_aggs = {
            'num_requests': F.count(F.col('@timestamp')).cast('float'),
        }

    def compute(self, df):
        from pyspark.sql import functions as F

        df = df.withColumn(
            self.feature_name,
            F.col('num_requests').cast('float')
        ).fillna({self.feature_name: self.feature_default})

        return df

    @classmethod
    def update_row(cls, current, past, *args, **kwargs):
        return update_total(
            current[cls.feature_name_from_class()],
            past.get(cls.feature_name_from_class())
        )
