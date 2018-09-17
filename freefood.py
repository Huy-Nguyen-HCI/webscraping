from bs4 import BeautifulSoup, Tag, NavigableString
import os, csv
import requests
from datetime import datetime, timedelta
from tabulate import tabulate
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

SCHOOL_URLS = [
	"https://www.cs.cmu.edu/scs-seminar-series",				# All seminars in GHC have food!
	"https://www.cmu.edu/piper/calendar/",						# The Piper
	"https://www.heinz.cmu.edu/about/events",					# Heinz College
	"http://www.cfa.cmu.edu/pages/calendar",					# College of Fine Arts
	"http://www.cs.cmu.edu/~aiseminar/",						# AI seminar
]

"""if modifying these scopes, delete the file token.json."""
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'

"""time format for parsing"""
TIME_FORMAT = "%b %d %I:%M%p"

"""keyword to look for when looking at an event - should contain at least one of these"""
KEYWORDS = ["food", "lunch", "free", "seminars", "thesis", "proposal"]

"""A table of all chosen events, sorted by time, with the following columns: name, time, location, url"""
chosen_events = []

# Event time range filter
START = datetime.utcnow()
END = datetime.utcnow() + timedelta(days=7)

def check_for_food(label, event_time):
	"""Check if event (potentially) has free food, based on label and event time.

	Label must contain one of the keywords or time should be between 11am and 12pm, after today.
	"""
	if event_time < START or event_time > END:
		return False
	if len([word for word in KEYWORDS if word in label.lower()]) > 0:
		return True
	if (event_time.hour >= 11 and event_time.hour <= 12):
		return True
	return False


def print_event(title, event_time, location, event_link):
	"""Print the event information to std output."""
	time_str = datetime.strftime(event_time, TIME_FORMAT)
	print(title + "\t" + time_str + "\t" + location + "\t" + event_link)


def filter_time_string(str):
	return str.replace(" ", "").replace("\t", "").replace("\n", "")


def get_time_from_string(time_string, time_format=TIME_FORMAT):
	try:
		return datetime.strptime(time_string, time_format)
	except ValueError:
		return datetime.strptime(time_string, "%b %d %I%p")


def fetch_calendar(calendar_id):
	"""Use Google Calendar Python API to get a list of events between now and 7 days later.
	For documentation refer to https://developers.google.com/calendar/v3/reference/events/list
	
	Args:
		calendar_id (str): the specified google calendar's id, used for extracting information
	
	Returns:
		events ([Event]): a list of Events in google calendar
	"""
	store = file.Storage('token.json')
	creds = store.get()
	if not creds or creds.invalid:
	    flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
	    creds = tools.run_flow(flow, store)
	service = build('calendar', 'v3', http=creds.authorize(Http()))

	# Call the Calendar API
	events_result = service.events().list(calendarId=calendar_id, timeMin=START.isoformat() + 'Z',
	                                    singleEvents=True, timeMax=END.isoformat() + 'Z',
	                                    orderBy='startTime').execute()
	return events_result.get('items', [])


def scrape_google_calendar(affiliation, google_calendar_id):
	"""Filter the Events retrieved from the specified google calendar according to the criteria in check_for_food.

	Args:
		affiliation (str): the name of the event organizer, which will be included in the output along with the event
		google_calendar_id (str): the specified google calendar's id, used for extracting information
	"""
	for event in fetch_calendar(google_calendar_id):
		try:
			event_time = event["start"].get("dateTime", event['start'].get("date")).replace("-04:00", "")
			event_time = datetime.strptime(event_time, '%Y-%m-%dT%H:%M:%S')
			title = event["summary"]
			if check_for_food(title, event_time):
				location = event["location"]
				event_link = event["htmlLink"]
				chosen_events.append([title, event_time, location, event_link, affiliation])
		# if missing any required information, skip event
		except ValueError:
			pass
		except KeyError:
			pass


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
		event_time = get_time_from_string(time_string).replace(year=START.year)
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
		event_time = get_time_from_string(time_string).replace(year=START.year)
		if check_for_food(title, event_time):
			print(title)
			location = container.find("span", class_="timely-venue").get_text()
			event_link = event.get("href")
			chosen_events.append([title, event_time, location, event_link, affiliation])


def engineering_food():
	"""Search for events in College of Engineering"""
	affiliation = "College of Engineering"
	url = "https://engineering.cmu.edu/news-events/events/"
	time_format = "%B %d %Y %I:%M %p"
	response = requests.get(url)
	soup = BeautifulSoup(response.text, "html.parser")
	for event in soup.find_all("div", class_="event"):
		title = event.find("div", class_="title").find("p").get_text()
		date_components = event.find("div", class_="date").contents
		try:
			date = date_components[1].get_text()
			hour = date_components[3].get_text()
			# if include both start and end time, only get start time
			if "-" in hour:
				hour = hour[:hour.find("-") - 1]
			event_time = get_time_from_string("{} {}".format(date, hour), time_format).replace(year=START.year)
			if check_for_food(title, event_time):
				location = event.find("div", class_="descrip").find("p").get_text()
				event_link = url + event.find("div", class_="title").find("a").get("href")
				chosen_events.append([title, event_time, location, event_link, affiliation])
		# if no hour specified, ignore event
		except IndexError:
			pass


def ai_seminar_food():
	"""Search for events in SCS AI seminar"""
	affiliation = "School of Computer Science"
	url = "http://www.cs.cmu.edu/~aiseminar/"
	time_format = "%b %d %Y %I:%M%p"
	response = requests.get(url)
	soup = BeautifulSoup(response.text, "html.parser")
	for event in soup.find("table").find_all("tr")[1:]:
		contents = [content for content in event.contents if isinstance(content, Tag)]
		# event link may be either text or <a> tag
		try:
			link = contents[3].find("a")
			title = link.get_text()
			event_link = url + link.get("href")
		except AttributeError:
			title = contents[3].get_text()
			event_link = ""
		date_and_location = [tag for tag in contents[0] if isinstance(tag, NavigableString)]
		date = date_and_location[0].replace(",", "") + " " + date_and_location[1].replace(" ", "")
		event_time = get_time_from_string(date, time_format).replace(year=START.year)
		if check_for_food(title, event_time):
			location = date_and_location[2]
			chosen_events.append([title, event_time, location, event_link, affiliation])


def dietrich_food():
	"""Search for events in Dietrich College of Humanities and Social Sciences"""
	scrape_google_calendar("Dietrich", "t6ebuir6klabea3q87b5qjs360@group.calendar.google.com")


def architecture_food():
	"""Search for events in School of Architecture"""
	scrape_google_calendar("School of Architecture", "soa-public@andrew.cmu.edu")
	scrape_google_calendar("School of Architecture", "soa-students@andrew.cmu.edu")
	scrape_google_calendar("School of Architecture", "soa-faculty@andrew.cmu.edu")


def campus_food():
	"""Search for events in general campus"""
	scrape_google_calendar("University-wide", "andrew.cmu.edu_333234353933332d373938@resource.calendar.google.com")


def print_events():
	output = sorted(chosen_events, key=lambda event: event[1])
	for event in output:
		event[1] = datetime.strftime(event[1], TIME_FORMAT)

	headers = ["Name", "Time", "Location", "Url", "Affiliation"]

	with open("omg_food.csv", "w") as f:
		writer = csv.writer(f, delimiter=",")
		writer.writerow(headers)
		writer.writerows(output)

	print("Found food at these events ^.^")
	print(tabulate(output, headers=headers))


if __name__ == '__main__':
	scs_food()
	mellon_science_food()
	dietrich_food()
	engineering_food()
	campus_food()
	architecture_food()
	ai_seminar_food()
	print_events()