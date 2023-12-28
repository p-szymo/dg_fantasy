from dg_fantasy_functions import events_list, Event


event_details = events_list(2023)

events = []
events_errors = []

for event_name,link in event_details:
	
    try:
        events.append(Event(name=event_name, url=link))
    except:
        print(link)
        events_errors.append(link)

    time.sleep(1)