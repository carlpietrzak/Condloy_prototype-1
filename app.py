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
from flask_login import LoginManager, login_required, logout_user, current_user, login_user
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
import boto3
import logging
from botocore.exceptions import ClientError
import helpers


import orm
import model

app = Flask(__name__)

app.config['SECRET_KEY'] = environ.get('SECRET_KEY')

app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

app.config['CONDOLY_MAIL_SUBJECT_PREFIX'] = '[Condoly]'
app.config['CONDOLY_MESSAGE_BUS_URL'] = os.environ.get('bus_queue')


mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)

orm.start_mappers()

engine = create_engine('sqlite:///condoly.db')

orm.metadata.create_all(engine)

get_session = sessionmaker(bind=engine)


def send_email(to, subject, template, **kwargs):

    ses_client = boto3.client('ses')

    response = ses_client.send_email(Destination={'ToAddresses': [to]},
                                     Message={'Body': {'Html': {'Data': render_template(template + '.html', **kwargs)}, 'Text': {'Data': render_template(template + '.txt', **kwargs)}}, 
                                              'Subject': {'Data': subject}},
                                     Source='hello@condoly.io')


def generate_user_token(user_id, expiration=3600):

    s = Serializer(app.config['SECRET_KEY'], expiration)

    return s.dumps({'user_id': user_id}).decode('utf-8')


def confirm_user_token(token):

    s = Serializer(app.config['SECRET_KEY'])

    try:

        data = s.loads(token.encode('utf-8'))

    except:

        return -1

    user_id = data.get('user_id')

    return user_id



@login_manager.user_loader
def load_user(user_id):
    """Check if user is logged-in on every page load."""
    if user_id is not None:

        session = get_session()

        return session.query(model.User).filter_by(id=user_id).one()

    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash('You must be logged in to view that page.')
    return redirect(url_for('auth_bp.login'))


@app.route('/', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('open_tasks'))

    if request.method == 'POST':

        session = get_session()
        user = session.query(model.User).filter_by(email=request.form["email"]).first()

        if user and user.check_password(password=request.form["password"]):

            user_org = session.query(model.UserOrg).filter_by(user_id=user.id).first()


            flask_session["org_id"] = user_org.organization_id
            flask_session["org_id_permanent"] = user_org.organization_id
            flask_session["org_name"] = session.query(model.Organization).filter_by(id=user_org.organization_id).one().name
            flask_session["org_name_permanent"] = flask_session["org_name"]
            flask_session["user_type"] = session.query(model.Organization).filter_by(id=user_org.organization_id).first().org_type
            flask_session["user_type_permanent"] = flask_session["user_type"]

            login_user(user)
            next_page = request.args.get('next')

            if flask_session["user_type"] == "Vendor":
                target = "vendor_tasks"
            else:
                target = "open_tasks"

            return redirect(next_page or url_for(target))

        else:
            flash('Invalid username/password combination')
            return redirect(url_for('login'))


    return render_template('login.html')

@app.route('/password', methods=['GET','POST'])
def forgot_password():

    session = get_session()

    if request.method == 'POST':

        email = request.form["email"]

        user = session.query(model.User).filter_by(email=email).first()

        if user:

            token = generate_user_token(user.id)

            send_email(email, "Password Recovery", "mail/forgot_password", token=token)

        flash("Password reset email sent.")

        return render_template("forgot_password.html")


    else:

        return render_template("forgot_password.html")

@app.route('/password/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):

    session = get_session()

    if request.method == 'POST':

        user_id = confirm_user_token(token)

        user = session.query(model.User).filter_by(id=user_id).first()

        user.set_password(request.form["password"])

        session.commit()
        session.flush()

        flash("Password reset successful!")

        return redirect(url_for('login'))

    else:

        return render_template("reset_password.html", token=token)





@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        session = get_session()

        existing_user = session.query(model.User).filter_by(email=request.form["email"]).first()

        if existing_user is None:

            new_user = model.User(request.form["firstName"], request.form["lastName"], request.form["email"] )
            new_user.set_password(request.form["password"])

            new_org = model.Organization(request.form["orgName"], request.form["orgType"])

            session.add(new_user)
            session.add(new_org)
            session.commit()

            session.flush()

            new_user_org = model.UserOrg(new_user.id, new_org.id)
            session.add(new_user_org)
            session.commit()

            flask_session["org_id"] = new_org.id
            flask_session["org_id_permanent"] = new_org.id
            flask_session["org_name"] = new_org.name
            flask_session["org_name_permanent"] = flask_session["org_name"]
            flask_session["user_type"] = new_org.org_type
            flask_session["user_type_permanent"] = flask_session["user_type"]
            
            login_user(new_user)

            if flask_session["user_type"] == "Vendor":
                return redirect(url_for('org_profile'))

            else:
                return redirect(url_for('open_tasks'))

        else:

            flash('A user already exists with that email address.')
            return render_template('signup.html')

    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect(url_for('login'))


@app.route('/tasks', methods=['GET'])
def tasks():

    return render_template('tasks.html')


@app.route('/tasks/open', methods=['GET'])
def open_tasks():

    # TODO: filter this by logged in user's organization

    session = get_session()

    tasks = session.query(model.Task).filter(and_(model.Task.org_id == flask_session["org_id"], model.Task.status == "Open")).all()

    return render_template('list_tasks.html', tasks=tasks)


@app.route('/tasks/in-progress', methods=['GET'])
def in_progress_tasks():

    session = get_session()

    tasks = session.query(model.Task).filter(and_(model.Task.org_id == flask_session["org_id"], model.Task.status == "In Progress")).all()

    return render_template('hoa_tasks_proposal_accepted.html', tasks=tasks)


@app.route('/tasks/completed', methods=['GET'])
def completed_tasks():

    session = get_session()

    tasks = session.query(model.Task).filter(and_(model.Task.org_id == flask_session["org_id"], model.Task.status == "Completed")).all()

    return render_template('hoa_tasks_proposal_accepted.html', tasks=tasks)


@app.route('/tasks/available', methods=['GET'])
def available_tasks():

    session = get_session()

    tasks = session.query(model.Task).outerjoin(model.Proposal).filter(and_(model.Task.status == 'Open',
                                                                            model.Proposal.id == None)).all()

    return render_template('vendor_list_tasks.html', tasks=tasks)


@app.route('/tasks/applied', methods=['GET', 'POST'])
def applied_tasks():

    session = get_session()

    if request.method == 'POST':

         categories = request.form.getlist("taskCategory")

         tasks = session.query(model.Task).filter(and_(model.Proposal.task_id == model.Task.id,
                                                       model.Proposal.org_id == flask_session["org_id"],
                                                       model.Task.status == 'Open',
                                                       model.Task.category.in_(categories))).all()

    else:

        tasks = session.query(model.Task).filter(and_(model.Proposal.task_id == model.Task.id,
                                                  model.Proposal.org_id == flask_session["org_id"],
                                                  model.Task.status == 'Open')).all()

    return render_template('vendor_list_tasks.html', tasks=tasks)

@app.route('/vendor/tasks/<status>', methods=['GET'])
@app.route('/vendor/tasks', defaults={"status": None}, methods=['GET'])
def vendor_tasks(status):

    session = get_session()

    req = request.args.to_dict(flat=False)

    org = session.query(model.Organization).filter_by(id=flask_session["org_id"]).one()

    if org.admin_approved == 'false':

        flash('Still pending admin approval.')

        return redirect(url_for('org_profile'))

    categories = req.get("taskCategory", org.categories.split(', '))

    if status == 'applied':

        tasks = session.query(model.Task).filter(and_(model.Proposal.task_id == model.Task.id,
                                                      model.Proposal.org_id == flask_session["org_id"],
                                                      model.Task.status == 'Open',
                                                      model.Task.category.in_(categories))).all()

    elif status == 'available' or status == None:

        this_vendor = session.query(model.Organization).filter_by(id=flask_session["org_id"]).one()

        target_zips = session.query(model.TargetZip).filter_by(vendor_id=this_vendor.id).all()

        if len(target_zips) > 0:


            tasks = session.query(model.Task).outerjoin(model.Proposal, model.Task.id==model.Proposal.task_id).join(
                                                                                model.Organization,
                                                                                model.Task.org_id==model.Organization.id).outerjoin(
                                                                                model.ZipDistance,
                                                                                model.Organization.zipcode==model.ZipDistance.destination).outerjoin(
                                                                                model.TargetZip,
                                                                                model.ZipDistance.origin==model.TargetZip.zipcode).filter(
                                                                                        and_(model.Task.status == 'Open',
                                                                                             model.Task.admin_approved == 'true',
                                                                                             or_(model.Proposal.org_id != flask_session["org_id"],
                                                                                                 model.Proposal.org_id == None),
                                                                                             or_(model.Task.vendors_assigned.contains(this_vendor),
                                                                                                 ~model.Task.vendors_assigned.any()),
                                                                                             model.Task.category.in_(categories),
                                                                                             model.TargetZip.vendor_id == this_vendor.id,
                                                                                             model.ZipDistance.distance < model.TargetZip.max_distance)).all()
        else:

            tasks = session.query(model.Task).outerjoin(model.Proposal, model.Task.id==model.Proposal.task_id).filter(
                                                                                        and_(model.Task.status == 'Open',
                                                                                             model.Task.admin_approved == 'true',
                                                                                             or_(model.Proposal.org_id != flask_session["org_id"],
                                                                                                 model.Proposal.org_id == None),
                                                                                             or_(model.Task.vendors_assigned.contains(this_vendor),
                                                                                                 ~model.Task.vendors_assigned.any()),
                                                                                             model.Task.category.in_(categories))).all()


        status = 'available'

    elif status == 'completed':

        tasks = session.query(model.Task).filter(and_(model.Proposal.task_id == model.Task.id,
                                                      model.Proposal.org_id == flask_session["org_id"],
                                                      model.Task.status == 'Completed',
                                                      model.Task.category.in_(categories))).all()

    elif status == 'in-progress':

        tasks = session.query(model.Task).filter(and_(model.Proposal.task_id == model.Task.id,
                                                      model.Proposal.org_id == flask_session["org_id"],
                                                      model.Task.status == 'In Progress',
                                                      model.Task.category.in_(categories))).all()


    return render_template('vendor_list_tasks.html', tasks=tasks, status=status, categories=categories)


@app.route('/tasks/create', methods=['GET', 'POST'])
def create_task():

    if request.method == 'POST':

        session = get_session()

        date_str = request.form["dueDateField"]
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')

        new_task = model.Task(request.form["taskName"],
                              request.form["taskCategory"],
                              request.form["taskDescription"],
                              date_obj,
                              "Open",
                              current_user.id,
                              flask_session["org_id"])

        session.add(new_task)
        session.commit()

        session.flush()

        for i in request.files.getlist("fileUpload"):

            try:

                new_task.add_image(i.filename)

            except:
                continue

        session.commit()

        for i in request.files.getlist("fileUpload"):

            try:

                i.save(i.filename)

                upload_file(i.filename, "condoly-74huhf8423u36d", f"task-images/{new_task.id}/" + i.filename)

            except:
                continue

        publish_event('task', 'create_task', new_task.id)

        return redirect(f'/tasks/{new_task.id}')

    else:

        return render_template('create_task.html')

def upload_file(file_name, bucket, object_name=None):

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


@app.route('/tasks/<int:task_id>/proposals/create', methods=['GET', 'POST'])
def create_proposal(task_id):

    session = get_session()

    task = session.query(model.Task).filter_by(id=task_id).one()

    if request.method == 'POST':


        # Parse the field values for every row
        line_nums = set([ i.split("Line")[-1] for i in request.form.keys() if "Line" in i ])

        lines = { num: {} for num in line_nums }

        for num in line_nums:
            for k,v in request.form.items():
                if num in k:
                    lines[num].update({k.split("Line")[0] : v})


        # Create individual Proposal Lines from the extracted form data
        line_objects = [ model.ProposalLine(**v) for k,v in lines.items() ]


        # Create the actual proposal object itself
        new_proposal = model.Proposal(request.form["description"],
                                      request.form["estimate"],
                                      '0',
                                      '0',
                                      'Under Review',
                                      current_user.id,
                                      flask_session["org_id"])

        # Add the lines to the proposal
        for line in line_objects:
            new_proposal.add_line(line)


        # Add the proposal to its corresponding task
        task = session.query(model.Task).filter_by(id=task_id).one()

        task.add_proposal(new_proposal)

        session.commit()
        session.flush()

        publish_event('proposal', 'create_proposal', new_proposal.id)

        return redirect(url_for('view_proposal', id=new_proposal.id, task_id=task_id))

    else:

        return render_template('create_proposal.html', task_id=task_id, task_name=task.name)

@app.route('/tasks/<int:task_id>/proposals/<int:id>/edit', methods=['GET', 'POST'])
def edit_proposal(id, task_id):

    session = get_session()

    proposal = session.query(model.Proposal).filter_by(id=id).one()

    task = session.query(model.Task).filter_by(id=task_id).one()

    if request.method == 'POST':

        proposal.cost_estimate = request.form["estimate"]
        proposal.content = request.form["description"]

        # assemble all the proposal lines, both existing and new
        line_nums = set([ i.split("Line")[-1] for i in request.form.keys() if "Line" in i ])

        # keyed by line id
        lines = { num: {} for num in line_nums }

        for num in line_nums:
            for k,v in request.form.items():
                if num in k:
                    lines[num].update({k.split("Line")[0] : v})

        # divide lines into existing and new
        existing_lines = { k: v for k,v in lines.items() if "existing" in v.keys()  }

        new_lines = {k: v for k,v in lines.items() if "existing" not in v.keys() }

        # update the existing lines
        for k,v in existing_lines.items():
            line = session.query(model.ProposalLine).filter_by(id=k).one()

            line.description = v["description"]
            line.quantity = v["quantity"]
            line.price = v["price"]
            line.total = v["total"]

        # delete the lines that removed from the form
        for line in proposal.lines:
            if str(line.id) not in existing_lines.keys():
                session.delete(line)


        # Add the new lines to the proposal
        new_line_objects = [ model.ProposalLine(**v) for k,v in new_lines.items() ]

        for line in new_line_objects:
            proposal.add_line(line)

        session.commit()
        session.flush()

        publish_event('proposal', 'edit_proposal', proposal.id)

        return redirect(url_for('view_proposal', id=proposal.id, task_id=task_id, task_name=task.name))

    else:

        return render_template('edit_proposal.html', task_id=task_id, proposal=proposal, task_name=task.name)



@app.route('/tasks/<int:task_id>/proposals', methods=['GET'])
def list_proposals(task_id):

    # if vendor user, display only their proposals;
    # if hoa user, display all the proposal submitted
    # for the task

    session = get_session()

    if flask_session["user_type"] == "Vendor":

        proposals = session.query(model.Proposal).filter(and_(model.Proposal.task_id == task_id, model.Proposal.org_id == flask_session["org_id"])).all()

    else:

        proposals = session.query(model.Proposal).filter(model.Proposal.task_id == task_id).all()

    task = session.query(model.Task).filter_by(id=task_id).one()


    return render_template('proposals_for_task.html', proposals=proposals, user_type=flask_session["user_type"], task_id=task_id, task_name=task.name)


@app.route('/tasks/<int:id>/edit', methods=['GET', 'POST'])
def edit_task(id):

    session = get_session()

    task = session.query(model.Task).filter_by(id=id).one()

    if request.method == 'POST':

        img_remove_list = request.form.getlist("removeImage")

        if len(img_remove_list) > 0:

            task.remove_images(img_remove_list)

            s3 = boto3.client("s3")

            for i in img_remove_list:
                s3.delete_object(Bucket="condoly-74huhf8423u36d", Key=f"task-images/{task.id}/" + i)

        for i in request.files.getlist("fileUpload"):

            try:

                task.add_image(i.filename)

            except:
                continue

        for i in request.files.getlist("fileUpload"):

            try:

                i.save(i.filename)

                upload_file(i.filename, "condoly-74huhf8423u36d", f"task-images/{task.id}/" + i.filename)

            except:
                continue


        date_str = request.form["dueDateField"]
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')

        task.due_by = date_obj
        task.description = request.form["taskDescription"]
        task.category = request.form["taskCategory"]

        session.commit()

        publish_event('task', 'edit_task', task.id)

        return redirect(f'/tasks/{task.id}')

    else:

        return render_template('edit_task.html', task=task)



@app.route('/tasks/<int:id>/messages', methods=['GET'])
def messages(id):

    session = get_session()


    query = f'''select
                t.*,
                max(t.id)
                from task_messages t where t.task_id = {id}
                and t.receiving_org_id = {flask_session['org_id']}
                group by t.vendor_org_id'''


    res = session.execute(query).fetchall()

    task = session.query(model.Task).filter_by(id=id).one()


    return render_template('messages.html', task_id=id, task_name=task.name, messages=res)

@app.route('/tasks/<int:task_id>/messages/create', methods=['POST'])
def add_task_message(task_id):

    session = get_session()

    new_message = model.TaskMessage(task_id,
                                    current_user.id,
                                    request.form["vendor_id"],
                                    request.form["sending_org_id"],
                                    request.form["receiving_org_id"],
                                    request.form["content"])

    session.add(new_message)

    session.commit()
    session.flush()

    #publish_event('message', 'new_message', new_message.id)

    return redirect(url_for('conversations', task_id=task_id, vendor_id=request.form["vendor_id"]))


@app.route('/tasks/<int:task_id>/messages/<int:vendor_id>', methods=['GET'])
def conversations(task_id, vendor_id):

    session = get_session()

    task = session.query(model.Task).filter_by(id=task_id).one()

    messages = session.query(model.TaskMessage).filter(and_(model.TaskMessage.task_id==task_id,model.TaskMessage.vendor_org_id==vendor_id)).all()

    return render_template('conversation.html',
                            messages=messages,
                            task_id=task_id,
                            vendor_id=vendor_id,
                            this_org=flask_session["org_id"],
                            user_type=flask_session["user_type"],
                            hoa_id=task.org_id,
                            task_name=task.name)

@app.route('/proposals', methods=['GET'])
def proposals():

    return render_template('proposals.html')

@app.route('/tasks/<int:task_id>/proposals/<int:id>', methods=['GET'])
def view_proposal(id, task_id):

    session = get_session()

    proposal = session.query(model.Proposal).filter_by(id=id).one()

    return render_template('view_proposal.html', proposal=proposal, user_type=flask_session["user_type"])

@app.route('/tasks/<int:task_id>/proposals/<int:id>', methods=['POST'])
def proposal_action(id, task_id):

    session = get_session()

    proposal = session.query(model.Proposal).filter_by(id=id).one()

    action = request.form["action"]

    if action == "hoa-request-update":

        proposal.requested_updates = request.form["requestedUpdates"]
        proposal.status = "Updates Requested"

    elif action == "hoa-accept":

        proposal.status = "Accepted"
        proposal.task.status = "In Progress"

        proposal.task.select_proposal(proposal)

    elif action ==  'hoa-decline':

        proposal.status = "Declined"

    elif action == 'vendor-withdraw':

        proposal.status = "Withdrawn"


    session.commit()

    session.flush()

    publish_event('proposal', action, proposal.id)

    return redirect(url_for('view_proposal', id=id, task_id=task_id))

@app.route('/tasks/<int:task_id>/proposals/<int:id>/vendorResponse', methods=['POST'])
def vendor_response(id, task_id):

    session = get_session()

    proposal = session.query(model.Proposal).filter_by(id=id).one()

    proposal.status = request.form["vendorResponse"]

    proposal.vendor_response = request.form["vendorResponseComments"]

    proposal.vendor_response_date = datetime.date.today().strftime("%Y-%m-%d")

    session.commit()

    session.flush()

    publish_event('proposal', 'vendor_response', proposal.id)

    return redirect(url_for('view_proposal', id=id, task_id=task_id))


@app.route('/history', methods=['GET'])
def history():

    return render_template('history.html')


@app.route('/tasks/<int:id>', methods=['GET'])
def view_task(id):

    session = get_session()

    task = session.query(model.Task).filter_by(id=id).one()

    downloaded_images = []

    if task.images:

        # download the images, save locally
        s3 = boto3.client('s3')

        image_names = task.get_images()

        for i in image_names:

            filename = str(id) + "_" + i

            s3.download_file("condoly-74huhf8423u36d", f"task-images/{id}/{i}", filename)

            os.rename(filename, f'static/{filename}')

            downloaded_images.append(filename)

    if len(downloaded_images) > 0:

        first_img = downloaded_images[0]

    else:

        first_img = None

    if len(downloaded_images) > 1:

        other_img = downloaded_images[1:]

    else:

        other_img = []


    return render_template('view_task.html',
                            task=task,
                            user_type=flask_session["user_type"],
                            this_org=flask_session["org_id"],
                            first_img=first_img,
                            other_img=other_img)


@app.route('/user', methods=['GET'])
def user_profile():

    return render_template('user_profile.html',
                            user=current_user,
                            user_type=flask_session['user_type'],
                            email_prefs=current_user.get_email_preferences(flask_session['user_type']))

@app.route('/user/edit', methods=['GET', 'POST'])
def edit_user():

    session = get_session()

    if request.method == 'POST':

        user = session.query(model.User).filter_by(id=current_user.id).one()

        user.first_name = request.form["firstName"]
        user.last_name = request.form["lastName"]
        user.email = request.form["email"]

        print(request.form)

        user.set_email_preferences(request.form)

        session.commit()

        session.flush()

        return redirect(url_for('user_profile'))

    else:

        return render_template('edit_user.html',
                               user=current_user,
                               user_type=flask_session['user_type'],
                               email_prefs=current_user.get_email_preferences(flask_session['user_type']))

@app.route('/user/password', methods=['GET', 'POST'])
def edit_password():

    session = get_session()

    if request.method == 'POST':

        user = session.query(model.User).filter_by(id=current_user.id).one()

        user.set_password(request.form["password"])
        session.commit()

        return render_template('user_profile.html', user=user, user_type=flask_session['user_type'])

    else:

        return render_template('edit_password.html')

@app.route('/organization', methods=['GET'])
def org_profile():

    session = get_session()

    org = session.query(model.Organization).filter_by(id=flask_session["org_id_permanent"]).one()

    target_zips = session.query(model.TargetZip).filter_by(vendor_id=flask_session["org_id_permanent"]).all()

    return render_template('org_profile.html',
                           org=org,
                           user_type=flask_session['user_type'],
                           target_zips=target_zips,
                           users=[])


@app.route('/admin/organization/<org_id>', methods=['GET'])
def admin_view_org(org_id):

    session = get_session()

    org = session.query(model.Organization).filter_by(id=org_id).one()

    users = session.query(model.User).join(model.UserOrg, model.User.id==model.UserOrg.user_id).filter(model.UserOrg.organization_id==org.id).all()

    target_zips = session.query(model.TargetZip).filter_by(vendor_id=org_id).all()

    return render_template('org_profile.html',
                            org=org,
                            user_type=flask_session['user_type'],
                            users=users,
                            target_zips=target_zips)


@app.route('/admin/vendor/approvals', methods=['GET'])
def admin_vendor_approvals():

    session = get_session()

    orgs = session.query(model.Organization).filter_by(admin_approved="false").all()

    return render_template('admin_vendor_approval.html', orgs=orgs)

@app.route('/admin/vendor/approve/<org_id>', methods=['GET'])
def admin_approve_vendor(org_id):

    session = get_session()

    org = session.query(model.Organization).filter_by(id=org_id).one()

    org.admin_approved = 'true'

    session.commit()

    return redirect(url_for('admin_vendor_approvals'))

@app.route('/admin/organization/<org_id>/edit', methods=['GET', 'POST'])
@app.route('/organization/edit', defaults={'org_id': None}, methods=['GET', 'POST'])
def edit_org(org_id):

    session = get_session()

    if org_id is None:

        org = session.query(model.Organization).filter_by(id=flask_session["org_id_permanent"]).one()

    else:

        org = session.query(model.Organization).filter_by(id=org_id).one()

    if request.method == 'POST':


        org.name = request.form["name"]
        org.org_type = request.form["orgType"]
        org.street_address = request.form["address"]
        org.city = request.form["city"]
        org.state = request.form["state"]
        org.zipcode = request.form["zipcode"]
        org.categories = ', '.join(request.form.getlist("taskCategory"))

        if org.org_type == 'Vendor':

            org.admin_approved = 'false'

            # get any current target zips
            target_zips_existing = session.query(model.TargetZip).filter_by(vendor_id=org.id).all()

            # remove them
            for tz in target_zips_existing:
                session.delete(tz)


            # get the target zips from the form
            target_zips = request.form.getlist("targetZip1")
            target_radius = request.form.getlist("radius1")

            tzr = list(zip(target_zips,target_radius))

            tzr_objs = [ model.TargetZip(flask_session["org_id"], i[0], i[1]) for i in tzr if i[0] != ''  ]

            for obj in tzr_objs:
                session.add(obj)


        session.commit()

        session.flush()

        if org_id is None:

            return redirect(url_for('org_profile'))

        else:

            return redirect(url_for('admin_view_org', org_id=org_id))

    else:

        if flask_session["user_type"] == "Vendor" or flask_session["user_type"] == "admin":

            if org.categories == None:

                categories = []

            else:

                categories = org.categories.split(', ')


            target_zips = session.query(model.TargetZip).filter_by(vendor_id=org.id).all()


            return render_template('edit_org.html',
                                   org=org,
                                   categories=categories,
                                   user_type=flask_session['user_type'],
                                   target_zips=target_zips)

        else:

            return render_template('edit_org.html', org=org, user_type=flask_session['user_type'])


@app.route('/admin/hoa/<target>', methods=['GET', 'POST'])
def admin_hoa_view_dispatch(target):

    session = get_session()

    orgs = session.query(model.Organization).filter_by(org_type='HOA').all()

    return render_template("admin_list_hoa_orgs.html", orgs=orgs, target=target)

@app.route('/admin/vendor/<status>', methods=['GET', 'POST'])
def admin_vendor_view_dispatch(status):

    session = get_session()

    orgs = session.query(model.Organization).filter_by(org_type='Vendor').all()

    return render_template("admin_list_vendor_orgs.html", orgs=orgs, status=status)


@app.route('/admin/hoa/<target>/<org_id>', methods=['GET'])
def admin_hoa_org_dispatch(target, org_id):

    session = get_session()

    flask_session['org_id'] = org_id
    flask_session['org_name'] = session.query(model.Organization).filter_by(id=org_id).one().name


    return redirect(url_for(target))


@app.route('/admin/vendor/<status>/<org_id>', methods=['GET'])
def admin_vendor_org_dispatch(status, org_id):

    session = get_session()

    flask_session['org_id'] = org_id
    flask_session['org_name'] = session.query(model.Organization).filter_by(id=org_id).one().name

    return redirect(url_for('vendor_tasks', status=status))

@app.route('/admin/org-switch/<org_id>', methods=['GET'])
def switch_to_org(org_id):

    session = get_session()

    flask_session['org_id'] = org_id

    org = session.query(model.Organization).filter_by(id=org_id).one()

    flask_session['org_name'] = org.name

    if org.org_type == 'HOA':

        return redirect(url_for('open_tasks'))

    else:

        return redirect(url_for('vendor_tasks'))

@app.route('/admin/list-orgs/<org_type>', methods=['GET'])
def list_orgs(org_type):

    session = get_session()

    orgs = session.query(model.Organization).filter_by(org_type=org_type).all()

    return render_template("admin_list_orgs.html", orgs=orgs)

@app.route('/admin/task-approvals/<status>', methods=['GET'])
def admin_task_approvals(status):

    session = get_session()

    tasks = session.query(model.Task).filter_by(status='Open',admin_approved=status).order_by(model.Task.created_at.desc()).all()

    return render_template("admin_task_approval.html", tasks=tasks)

@app.route('/admin/task-approvals/manage/<task_id>', methods=['GET', 'POST'])
def admin_manage_task(task_id):

    session = get_session()

    task = session.query(model.Task).filter_by(id=task_id).one()

    if request.method == 'GET':

        vendors = session.query(model.Organization).filter_by(org_type='Vendor').all()

        if len(task.vendors_assigned) == 0:

            current_vendors = []

        else:

            current_vendors = [ x.id for x in task.vendors_assigned ]

        return render_template('admin_manage_task.html', task=task, vendors=vendors, current_vendors=current_vendors)

    else:

        vendor_ids = request.form.getlist("taskAssignedVendors")

        vendors = session.query(model.Organization).filter(model.Organization.id.in_(vendor_ids)).all()

        task.vendors_assigned = vendors

        task.admin_approved = request.form["adminApproved"]

        session.commit()
        session.flush()

        return redirect(url_for('admin_manage_task', task_id=task.id))

def publish_event(entity_type, event, entity_id):

    sqs = boto3.client('sqs', region_name='us-east-1')

    queue_url = app.config["CONDOLY_MESSAGE_BUS_URL"]

    response = sqs.send_message(
            QueueUrl=queue_url,
            MessageAttributes={"entity_type": {"DataType": "String", "StringValue": entity_type},
                                "event": {"DataType": "String", "StringValue": event},
                                "entity_id": {"DataType": "String", "StringValue": str(entity_id)}},
            MessageBody=("Here's a new event from Condoly."))


if __name__ == '__main__':

    app.run(host='0.0.0.0', debug=True)
