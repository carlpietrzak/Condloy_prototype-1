import datetime

categories = ["Appliance Repair",
              "Blacktop Sealcoating",
              "Cable / Internet",
              "Carpet Cleaning",
              "Cleaning",
              "Construction Contractors",
              "Electricians",
              "Elevator Repair/Maintenance",
              "Environmental Consulting",
              "FHA Certification",
              "Fencing",
              "Fire Safety Equipment",
              "Garage Door Repair",
              "Gutter Repair/Maintenance",
              "Handyman",
              "Heating / AC Repair",
              "Inspections/Reserve Studies",
              "Intercom/Entry Systems",
              "Land Surveying",
              "Landscaping/Snow Removal",
              "Laundry Service",
              "Locksmith",
              "Mediation Services",
              "Packaged Maintenance",
              "Pest Control",
              "Plumbing",
              "Real Estate Tax Appeals",
              "Restoration (Water / Smoke Damage)",
              "Roofing",
              "Tuck Pointing / Masonry",
              "Other"]

def reformat_date_string(initial_string):

    date_obj = datetime.datetime.strptime(initial_string, '%Y-%m-%d')

    return date_obj.strftime('%B %d, %Y')
