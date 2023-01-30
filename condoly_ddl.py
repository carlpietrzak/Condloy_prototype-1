import sqlite3


drop_user_table = """drop table users;"""

create_users_table = """create table if not exists users (
                        id integer PRIMARY KEY,
                        first_name text,
                        last_name text,
                        email text,
                        password text
                        )"""

drop_org_table = """drop table organizations;"""

create_orgs_table = """create table if not exists organizations (
                       id integer PRIMARY KEY,
                       name text,
                       org_type text,
                       street_address text,
                       city text,
                       state text,
                       zipcode text
                       )"""



create_user_org_table = """create table if not exists users_orgs ( 
                           id integer PRIMARY KEY,
                           user_id integer,
                           organization_id integer)"""


drop_tasks_table = "drop table tasks;"

create_tasks_table = """         create table if not exists tasks (
                                 id integer PRIMARY KEY,
                                 name text,
                                 category text,
                                 description text,
                                 due_by text,
                                 status text,
                                 created_at text,
                                 user_id integer,
                                 org_id integer
                                 );"""

drop_proposals_table = """drop table proposals;"""


create_proposals_table = """create table if not exists proposals (
	    id integer PRIMARY KEY,
	    task_id integer,
	    content text,
	    cost_estimate integer,
	    time_estimate_days integer,
	    time_estimate_hours integer,
	    status text,
            requested_updates text,
	    created_by integer,
            org_id integer,
            created_at text)"""


create_task_messages_table = """create table if not exists task_messages(
                                id integer PRIMARY KEY,
                                task_id integer,
                                sending_user_id integer,
                                vendor_org_id integer,
                                sending_org_id integer,
                                receiving_org_id integer,
                                content text,
                                created_at text);"""

create_proposal_lines_table = """create table if not exists proposal_lines(
                                 id integer PRIMARY KEY,
                                 proposal_id integer,
                                 description text,
                                 quantity integer,
                                 price real,
                                 total real,
                                 created_at text
                                 )"""


create_statements = [create_users_table, 
                     create_orgs_table,
                     create_user_org_table, 
                     create_tasks_table, 
                     create_proposals_table,
                     create_task_messages_table,
                     create_proposal_lines_table]

ad_hoc = [drop_tasks_table, create_tasks_table]

conn = sqlite3.connect("condoly.db")
c = conn.cursor()

for s in create_statements:

    c.execute(s)
