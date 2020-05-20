from pyspark.sql import functions as F, types as T

from baskerville.util.enums import FeatureComputeType
from baskerville.features.feature_unique_path_total import FeatureUniquePathTotal

from tests.unit.baskerville_tests.helpers.spark_testing_base import \
    FeatureSparkTestCase


class TestSparkUniquePathTotal(FeatureSparkTestCase):

    def setUp(self):
        super(TestSparkUniquePathTotal, self).setUp()
        self.feature = FeatureUniquePathTotal()

    def test_instance(self):
        self.assertTrue(hasattr(self.feature, 'feature_name'))
        self.assertTrue(hasattr(self.feature, 'COLUMNS'))
        self.assertTrue(hasattr(self.feature, 'DEPENDENCIES'))
        self.assertTrue(hasattr(self.feature, 'DEFAULT_VALUE'))
        self.assertTrue(hasattr(self.feature, 'compute_type'))

        self.assertTrue(self.feature.feature_name == 'unique_path_total')
        self.assertTrue(
            self.feature.columns == ['client_url'])
        self.assertTrue(self.feature.dependencies == [])
        self.assertTrue(self.feature.DEFAULT_VALUE == 1.)
        self.assertTrue(self.feature.compute_type == FeatureComputeType.total)
        self.assertIsNotNone(self.feature.feature_name)
        self.assertIsNotNone(self.feature.feature_default)

        self.assertTrue(isinstance(self.feature.feature_name, str))
        self.assertTrue(isinstance(self.feature.feature_default, float))

    def test_compute_single_record(self):
        ats_record = {
            "client_ip": '55.555.55.55',
            "@timestamp": '2018-01-17T08:30:00.000Z',
            "content_type": 'html',
            "client_url": 'page1/page2/page3?query',
        }
        sub_df = self.get_sub_df_for_feature(self.feature, [ats_record])
        result = self.feature.compute(sub_df)
        expected_df = sub_df.withColumn(
            self.feature.feature_name,
            F.lit(1.).cast('float')
        )

        self.assertDataFrameEqual(
            result,
            expected_df
        )

    def test_compute_multiple_records_different_depth(self):
        first_ats_record = {
            "client_ip": '55.555.55.55',
            "@timestamp": '2018-01-17T08:30:00.000Z',
            "content_type": 'html',
            "client_url": 'page1/page2/page3',
        }
        second_ats_record = {
            "client_ip": '55.555.55.55',
            "@timestamp": '2018-01-17T08:30:00.000Z',
            "content_type": 'html',
            "client_url": 'page1/page2',
        }
        third_ats_record = {
            "client_ip": '55.555.55.55',
            "@timestamp": '2018-01-17T08:30:00.000Z',
            "content_type": 'html',
            "client_url": 'page1/page2/page3',
        }

        sub_df = self.get_sub_df_for_feature(
            self.feature, [
                first_ats_record, second_ats_record, third_ats_record
            ]
        )
        result = self.feature.compute(sub_df)

        expected_df = sub_df.withColumn(
            self.feature.feature_name,
            F.lit(2.).cast('float')
        )
        self.assertDataFrameEqual(
            result,
            expected_df
        )

    def test_compute_multiple_records_same_depth_diff_type(self):
        first_ats_record = {
            "client_ip": '55.555.55.55',
            "@timestamp": '2018-01-17T08:30:00.000Z',
            "content_type": 'html',
            "client_url": 'page1/page2/page3',
        }
        second_ats_record = {
            "client_ip": '55.555.55.55',
            "@timestamp": '2018-01-17T08:30:00.000Z',
            "content_type": 'application/javascript',
            "client_url": 'page1/page2',
        }
        sub_df = self.session.createDataFrame(
            [first_ats_record, second_ats_record]
        )
        sub_df = sub_df.withColumn(
            '@timestamp', F.col('@timestamp').cast('timestamp')
        )
        for k, v in self.feature.pre_group_by_calcs.items():
            sub_df = sub_df.withColumn(k, v)
        sub_df = self.feature.misc_compute(sub_df)
        sub_df = sub_df.groupby('client_ip').agg(
            *[v.alias(k) for k, v in self.feature.group_by_aggs.items()]
        )
        result = self.feature.compute(sub_df)
        expected_df = sub_df.withColumn(
            self.feature.feature_name,
            F.lit(2.).cast('float')
        )
        self.assertDataFrameEqual(
            result,
            expected_df
        )

    def test_update_row(self):
        test_current = {self.feature.feature_name: 2.}
        test_past = {self.feature.feature_name: 1.}
        value = self.feature.update_row(
            test_current, test_past
        )

        self.assertAlmostEqual(value, 3., places=2)

    def test_update(self):
        schema = T.StructType([
            T.StructField(
                self.feature.current_features_column,
                T.MapType(T.StringType(), T.FloatType())
            ),
            T.StructField(
                self.feature.past_features_column,
                T.MapType(T.StringType(), T.FloatType())
            ),
        ])

        sub_df = self.session.createDataFrame(
            [{
                self.feature.current_features_column: {
                    self.feature.feature_name: 2.,
                },
                self.feature.past_features_column: {
                    self.feature.feature_name: 1.,
                }
            }],
            schema=schema
        )
        result_df = self.feature.update(
            sub_df
        )

        result_df.show()
        value = result_df.select(
            self.feature.updated_feature_col_name
        ).collect()[0][self.feature.updated_feature_col_name]
        expected_value = 3.
        self.assertAlmostEqual(value, expected_value, places=2)
