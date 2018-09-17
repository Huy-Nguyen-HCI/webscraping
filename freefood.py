from bs4 import BeautifulSoup
import os, csv
import requests
from time import strptime, strftime
from datetime import datetime, timedelta
from tabulate import tabulate
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

SCHOOL_URLS = [
	"https://www.cmu.edu/events/",								# campus wide
	"https://events.time.ly/0qe3bmk",							# Mellon School of Science
	"https://www.cs.cmu.edu/calendar",							# School of Computer Science
	"https://www.cs.cmu.edu/scs-seminar-series",				# All seminars in GHC have food!
	"https://www.cmu.edu/dietrich/about/calendar/",				# Dietrich College of H & SS
	"https://soa.cmu.edu/calendar/",							# School of Architecture
	"https://www.cmu.edu/piper/calendar/",						# The Piper
	"https://www.heinz.cmu.edu/about/events",					# Heinz College
	"http://www.cfa.cmu.edu/pages/calendar",					# College of Fine Arts
	"http://www.cs.cmu.edu/~aiseminar/",						# AI seminar
	"https://engineering.cmu.edu/news-events/events/index.html"	# College of Engineering
]

"""if modifying these scopes, delete the file token.json."""
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'

"""time format for parsing"""
TIME_FORMAT = "%b %d %I:%M%p"

"""keyword to look for when looking at an event - should contain at least one of these"""
KEYWORDS = ["food", "lunch", "free", "seminars", "thesis", "proposal"]

"""A table of all chosen events, sorted by time, with the following columns: name, time, location, url"""
chosen_events = []

def check_for_food(label, event_time):
	"""Check if event (potentially) has free food, based on label and event time.

	Label must contain one of the keywords or time should be between 11am and 12pm.
	"""
	if len([word for word in KEYWORDS if word in label.lower()]) > 0:
		return True
	if (event_time.tm_hour >= 11 and event_time.tm_hour <= 12):
		return True
	return False


def print_event(title, event_time, location, event_link):
	"""Print the event information to std output."""
	time_str = strftime(TIME_FORMAT, event_time)
	print(title + "\t" + time_str + "\t" + location + "\t" + event_link)


def filter_time_string(str):
	return str.replace(" ", "").replace("\t", "").replace("\n", "")


def get_time_from_string(time_string):
	try:
		return strptime(time_string, TIME_FORMAT)
	except ValueError:
		return strptime(time_string, "%b %d %I%p")


def fetch_calendar(calendar_id):
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    # Call the Calendar API
    start = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    end = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
    events_result = service.events().list(calendarId=calendar_id, timeMin=start,
                                        singleEvents=True, timeMax=end,
                                        orderBy='startTime').execute()
    return events_result.get('items', [])


def scs_food():
	"""Search for events in SCS"""
	affiliation = "School of Computer Science"
	base_url = "http://cs.cmu.edu"
	url = base_url + "/calendar/"
	response = requests.get(url)
	soup = BeautifulSoup(response.text, "html.parser")
	for event in soup.find_all("a", class_="event__link-wrapper"):
		label = event.find("div", class_="event__label").get_text()
		time_tag = event.find("time")
		time_string = " ".join([t.get_text() for t in time_tag.children])
		event_time = get_time_from_string(time_string)
		if check_for_food(label, event_time):
			title = event.find("h3", class_="event__title").get_text()
			location = " ".join([l.get_text() for l in event.find_all("div", class_="field-item")])
			event_link = base_url + event.get("href")
			chosen_events.append([title, event_time, location, event_link, affiliation])


def mellon_science_food():
	"""Search for events in Mellon School of Science"""
	affiliation = "Mellon School of Science"
	url = "http://events.time.ly/0qe3bmk"
	response = requests.get(url)
	soup = BeautifulSoup(response.text, "html.parser")
	for event in soup.find_all("a", class_="timely-event"):
		container = event.find("div", class_="timely-title-text")
		title = container.find("span").get_text()
		time_string = "{} {} {}".format(
			event.find("div", class_="timely-month").get_text(),
			event.find("div", class_="timely-day").get_text(),
			filter_time_string(container.find("div", class_="timely-start-time").get_text())
		)
		event_time = get_time_from_string(time_string)
		if check_for_food(title, event_time):
			location = container.find("span", class_="timely-venue").get_text()
			event_link = event.get("href")
			chosen_events.append([title, event_time, location, event_link, affiliation])


def dietrich_food():
	"""Search for events in Dietrich College of Humanities and Social Sciences"""
	affiliation = "Dietrich"
	google_calendar_id = "t6ebuir6klabea3q87b5qjs360@group.calendar.google.com"
	for event in fetch_calendar(google_calendar_id):
		# print(event["start"].get("dateTime", event['start'].get("date")), event['summary'])
		event_time = event["start"].get("dateTime", event['start'].get("date")).replace("-04:00", "")
		event_time = strptime(event_time, '%Y-%m-%dT%H:%M:%S')
		title = event["summary"]
		if check_for_food(title, event_time):
			location = event["location"]
			event_link = event["htmlLink"]
			chosen_events.append([title, event_time, location, event_link, affiliation])

	

def print_events():
	output = sorted(chosen_events, key=lambda event: event[1])
	for event in output:
		event[1] = strftime(TIME_FORMAT, event[1])
	print("Found food at these events ^.^")
	print(tabulate(output, headers=["Name", "Time", "Location", "Url", "Affiliation"]))


if __name__ == '__main__':
	# scs_food()
	# mellon_science_food()
	dietrich_food()
	print_events()