import datetime

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

import model
import orm
import repository


orm.start_mappers()

engine = create_engine('sqlite:///:memory:')

orm.metadata.create_all(engine)

get_session = sessionmaker(bind=engine)

session = get_session()

date_str = '2021-03-21'
date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')

new_user = model.User("ross", "kraynak", "ross.kraynak@gmail.com")
new_org = model.Organization("hoa1", "hoa")

new_org.add_user(new_user)


session.add(new_user)
session.add(new_org)
session.commit()

user = session.query(model.User).one()
print("user")
print(user)
print(dir(user))
print("user org id")
print(user.organization_id)
print("user organizations")
print(user.organizations)
print("#########################")


new_vendor_user = model.User("john", "smith", "john.smith@gmail.com")
new_vendor_user2 = model.User("joan", "smythe", "joan.smythe@gmail.com")

new_vendor_org = model.Organization("vendor1", "vendor")
new_vendor_org2 = model.Organization("vendor2", "vendor")


session.add(new_vendor_user)
session.add(new_vendor_org)
session.add(new_vendor_user2)
session.add(new_vendor_org2)

session.commit()
session.flush()

users = session.query(model.User).all()
orgs = session.query(model.Organization).all()

new_task = model.Task("landscape", "cut the lawn", date_obj, "in_progress", new_user.id)

session.add(new_task)
session.commit()

task = session.query(model.Task).all()[0]

new_message = model.TaskMessage(task, new_vendor_user.id, new_vendor_org.id, new_user.id, new_org.id,'this is a message')
new_message2 = model.TaskMessage(task, new_vendor_user2.id, new_vendor_org2.id, new_user.id, new_org.id,'this is another message')
new_message3 = model.TaskMessage(task, new_vendor_user2.id, new_vendor_org2.id, new_user.id, new_org.id,'this is a new message')


task.add_message(new_message)
task.add_message(new_message2)
task.add_message(new_message3)


session.commit()

task_again = session.query(model.Task).all()[0]


print("task info")
print(task_again.id, task_again.category, task_again.description, task_again.due_by, task_again.status, task_again.created_by, task_again.task_msgs)


print("task message info")
message = session.query(model.TaskMessage).all()[0]
print(message.id, message.content, message.created_at, message.sender_user_id, message.receiver_user_id, message.task)
print("####################")
print("############")
res = session.execute("select * from task_messages")
print(res.fetchall())
print("#######################")
res = session.execute(f"select sender_org_id, o.name, max(t.id), content from task_messages t join organizations o on t.sender_org_id = o.id where t.receiver_org_id = {new_org.id} and t.task_id = {task.id}  group by sender_org_id")
print(res.fetchall())


