import unittest

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from os import environ
import traceback
environ['DCHK_ENV'] = 'test'

import models.helpers.base
engine = models.helpers.base.get_new_engine()

models.helpers.base.init(engine) # Initialize base declarative class.

from models import *
from models.data_source import DataSource, DataSourceType
db_session = models.helpers.base.db_session

class BaseTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        models.helpers.base.Base.metadata.create_all(engine)
        from celery_jobs.job_runs import app as celery_app
        celery_app.conf.update(CELERY_ALWAYS_EAGER=True)

    def setUp(self):
        models.helpers.base.Base.metadata.create_all(engine)
        self.s = db_session


    def tearDown(self):
        self.s.remove()
        models.helpers.base.Base.metadata.drop_all(engine)


    def dummy_datasource(self):
        config = self.__class__.config()
        config["schemas"] = ["test"]
        config["data_source_type"] = DataSourceType.impala
        d = DataSource(**config)
        return d

    @classmethod
    def config(cls):
        return {
            "host": "localhost",
            "port": 21050,
            "user": None,
            "password": None
        }