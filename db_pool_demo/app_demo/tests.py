import time
import random
from datetime import tzinfo

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from faker import Faker

from app_demo.models import PoolDemoModel

tzinfo = timezone.get_default_timezone()


class MySQLDBPoolTestCase(TestCase):
    def setUp(self) -> None:
        self._faker = Faker(locale='zh_CN')

    def tearDown(self) -> None:
        # super().tearDown()
        pass

    def test_insert_with_model(self):
        for i in range(100):
            if i % 2 == 0:
                obj = PoolDemoModel.objects.create(
                    name=self._faker.address(),
                    size=random.randint(100, 100000),
                    od_date=self._faker.date_time(tzinfo=tzinfo, end_datetime=None),
                    remark="model_one_create_commit"
                )
                # self.assertEqual(obj.id, 100, msg="DD:%s" % obj.id)
                # obj.refresh_from_db()
            else:
                obj = PoolDemoModel(
                    name=self._faker.address(),
                    size=random.randint(100, 100000),
                    od_date=self._faker.date_time(tzinfo=tzinfo, end_datetime=None),
                    remark="model_one_save_commit"
                )
                obj.save()

        bulk_objs = []
        for i in range(100):
            obj = PoolDemoModel(
                name=self._faker.address(),
                size=random.randint(100, 100000),
                od_date=self._faker.date_time(tzinfo=tzinfo, end_datetime=None),
                remark="model_bulk_create_commit"
            )
            bulk_objs.append(obj)

        PoolDemoModel.objects.bulk_create(bulk_objs)

    def test_insert_with_sql(self):
        pass

    def test_query_with_model(self):
        pass

    def test_query_with_sql(self):
        pass

    def test_update_with_model(self):
        pass

    def test_update_with_sql(self):
        pass

    def test_delete_with_model(self):
        pass

    def test_delete_with_sql(self):
        pass


class PgDBPoolTest(TestCase):
    def setUp(self) -> None:
        self._faker = Faker(locale='zh_CN')

    def tearDown(self) -> None:
        super().tearDown()

    def test_insert_with_model(self):
        max_cnt = 2000

        for i in range(max_cnt):
            pass

    def test_insert_with_sql(self):
        pass

    def test_query_with_model(self):
        pass

    def test_query_with_sql(self):
        pass

    def test_update_with_model(self):
        pass

    def test_update_with_sql(self):
        pass

    def test_delete_with_model(self):
        pass

    def test_delete_with_sql(self):
        pass


class PracleDBPoolTest(TestCase):
    def setUp(self) -> None:
        self._faker = Faker(locale='zh_CN')

    def tearDown(self) -> None:
        super().tearDown()

    def test_insert_with_model(self):
        max_cnt = 2000

        for i in range(max_cnt):
            pass

    def test_insert_with_sql(self):
        pass

    def test_query_with_model(self):
        pass

    def test_query_with_sql(self):
        pass

    def test_update_with_model(self):
        pass

    def test_update_with_sql(self):
        pass

    def test_delete_with_model(self):
        pass

    def test_delete_with_sql(self):
        pass
