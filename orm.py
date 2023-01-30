import datetime

from sqlalchemy import (
    Table, MetaData, Column, Integer, String, Date,
    DateTime, ForeignKey, Numeric
)
from sqlalchemy.orm import mapper, relationship

import model

metadata = MetaData()

users = Table(
    'users', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('first_name', String(55)),
    Column('last_name', String(100)),
    Column('email', String(100)),
    Column('password', String(200)),
    Column('email_create_task', String(10)),
    Column('email_new_available_task', String(10)),
    Column('email_edit_task', String(10)),
    Column('email_proposal_accepted', String(10)),
    Column('email_status_completed', String(10)),
    Column('email_new_proposal', String(10)),
    Column('email_edit_proposal', String(10)),
    Column('email_hoa_request_updates', String(10))
)

organizations = Table(
    'organizations', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', String(55)),
    Column('org_type', String(55)),
    Column('street_address', String(100)),
    Column('city', String(60)),
    Column('state', String(2)),
    Column('zipcode', String(9)),
    Column('categories', String(1000)),
    Column('admin_approved', String(35)),
    Column('approval_type', String(35))
)

users_orgs = Table(
    'users_orgs', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id'),
    Column('organization_id')
)

buildings = Table(
    'buildings', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('address', String(55)),
    Column('city', String(55)),
    Column('state', String(2)),
    Column('zip', String(5)),
    Column('organization_id', ForeignKey('organizations.id'))
)

units = Table(
    'units', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('building_id', ForeignKey('buildings.id'))
)


tasks = Table(
    'tasks', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', String(40)),
    Column('category', String(35)),
    Column('description', String(500)),
    Column('due_by', Date),
    Column('status', String(35)),
    Column('created_at', Date),
    Column('user_id', ForeignKey('users.id')),
    Column('org_id', ForeignKey('organizations.id')),
    Column('accepted_proposal_id', ForeignKey('proposals.id')),
    Column('images', String(750)),
    Column('assigned_vendors', String(750)),
    Column('admin_approved', String(35))
)

tasks_vendors = Table(
    'tasks_vendors', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('task_id', ForeignKey('tasks.id')),
    Column('vendor_id', ForeignKey('organizations.id'))
)

proposals = Table(
    'proposals', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('task_id', ForeignKey('tasks.id')),
    Column('content', String(500)),
    Column('cost_estimate', Integer),
    Column('time_estimate_days', Integer),
    Column('time_estimate_hours', Integer),
    Column('status', String(35)),
    Column('requested_updates', String(350)),
    Column('vendor_response', String(350)),
    Column('vendor_response_date', String(35)),
    Column('created_at', Date),
    Column('created_by', ForeignKey('users.id')),
    Column('org_id', ForeignKey('organizations.id'))

)

task_messages = Table(
    'task_messages', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('task_id', ForeignKey('tasks.id')),
    Column('sending_user_id', Integer),
    Column('vendor_org_id', Integer),
    Column('sending_org_id', Integer),
    Column('receiving_org_id', Integer),
    Column('content', String(255)),
    Column('created_at', DateTime, default=datetime.datetime.utcnow)
)

proposal_lines = Table(
    'proposal_lines', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('proposal_id', ForeignKey('proposals.id')),
    Column('description', String(155)),
    Column('quantity', Integer),
    Column('price', Numeric(precision=6, scale=2)),
    Column('total', Numeric(precision=6, scale=2))
)

target_zips = Table(
    'target_zips', metadata,
    Column('vendor_id', ForeignKey('organizations.id')),
    Column('zipcode', String(10)),
    Column('max_distance', Numeric(precision=6, scale=1))
)

zip_distance = Table(
    'zip_distance', metadata,
    Column('origin', String(7)),
    Column('destination', String(7)),
    Column('distance', Numeric(precision=6, scale=1))
)


def start_mappers():

    zip_distance_mapper = mapper(model.ZipDistance, zip_distance, primary_key=[zip_distance.c.origin, zip_distance.c.destination])
    
    target_zips_mapper = mapper(model.TargetZip, target_zips, primary_key=[target_zips.c.vendor_id, target_zips.c.zipcode])

    user_mapper = mapper(model.User, users)
    org_mapper = mapper(model.Organization, organizations)
    user_org_mapper = mapper(model.UserOrg, users_orgs)

    task_msg_mapper = mapper(model.TaskMessage, task_messages)
    proposal_line_mapper = mapper(model.ProposalLine, proposal_lines)

    proposal_mapper = mapper(model.Proposal, proposals, properties={'vendor_org': relationship(org_mapper, foreign_keys=[proposals.c.org_id]),
                                                                    'user': relationship(user_mapper, foreign_keys=[proposals.c.created_by]),
                                                                    'lines': relationship(proposal_line_mapper, collection_class=list)
                                                                    })

    mapper(model.Task, tasks, properties={'proposals': relationship(proposal_mapper, backref='task', collection_class=list, foreign_keys=[proposals.c.task_id]),
                                          'messages': relationship(task_msg_mapper, backref='task', collection_class=list),
                                          'hoa_org': relationship(org_mapper, foreign_keys=[tasks.c.org_id]),
                                          'user': relationship(user_mapper, foreign_keys=[tasks.c.user_id]),
                                          'accepted_proposal': relationship(proposal_mapper,foreign_keys=[tasks.c.accepted_proposal_id]),
                                          'vendors_assigned': relationship(org_mapper, secondary=tasks_vendors, collection_class=list)
                                          })

    
    



