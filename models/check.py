from sqlalchemy import Column, String, Integer, ForeignKey, Enum, Table, DateTime
from sqlalchemy.orm import relationship, backref

import models.helpers.base
from models.helpers.timestamps_triggers import timestamps_triggers
from models.log import Log, HasLogs
from sqlalchemy.dialects.postgresql import JSONB
from copy import deepcopy
from models.data_source import DataSource
from models.job_run import JobRun, JobRunStatus
import datetime
now = datetime.datetime.now
from checks.date_gap_check import DateGapCheck
from checks.null_check import NullCheck
from checks.uniqueness_check import UniquenessCheck
from models.helpers.crud_mixin import CrudMixin
import sys

Base = models.helpers.base.Base
db_session = models.helpers.base.db_session


from marshmallow import Schema, fields, pprint

class CheckMetadataSchema(Schema):
    column = fields.Str()


class CheckSchema(Schema):
    id = fields.Integer()
    check_type = fields.Str()
    check_metadata = fields.Nested(CheckMetadataSchema())

    @classmethod
    def default_json(cls):
        """
            Used by the NEW action in Flask, to generate a dummy object that can
            be sent down with id=new for the form on the React-side to use.

            This makes it easy to work with new or existing objects in the form,
            it only needs to look at ID to know to POST or PUT, but functionality
            is otherwise identical.
        """
        return {
            "id": 'new',
            "check_metadata": {
                "column": ''
            },
            "check_type": 'CheckType.uniqueness'
        }


import enum
class CheckType(enum.Enum):
    uniqueness = "uniqueness"
    null = "null"
    date_gap = "date_gap"


class Check(Base, HasLogs, CrudMixin):
    __tablename__ = 'check'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    check_type = Column(Enum(CheckType), nullable=False)
    check_metadata = Column(JSONB, nullable=False)
    rule_id = Column(Integer, ForeignKey('rule.id'))
    rule = relationship("Rule", back_populates="checks")

    ENUMS = ["check_type"]

    def run(self, job_run, source, table):
        log = self.get_log(job_run=job_run)
        log.add_log("creation", "Begin %s Check of Source %s Table %s with Metadata %s" % (self.check_type.value, source.id, table, self.check_metadata))
        db_session.add(job_run)

        try:
            if (job_run.status in [JobRunStatus.failed, JobRunStatus.cancelled, JobRunStatus.rejected]):
                log.add_log("cancelled", "Check cancelled due to Job Run Status of %s caused by some other worker." % (job_run.status))
            else:
                chk_class = eval(str(self.check_type.value).title() + "Check")

                metadata = deepcopy(self.check_metadata)
                metadata["table"] = table.split(".")[1]
                metadata["schema"] = table.split(".")[0]
                metadata["config"] = source.config()
                metadata["log"] = log

                check = chk_class(metadata)
                check.run()
                log.add_log("finished", "Check Ended")
        except Exception as e:
            print str(sys.exc_info())
            log.new_error_event()
            job_run.set_failed()

        db_session.commit()


timestamps_triggers(Check)