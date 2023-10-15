import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
import itertools


def soupify(url):
    page = requests.get(url)
    soup = bs(page.content, "html.parser")
    return soup


def event_parser_initial(url):

    # _base_url = 'https://www.pdga.com/'

    soup = soupify(url)
    table = soup.select('div[class*="table-container"]')[0]

    odd_rows = table.select('tr[class*="odd"]')
    even_rows = table.select('tr[class*="even"]')

    rows = [x for x in itertools.chain.from_iterable(itertools.zip_longest(odd_rows,even_rows)) if x]
    
    parsings = []
    for row in rows:
        if row.select('td[class*="views-field views-field-Classification"]')[0].text.strip() == 'Pro':
            event_link = row.select('a[href*="/tour/event/"]')[0]
            event_url = _base_url + event_link['href']
            event_official_name = event_link.text
            event_number = int(event_url.split('/')[-1])
            parsings.append((event_url, event_official_name, event_number))
            
    if len(parsings) > 1:
        print('There may be an issue as we parsed more than one item that matches.')

    event = parsings[0]

    return event[0], event[1], event[2]


def events_list(
        year,
        tier=['ES', 'M'], 
        classification=['Pro'],
        base_url='https://www.pdga.com/tour/search',
    ):

    tier_str = '&'.join([f'Tier[]={t}' for t in tier])
    classification_str = '&'.join([f'Classification[]={c}' for c in classification])
    url = f'{base_url}?date_filter[min][date]={year}-01-01&date_filter[max][date]={year}-12-31&{tier_str}&{classification_str}'

    soup = soupify(url)
    events_with_links_raw = soup.select('a[href*="/tour/event/"]')
    # for e in events_with_links_raw:
    #     print(e)
    events_with_links = [(e.text,'https://www.pdga.com/'+e['href']) for e in events_with_links_raw if e.text] #   and '<img' not in e

    return events_with_links


def parse_rows(row):
    if row.select('td[class*="par"]'):
        score = row.select('td[class*="par"]')[0].text
    elif row.select('td[class*="dnf"]'):
        score = "DNF"
    else:
        score = "ERROR"
    result = { # could also do round scores, round ratings, and total score
        'Place': int(row.select_one('td[class*="place"]').text),
        'Player': row.select_one('td[class*="player"]').text,
        'PDGA Number': int(row.select_one('td[class*="pdga-number"]').text),
        'Player Rating': int(row.select_one('td[class*="player-rating"]').text),
        'Score': score,
    }
    return result


def event_parser_results(event):
    
    soup = soupify(event.event_url)
    soup_table = soup.select('div[class*="leaderboard"]')[0]
    results_table_raw = soup_table.select('div[class*="table-container"]')[0]
    odd_rows = results_table_raw.select('tr[class*="odd"]')
    even_rows = results_table_raw.select('tr[class*="even"]')
    results_raw = [x for x in itertools.chain.from_iterable(itertools.zip_longest(odd_rows,even_rows)) if x]
    results_list = [parse_rows(row) for row in results_raw]
    results_df = pd.DataFrame(data=results_list) #.set_index('Place')
        
    return results_df


def total_scorer(results, players, verbose=0):
    
    players_dict = {
        player: {
            'number_of_events': 0,
            'total_score': 0,
            'average_score': 0
        } for player in players
    }
    
    for event, results_df in results.items():
        for player in players:
            if player in results_df.Player.values:
                score = results_df[results_df.Player == player].Place.values[0]
                if score == 'DNF':
                    score = max([x for x in results_df.Place.values if x.isnumeric()]) + 1
                    in_event = 1
                    
                elif score == 'ERROR':
                    if verbose:
                        print(f'Something went wrong for {player} in the {event} event.')
                    in_event = 0
                    
                else:
                    in_event = 1
                    
                players_dict[player]['total_score'] += int(score)
                players_dict[player]['number_of_events'] += in_event
                players_dict[player][event] = score
            else:
                if verbose:
                    print(f'{player} did not play in the {event}.')
    
    for player in players:
        if players_dict[player]['number_of_events'] != 0:
            avg_score = players_dict[player]['total_score'] / players_dict[player]['number_of_events']
            players_dict[player]['average_score'] = round(avg_score, 3)
        else:
            players_dict[player]['average_score'] = 0
            
    return players_dict


def print_output(players_dict):
    for player, stats in players_dict.items():
        separator = '*' * (len(player)+6)
        print(f"""
{separator}
-- {player} --
{separator}
Number of events: {stats['number_of_events']}
Total score: {stats['total_score']}
Average score: {stats['average_score']}
""")

    pass


class Player:
    
    def __init__(self, name):
        self.name = name.strip().title()
        self.first_name = self.name.split(' ')[0]
        self.last_name = self.name.split(' ')[-1]
        self._base_url = 'https://www.pdga.com/players'
        self.search_url = f'{self._base_url}?FirstName={self.first_name}&LastName={self.last_name}'
        
        soup = soupify(self.search_url)
        
        self.pdga_number = int(soup.select('td[class*="pdga-number"]')[0].text.strip())
        self.rating = int(soup.select('td[class*="Rating"]')[0].text.strip())
        
        self.pdga_url = f'https://www.pdga.com/player/{self.pdga_number}'
        
    def __repr__(self):
        return self.name


class EventSearch:

    def __init__(self, search_name, year, tier=['ES', 'M'], classification=['Pro']):

        self.search_name = search_name.strip()
        self.year = int(year)
        
        self._base_url = 'https://www.pdga.com/tour/search?'
        self._event_name = self.search_name.replace(' ','%20')
        self._min_date = f'{self.year}-01-01'
        self._max_date = f'{self.year}-12-31'
        self._tier = tier
        self._classification = classification

        _tier_search = '&'.join([f'Tier[]={t}' for t in self._tier])
        _classification_search = '&'.join([f'Classification[]={c}' for c in self._classification])

        self.search_url = self._base_url \
                            + 'OfficialName=' + self._event_name \
                            + '&date_filter[min][date]=' + self._min_date \
                            + '&date_filter[max][date]=' + self._max_date \
                            + '&' + _tier_search \
                            + '&' + _classification_search

        print(f'Searching here: {self.search_url}')


    def search(self):
        
        soup = soupify(self.search_url)

        event_details = event_parser_initial(self.search_url)
        
        self.event_url = event_details[0]
        self.event_official_name = event_details[1]
        self.event_number = event_details[2]
        
        return event_details


    def getEventName(self):
        return self.event_official_name


    def getEventNumber(self):
        return self.event_number


class Event:

    def __init__(self, name, year, tier=['ES', 'M'], classification=['Pro']):
        # super(Event, self).__init__(**kwargs)
        self.name = name.strip()
        self.year = int(year)
        
        self._base_url = 'https://www.pdga.com/tour/search?'
        self._event_name = self.name.replace(' ','%20')
        self._min_date = f'{self.year}-01-01'
        self._max_date = f'{self.year}-12-31'
        self._tier = tier
        self._classification = classification

        _tier_search = '&'.join([f'Tier[]={t}' for t in self._tier])
        _classification_search = '&'.join([f'Classification[]={c}' for c in self._classification])

        self.search_url = self._base_url \
                            + 'OfficialName=' + self._event_name \
                            + '&date_filter[min][date]=' + self._min_date \
                            + '&date_filter[max][date]=' + self._max_date \
                            + '&' + _tier_search \
                            + '&' + _classification_search

        print(f'Searching here: {self.search_url}')
        
        soup = soupify(self.search_url)

        event_details = event_parser_initial(self.search_url)
        
        self.event_url = event_details[0]
        self.event_official_name = event_details[1]
        self.event_number = event_details[2]

        self.results_df = event_parser_results(self)


    def __repr__(self):
        return self.event_official_name


    def save_event_results(self, file_path=''):

        file_name = f'Results_{self.event_official_name.replace(" ","-")}.csv'

        if len(self.results_df) == 0:
            print(f'Results for "{self}" do not exist.')

        else:
            self.results_df.to_csv(file_path + file_name)
            print(f'{file_name} has been saved.')

        setattr(self, 'file_path', file_path)
        setattr(self, 'file_name', file_name)

    
