import datetime
from os import environ
import os

from flask import (Flask,
                   render_template,
                   request,
                   redirect,
                   url_for,
                   flash,
                   session as flask_session)

from flask_mail import Mail
from flask_mail import Message
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
import boto3
import logging
from botocore.exceptions import ClientError
import helpers
import orm
import model

app = Flask(__name__)

app.app_context().push()

app.config['SECRET_KEY'] = environ.get('SECRET_KEY')

app.config['MAIL_SERVER'] = 'email-smtp.us-east-1.amazonaws.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

app.config['CONDOLY_MAIL_SUBJECT_PREFIX'] = '[Condoly] '
app.config['CONDOLY_MAIL_SENDER'] = 'Condoly Admin <kraynakr@gmail.com>'
app.config['CONDOLY_MESSAGE_BUS_URL'] = 'https://sqs.us-east-1.amazonaws.com/453965245725/condoly_message_bus'

mail = Mail(app)

orm.start_mappers()

engine = create_engine('sqlite:///condoly.db')

orm.metadata.create_all(engine)

get_session = sessionmaker(bind=engine)
queue_url = 'https://sqs.us-east-1.amazonaws.com/453965245725/condoly_message_bus'


def send_email(to, subject, template, **kwargs):
    msg = Message(app.config['CONDOLY_MAIL_SUBJECT_PREFIX'] + subject,
                  sender=app.config['CONDOLY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    mail.send(msg)


def event_dispatching():

    # Create SQS client
    sqs = boto3.client('sqs', region_name='us-east-1')

    dispatch_lookup = {"create_task": new_task_email,
                               "create_proposal": new_proposal_email,
                               "edit_proposal": edit_proposal_email,
                               "edit_task": edit_task_email,
                               "hoa-request-update": hoa_request_updates_email,
                               "hoa-accept": proposal_accepted_email}

    while True:

        # Receive message from SQS queue
        response = sqs.receive_message(
            QueueUrl=queue_url,
            AttributeNames=[
                'SentTimestamp'
            ],
            MaxNumberOfMessages=1,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=0,
            WaitTimeSeconds=0
        )

        if 'Messages' in response.keys():

            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']

            # Delete received message from queue
            sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            #print('Received and deleted message: %s' % message)
            print(message["MessageAttributes"]["entity_type"]["StringValue"],
                  message["MessageAttributes"]["event"]["StringValue"],
                  message["MessageAttributes"]["entity_id"]["StringValue"])

            entity_id = message["MessageAttributes"]["entity_id"]["StringValue"]
            entity_type = message["MessageAttributes"]["entity_type"]["StringValue"]
            event = message["MessageAttributes"]["event"]["StringValue"]

            try:
                dispatch_lookup[event](entity_id)
            except:
                continue

def new_task_email(task_id):

    session = get_session()

    task = session.query(model.Task).filter_by(id=task_id).one()

    #check to see if the hoa user wants to receive a notification
    if task.user.email_create_task == 'true':

        send_email(task.user.email, 'New Task Created', 'mail/new_task_hoa', task=task)



def edit_task_email(task_id):

    session = get_session()

    task = session.query(model.Task).filter_by(id=task_id).one()

    if task.user.email_edit_task == 'true':

        send_email(task.user.email, 'Task Edited', 'mail/task_edited_hoa', task=task)

def new_proposal_email(proposal_id):

    session = get_session()

    proposal = session.query(model.Proposal).filter_by(id=proposal_id).one()

    if proposal.user.email_new_proposal == 'true':

        send_email(proposal.user.email, 'New Proposal Created', 'mail/new_proposal_email_vendor', proposal=proposal)

    if proposal.task.user.email_new_proposal == 'true':

        send_email(proposal.task.user.email, 'New Proposal Created', 'mail/new_proposal_email_hoa', proposal=proposal)

def edit_proposal_email(proposal_id):

    session = get_session()

    proposal = session.query(model.Proposal).filter_by(id=proposal_id).one()

    if proposal.user.email_edit_proposal == 'true':

        send_email(proposal.user.email, 'Proposal Edited', 'mail/edit_proposal_email_vendor', proposal=proposal)

    if proposal.task.user.email_edit_proposal == 'true':

        send_email(proposal.task.user.email, 'Proposal Edited', 'mail/edit_proposal_email_hoa', proposal=proposal)


def proposal_accepted_email(proposal_id):

    session = get_session()

    proposal = session.query(model.Proposal).filter_by(id=proposal_id).one()

    if proposal.user.email_proposal_accepted == 'true':

        send_email(proposal.user.email, 'Proposal Accepted', 'mail/accept_proposal_email_vendor', proposal=proposal)

    if proposal.task.user.email_proposal_accepted == 'true':

        send_email(proposal.task.user.email, 'Proposal Edited', 'mail/accept_proposal_email_hoa', proposal=proposal)


def hoa_request_updates_email(proposal_id):

    session = get_session()

    proposal = session.query(model.Proposal).filter_by(id=proposal_id).one()

    if proposal.user.email_hoa_request_updates == 'true':

        send_email(proposal.user.email, 'Proposal Updates Requested', 'mail/proposal_updates_requested_email_vendor', proposal=proposal)

    if proposal.task.user.email_hoa_request_updates == 'true':

        send_email(proposal.task.user.email, 'Proposal Updates Requested', 'mail/proposal_updates_requested_email_hoa', proposal=proposal)



if __name__ == '__main__':

    event_dispatching()
