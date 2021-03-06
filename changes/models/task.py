from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, String, Integer
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.constants import Result, Status
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Task(db.Model):
    __tablename__ = 'task'
    __table_args__ = (
        Index('idx_task_parent_id', 'parent_id', 'task_name'),
        Index('idx_task_child_id', 'child_id', 'task_name'),
        UniqueConstraint('task_name', 'parent_id', 'child_id', name='unq_task_entity'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    task_name = Column(String(128), nullable=False)
    task_id = Column('child_id', GUID, nullable=False)
    parent_id = Column(GUID)
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    num_retries = Column(Integer, nullable=False, default=0)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    __repr__ = model_repr('task_name', 'parent_id', 'child_id', 'status')

    def __init__(self, **kwargs):
        super(Task, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created

    @classmethod
    def check(cls, task_name, parent_id):
        """
        >>> if Task.check('my_task', parent_item.id) == Status.finished:
        >>>     print "all child tasks done!"
        """
        # XXX(dcramer): we could make this fast if we're concerneda bout # of
        # rows by doing two network hops (first check for in progress, then
        # report result)
        child_tasks = list(db.session.query(
            cls.result, Task.status
        ).filter(
            cls.task_name == task_name,
            cls.parent_id == parent_id,
        ))
        if any(r.status != Status.finished for r in child_tasks):
            return Status.in_progress
        return Status.finished
