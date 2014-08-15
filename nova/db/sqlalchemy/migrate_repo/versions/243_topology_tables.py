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

    node_info = Table('node_info',meta,
			Column('created_at', DateTime),
        		Column('updated_at', DateTime),
        		Column('deleted_at', DateTime),
			Column('deleted', Integer),
        		Column('id', Integer, primary_key=True, nullable=False),
                        Column('node_id',Integer,nullable=False),
                        Column('name',String(length=30),nullable=False),
                        Column('ip_addr',String(length=20)),
			Column('hostname',String(length=255)),
                        mysql_engine='InnoDB',
                        mysql_charset='utf8'
    )

    edge_info = Table('edge_info',meta,
			Column('created_at', DateTime),
        		Column('updated_at', DateTime),
        		Column('deleted_at', DateTime),
			Column('deleted', Integer),
        		Column('id', Integer, primary_key=True, nullable=False),
                        Column('start',Integer,nullable=False),
                        Column('end',Integer,nullable=False),
                        mysql_engine='InnoDB',
                        mysql_charset='utf8'
    )

    try:
        node_info.create()
    except Exception:
        LOG.info(repr(node_info))
        LOG.exception(_('Exception while creating table node_info.'))
        raise

    try:
        edge_info.create()
    except Exception:
        LOG.info(repr(edge_info))
        LOG.exception(_('Exception while creating table edge_info.'))
        raise

    # TO DO
    # Create indicies


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    node_info = Table('node_info',meta)
    try:
        node_info.drop()
    except Exception:
    	LOG.info("Table node_info doesn't exist")
        #LOG.info(repr(node_info))
        #LOG.exception(_('Exception while deleting table node_info.'))
        

    edge_info = Table('edge_info',meta)
    try:
        edge_info.drop()
    except Exception:
    	LOG.info("Table edge_info doesn't exist")
        #LOG.info(repr(edge_info))
        #LOG.exception(_('Exception while deleting table edge_info.'))

