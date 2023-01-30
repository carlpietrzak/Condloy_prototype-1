import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app


class Task:

    def __init__(self, name, category, description, due_by, status, user_id, org_id):
        self.name = name
        self.category = category
        self.description = description
        self.due_by = due_by
        self.status = status
        self.user_id = user_id
        self.org_id = org_id
        self.created_at = datetime.datetime.now()
        self.proposals = list()
        self.task_msgs = list()
        self.images = None
        self.vendors_assigned = []
        self.admin_approved = 'false'
        self.accepted_proposal_id = None

    def select_proposal(self, proposal):
        if proposal in self.proposals:
            self.accepted_proposal_id = proposal.id


    def add_message(self, message):

        self.task_msgs.append(message)

    def add_proposal(self, proposal):

        self.proposals.append(proposal)

    def assign_vendor(self, vendor):

        self.vendors_assigned.append(vendor)

    def add_image(self, image_file):

        if self.images:

            self.images += f',{image_file}'

        else:

            self.images = image_file

    def get_images(self):

        if self.images:

            return self.images.split(',')

    def remove_images(self, img_list):
 
        current_images = self.get_images()

        updated_images = list(set(current_images) - set(img_list))

        self.images = ','.join(updated_images)



class Proposal:

    def __init__(self, content, cost_estimate, time_estimate_days, time_estimate_hours, status, created_by, org_id):
        self.content = content
        self.cost_estimate = cost_estimate
        self.time_estimate_days = time_estimate_days
        self.time_estimate_hours = time_estimate_hours
        self.status = status
        self.created_by = created_by
        self.org_id = org_id
        self.created_at = datetime.datetime.now()
        self.lines = list()

    def add_line(self, line):
        self.lines.append(line)


class TaskMessage:

    def __init__(self, task_id, sending_user_id, vendor_org_id, sending_org_id, receiving_org_id, content):
        self.task_id = task_id
        self.sending_user_id = sending_user_id
        self.vendor_org_id = vendor_org_id
        self.sending_org_id = sending_org_id
        self.receiving_org_id = receiving_org_id
        self.content = content


class User(UserMixin):

    def __init__(self, first_name, last_name, email):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.email_create_task = "true"
        self.email_new_available_task = "true"
        self.email_edit_task = "true"
        self.email_proposal_accepted = "true"
        self.email_status_completed = "true"
        self.email_new_proposal = "true"
        self.email_edit_proposal = "true"
        self.email_hoa_request_updates = "true"

    def set_password(self, password):
                
        """Create hashed password."""
        self.password = generate_password_hash(
            password,
            method='sha256'
        )

    def check_password(self, password):
        """Check hashed password."""
        
        return check_password_hash(self.password, password)


    def _email_pref_map(self):

        email_prefs = [{"name": "Proposal Accepted", "value": self.email_proposal_accepted},
                       {"name": "Task Completed", "value": self.email_status_completed },
                       {"name": "New Proposal Created", "value": self.email_new_proposal},
                       {"name": "Proposal Edited", "value": self.email_edit_proposal},
                       {"name": "Proposal Updates Requested", "value": self.email_hoa_request_updates}]

        hoa_prefs = [{"name": "Task Created", "value": self.email_create_task},
                     {"name": "Task Edited", "value": self.email_edit_task}]


        vendor_prefs = [{"name": "New Available Tasks", "value": self.email_new_available_task}]

        return (email_prefs, hoa_prefs, vendor_prefs)


    def get_email_preferences(self, user_type):

        email_prefs = self._email_pref_map()

        if user_type == 'HOA':

            return email_prefs[0] + email_prefs[1]

        elif user_type == 'Vendor':

            return email_prefs[0] + email_prefs[2]

    def set_email_preferences(self, request_dict):

        if "Proposal Accepted" in request_dict.keys():

            self.email_proposal_accepted = 'true'

        else:

            self.email_proposal_accepted = 'false'

        if 'Task Completed' in request_dict.keys():

            self.email_status_completed = 'true'

        else:

            self.email_status_completed = 'false'
            
        if 'New Proposal Created' in request_dict.keys():

            self.email_new_proposal = 'true'

        else:

            self.email_new_proposal = 'false'
         
        if 'Proposal Edited' in request_dict.keys():

            self.email_edit_proposal = 'true'

        else:

            self.email_edit_proposal = 'false'

        if 'Proposal Updates Requested' in request_dict.keys():

            self.email_hoa_request_updates = 'true'

        else:

            self.email_hoa_request_updates = 'false'

        if 'Task Created' in request_dict.keys():

            self.email_create_task = 'true'

        else:

            self.email_create_task = 'false'

        if 'Task Edited' in request_dict.keys():

            self.email_edit_task = 'true'

        else:

            self.email_edit_task = 'false'

        if 'New Available Tasks' in request_dict.keys():

            self.email_new_available_task = 'true'

        else:

            self.email_new_available_task = 'false'



    def __repr__(self):
                
        return '<User {}>'.format(self.first_name + " " + self.last_name)


class Organization:

    def __init__(self, name, org_type):
        self.name = name
        self.org_type = org_type
        self.admin_approved = 'false'
        self.approval_type = 'new'


class UserOrg:

    def __init__(self, user_id, org_id):
        self.user_id = user_id
        self.organization_id = org_id

class ProposalLine:

    def __init__(self, description, quantity, price, total):
        self.description = description
        self.quantity = quantity
        self.price = price
        self.total = total

class TargetZip:

    def __init__(self, vendor_id, zipcode, max_distance):
        self.vendor_id = vendor_id
        self.zipcode = zipcode
        self.max_distance = max_distance

class ZipDistance:

    def __init__(self, origin, destination, distance):
        self.origin = origin
        self.destination = destination
        self.distance = distance
