from bs4 import BeautifulSoup
import os, csv
import requests
from time import strptime, strftime

BASE_URL = "https://www.cmu.edu/"

SCHOOL_URLS = [
	"https://www.cmu.edu/events/"						# campus wide
	"https://events.time.ly/0qe3bmk"					# Mellon School of Science
	"https://www.cs.cmu.edu/calendar"					# School of Computer Science
	"https://www.cs.cmu.edu/scs-seminar-series"			# All seminars in GHC have food!
	"https://www.cmu.edu/dietrich/about/calendar/"		# Dietrich College of H & SS
	"https://soa.cmu.edu/calendar/"						# School of Architecture
	"https://www.cmu.edu/piper/calendar/"				# The Piper
	"https://www.heinz.cmu.edu/about/events"			# Heinz College
	"http://www.cfa.cmu.edu/pages/calendar"				# College of Fine Arts
	"http://www.cs.cmu.edu/~aiseminar/"					# AI seminar
]

# keyword to look for when looking at an event - should contain at least one of these
keywords = ["food", "lunch", "free", "seminars", "thesis", "proposal"]

def check_for_food(label, event_time):
	"""Check if event (potentially) has free food, based on label and event time.

	Label must contain one of the keywords or time should be between 11am and 12pm.
	"""
	if len([word for word in keywords if word in label.lower()]) > 0:
		return True
	if (event_time.tm_hour >= 11 and event_time.tm_hour <= 12):
		return True
	return False


def print_event(title, event_time, location, event_link):
	"""Print the event information to std output."""
	time_str = strftime("%b %d %I:%M%p", event_time)
	print(title + "\t" + time_str + "\t" + location + "\t" + event_link)


def scs_food():
	"""Search for events in SCS - https://www.cs.cmu.edu/calendar"""
	print("*** School of Computer Science ***")
	base_url = "https://cs.cmu.edu"
	url = base_url + "/calendar/"
	response = requests.get(url)
	soup = BeautifulSoup(response.text, "html.parser")
	for event in soup.find_all("a", class_="event__link-wrapper"):
		label = event.find("div", class_="event__label").get_text()
		time_tag = event.find("time")
		time_string = " ".join([t.get_text() for t in time_tag.children])
		try:
			event_time = strptime(time_string, "%b %d %I:%M%p")
		except ValueError:
			event_time = strptime(time_string, "%b %d %I%p")
		if check_for_food(label, event_time):
			title = event.find("h3", class_="event__title").get_text()
			location = " ".join([l.get_text() for l in event.find_all("div", class_="field-item")])
			event_link = base_url + event.get("href")
			print_event(title, event_time, location, event_link)
	print("******")


if __name__ == '__main__':
	print("Found food at these events ^.^")
	scs_food()