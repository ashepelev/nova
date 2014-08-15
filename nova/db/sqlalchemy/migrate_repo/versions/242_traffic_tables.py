from migrate.changeset import UniqueConstraint
from migrate import ForeignKeyConstraint
from sqlalchemy import Boolean, BigInteger, Column, DateTime, Enum, Float
from sqlalchemy import dialects
from sqlalchemy import ForeignKey, Index, Integer, MetaData, String, Table
from sqlalchemy import Text
from sqlalchemy.types import NullType

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging

LOG = logging.getLogger(__name__)

def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    traffic_info = Table('traffic_info',meta,
			Column('created_at', DateTime),
        		Column('updated_at', DateTime),
        		Column('deleted_at', DateTime),
			Column('deleted', Integer),
        		Column('id', Integer, primary_key=True, nullable=False),
                        Column('src',Integer,nullable=False),
                        Column('dst',Integer,nullable=False),
                        Column('bytes',Float,nullable=False),
			Column('m_id',Integer,nullable=False),
                        mysql_engine='InnoDB',
                        mysql_charset='utf8'
    )

    ping_info = Table('ping_info',meta,
			Column('created_at', DateTime),
        		Column('updated_at', DateTime),
        		Column('deleted_at', DateTime),
			Column('deleted', Integer),
        		Column('id', Integer, primary_key=True, nullable=False),
                        Column('src',Integer,nullable=False),
                        Column('dst',Integer,nullable=False),
                        Column('latency',Float,nullable=False),
                        mysql_engine='InnoDB',
                        mysql_charset='utf8'
    )

    try:
        traffic_info.create()
    except Exception:
        LOG.info(repr(traffic_info))
        LOG.exception(_('Exception while creating table traffic_info.'))
        raise

    try:
        ping_info.create()
    except Exception:
        LOG.info(repr(ping_info))
        LOG.exception(_('Exception while creating table ping_info.'))
        raise

    # TO DO
    # Create indicies


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    traffic_info = Table('traffic_info',meta)
    try:
        traffic_info.drop()
    except:
    	LOG.info("traffic_info doesn't exist")
        #LOG.info(repr(traffic_info))
        #LOG.exception(_('Exception while deleting table traffic_info.'))

    ping_info = Table('ping_info',meta)
    try:
        ping_info.drop()
    except Exception:
    	LOG.info("ping_info doesn't exist")
        #LOG.info(repr(ping_info))
        #LOG.exception(_('Exception while deleting table ping_info.'))
