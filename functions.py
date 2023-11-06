import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
import itertools
from datetime import date as dt
import re


def soupify(url):
    page = requests.get(url)
    soup = bs(page.content, "html.parser")
    return soup


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
    events_with_links = [
        (e.text,'https://www.pdga.com'+e['href']) for e in events_with_links_raw if e.text
    ]

    return events_with_links


def players_links_list(
        base_url='https://www.pdga.com/united-states-tour-ranking-open',
    ):
    
    soup = soupify('https://www.pdga.com/united-states-tour-ranking-open')
    table = soup.select('div[class*="table"]')[0]
    player_data = table.select('a[class*="player-profile-link"]')
    # player_data = table.select('a[href*="/player/"]')
    players_links = [
        ('https://www.pdga.com'+p['href']) for p in player_data if p.text.strip()
    ]

    return players_links


def type_check(item, _type):
    if type(item) != _type:
        raise TypeError(f'{item} must be type {_type}')
    else:
        pass


class Search:

    def __init__(self, search_type, **kwargs):

        self._search_type = search_type.title()

        self._search_options = {
            'Event': {
                'base_url': 'https://www.pdga.com/tour/search',
                'reqs': [
                    'event',
                    'date_filter_min',
                    'date_filter_max',
                    'tier',
                    'classification'
                ]
            },
            'Player': {
                'base_url': 'https://www.pdga.com/players',
                'reqs':  [
                    'first_name',
                    'last_name'
                ]
            }
        }

        self._search_dict = {
            'event': {'url': 'OfficialName', 'type': str},
            'date_filter_min': {'url': 'date_filter[min][date]', 'type': str},
            'date_filter_max': {'url': 'date_filter[max][date]', 'type': str},
            'tier': {'url': 'Tier[]', 'type': list},
            'classification': {'url': 'Classification[]', 'type': list},
            'first_name': {'url': 'FirstName', 'type': str},
            'last_name': {'url': 'LastName', 'type': str}
        }

        self._base_url = self._search_options[self._search_type]['base_url']
        self._search_reqs = self._search_options[self._search_type]['reqs']

        _reqs_not_met = [x for x in self._search_reqs if x not in kwargs.keys()]

        if _reqs_not_met:
            if len(_reqs_not_met) == 1:
                s = ''
                is_are = 'is'
            else:
                s = 's'
                is_are = 'are'

            print(f"The following argument{s} {is_are} missing: {', '.join(reqs_not_met)}")

        self.input = kwargs

        self.search_string = self._base_url + '?'

        _number_of_reqs = len(self._search_reqs)

        for i, item in enumerate(self._search_reqs):

            item_input = self.input[item]
            item_url_term = self._search_dict[item]['url']
            item_req_type = self._search_dict[item]['type']

            type_check(item_input, item_req_type)

            if item_req_type == list:
                url_part = '&'.join([f'{item_url_term}={x}' for x in item_input])

            elif item_req_type == str:
                url_part = f'{item_url_term}={item_input}'

            else:
                print('Something went wrong with _search_reqs')

            self.search_string += url_part.replace(' ','%20')

            if i != _number_of_reqs - 1:
                self.search_string += '&'

        self._soup = soupify(self.search_string)


    def parser_init(self):

        soup = self._soup
        table = soup.select('div[class*="table-container"]')[0]

        odd_rows = table.select('tr[class*="odd"]')
        even_rows = table.select('tr[class*="even"]')

        rows = [x for x in itertools.chain.from_iterable(itertools.zip_longest(odd_rows,even_rows)) if x]
        
        return rows


class EventSearch(Search):

    def __init__(self, **kwargs):
        Search.__init__(self, search_type='Event', **kwargs)

        self._event_details = self.parser()
        
        self.url = self._event_details[0]
        self.official_name = self._event_details[1]
        self.pdga_event_number = self._event_details[2]


    def parser(self, _base_url = 'https://www.pdga.com'):

        rows = self.parser_init()

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


class PlayerSearch(Search):

    def __init__(self, **kwargs):
        Search.__init__(self, search_type='Player', **kwargs)

        self._player_details = self.parser()
        
        self.url = self._player_details[0]
        self.official_name = self._player_details[1]
        self.pdga_number = self._player_details[2]


    def parser(self, _base_url = 'https://www.pdga.com'):

        rows = self.parser_init()

        parsings = []
        for row in rows:
            player_link = row.select('a[href*="player/"]')[0]
            player_url = _base_url + player_link['href']
            player_official_name = player_link.text
            player_number = int(player_url.split('/')[-1])
            parsings.append((player_url, player_official_name, player_number))
                
        if len(parsings) > 1:
            print('There may be an issue as we parsed more than one item that matches.')

        player = parsings[0]

        return player[0], player[1], player[2]


class Event(EventSearch):

    def __init__(self, name=None, url=None, year=dt.today().year, tier=['ES', 'M'], classification=['Pro']):

        self.year = int(year)

        if not url:
            self._search_name = name.strip().replace(' ','%20')
            self._min_date = f'{self.year}-01-01'
            self._max_date = f'{self.year}-12-31'
            self._tier = tier
            self._classification = classification

            self._search_params = {
                'event': self._search_name,
                'date_filter_min': self._min_date ,
                'date_filter_max': self._max_date,
                'tier': self._tier,
                'classification': self._classification
            }

            EventSearch.__init__(self, **self._search_params)

        else:
            self.url = url
            self.official_name = name
            self.pdga_event_number = self.url.split('/')[-1]

        print(self.url)

        self.results_df = self.event_parser(self.url)



    def __repr__(self):
        return self.official_name


    def row_parser(self, row):
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


    def event_parser(self, url):
        
        soup = soupify(url)
        soup_table = soup.select('div[class*="leaderboard"]')[0]
        results_table_raw = soup_table.select('div[class*="table-container"]')[0]
        odd_rows = results_table_raw.select('tr[class*="odd"]')
        even_rows = results_table_raw.select('tr[class*="even"]')
        results_raw = [x for x in itertools.chain.from_iterable(itertools.zip_longest(odd_rows,even_rows)) if x]
        results_list = [self.row_parser(row) for row in results_raw]
        results_df = pd.DataFrame(data=results_list) #.set_index('Place')
            
        return results_df


    def save_event_results(self, file_path=''):

        file_name = f'Results_{self.official_name.replace(" ","-")}.csv'

        if len(self.results_df) == 0:
            print(f'Results for "{self}" do not exist.')

        else:
            self.results_df.to_csv(file_path + file_name)
            print(f'{file_name} has been saved.')

        setattr(self, 'file_path', file_path)
        setattr(self, 'file_name', file_name)


class Player(PlayerSearch):
    
    def __init__(self, search_name=None, url=None, is_active=False, year=dt.today().year):

        if search_name:
            self._search_name = search_name.strip().title()
            self._search_first_name = self._search_name.split(' ')[0]
            self._search_last_name = self._search_name.split(' ')[-1]


        if not url:
            self._base_url = 'https://www.pdga.com/players'
            self.search_url = f'{self._base_url}?FirstName={self._search_first_name}&LastName={self._search_last_name}'
        
            _soup = soupify(self.search_url)
            
            self.pdga_number = int(_soup.select('td[class*="pdga-number"]')[0].text.strip())
            
            self.url = f'https://www.pdga.com/player/{self.pdga_number}'

        else:
            self._base_url = None
            self.search_url = None
            self._search_first_name = None
            self._search_last_name = None
            self.url = url
            self.pdga_number = int(self.url.split('/')[-1])

            
        _soup = soupify(self.url)

        try:
            _name_raw = soup.select('div[class*="pane-page-title"]')[0].text.strip()
        except:
            _name_raw = re.findall('<h1>(.+) #\d{1,7}<\/h1>', str(_soup))[0]
        self.official_name = _name_raw.split('#')[0].strip()
        self.first_name = self.official_name.split(' ')[0]
        self.last_name = self.official_name.split(' ')[-1]
        rating_raw = _soup.select('li[class*="rating"]')[0].text.strip()
        self.rating = int(re.findall(' (\d{3,4}) ', rating_raw)[0])

        self.total_score = 0
        self.number_of_events = 0
        self.average_score = 0

        self.player_results = {
            year: {}
        }

        self.is_active = is_active
        

    def __repr__(self):
        return self.official_name


    def fantasy_score(self, event, verbose=0):

        player = self.official_name
        results = event.results_df
        year = event.year
        event_name = event.official_name

        max_score = max([x for x in results.Place.values if str(x).isnumeric()])

        if player in results.Player.values:

            score = results[results.Player == player].Place.values[0]

            if score == 'DNF':
                score = max_score + 1
                # in_event = 1
                
            elif score == 'ERROR':
                if verbose:
                    print(f'Something went wrong for {player} in the "{event}" event.')
                # in_event = 0

                pass
                
            # else:
            #     in_event = 1

            self.player_results[year][event_name] = score

            # if event_name in self.player_results.keys():
            #     self.total_score -= self.player_results[event_name]

            # else:
            #     self.number_of_events += in_event
                
            # self.total_score += int(score)

            self.total_score = sum(self.player_results[year].values())
            self.number_of_events = len(self.player_results[year])
            
            if self.number_of_events:
                self.average_score = round(self.total_score / self.number_of_events, 3)

            return score

        else:
            if verbose:
                print(f'{player} did not play in the {event}.')
            pass


    def years_results(self, year, i=0):

        player = self.official_name

        results = self.player_results[year]
        total_score = sum(results.values())
        number_of_events = len(results)
        if number_of_events:
            average_score = round(total_score / number_of_events, 3)
        else:
            average_score = 0

        if i:
            player_line = f'{i}. {player}'
        else:
            player_line = f'-- {player} --'

        separator = '*' * (len(player_line)+2)

        return f"""{separator}
 {player_line}
{separator}
Number of events: {self.number_of_events}
Total score: {self.total_score}
Average score: {self.average_score:.3f}
Weighted average: {round(self.total_score / (self.number_of_events * 0.5), 3):.3f}
"""     


    def update_status(self, activate=True):

        action_dict = {
            True: 'active',
            False: 'inactive'
        }

        if self.is_active == activate:
            print(f'{player} is already {action_dict[activate]}')
        else:
            player.is_active = activate

        return None

# class SomeClass(object):
#     def __init__(self, n):
#         self.list = range(0, n)

#     @property
#     def list(self):
#         return self._list
#     @list.setter
#     def list(self, val):
#         self._list = val
#         self._listsquare = [x**2 for x in self._list ]

#     @property
#     def listsquare(self):
#         return self._listsquare
#     @listsquare.setter
#     def listsquare(self, val):
#         self.list = [int(pow(x, 0.5)) for x in val]

# >>> c = SomeClass(5)
# >>> c.listsquare
# [0, 1, 4, 9, 16]
# >>> c.list
# [0, 1, 2, 3, 4]
# >>> c.list = range(0,6)
# >>> c.list
# [0, 1, 2, 3, 4, 5]
# >>> c.listsquare
# [0, 1, 4, 9, 16, 25]
# >>> c.listsquare = [x**2 for x in range(0,10)]
# >>> c.list
# [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    
class Team:
    
    def __init__(self, owner, name, roster=[], total_limit=8, active_limit=5, year=dt.today().year):

        self.owner = owner.strip().title()
        self.name = name.strip().title()
        self._limit = total_limit
        self._active_limit = active_limit
        self.roster = roster
        self.player_count = len(self.roster)
        # self.active_player_count = self.count_active_players()
        # self.active_spots_remaining = self._active_limit - self.number_of_active_players

    def __repr__(self):
        return f'{self.name}, owned by {self.owner}'

    def __add__(self, player):

        if type(player) == Player:

            if player not in self.roster:

                if len(self.roster) < self._limit:

                    self.roster += [player]
                    _message = f'{player} has been added to {self.name}'

                    if self.player_count <= self._active_limit:
                        player.is_active = True
                        _message += ' and set to active'

                    else:
                        player.is_active = False

                else:
                    _message = f'{self.name} must drop a player before adding another'

            else:
                _message = print(f'{player} is already a member of {self.name}')

            print(_message + '.')

            return None

        else:
            raise TypeError
        

    def __sub__(self, player):

        if type(player) == Player:

            if player in self.roster:

                player.is_active = False
                self.roster.remove(player)
                
                print(f'{player} has been dropped from {self.name}')

            else:
                print(f'{player} is not a member of {self.name}')

            return None

        else:
            raise TypeError

    @property
    def roster(self):
        return self._roster
    @roster.setter
    def roster(self, val):
        self._roster = val
        self.player_count = len(self._roster)
        self.active_roster = [player for player in self._roster if player.is_active]
        self.active_player_count = len(self.active_roster)
        self.active_spots_remaining = self._active_limit - self.active_player_count
        

    def count_active_players(self):

        _number_of_active_players = len(self.active_roster)

        return _number_of_active_players
        

    def count_active_players(self):

        _number_of_active_players = len([player for player in self.roster if player.is_active])

        return _number_of_active_players
        

    def update_player(self, player, action):

        if player not in self.roster:
            print(f'{player} is not a member of {self.name}')
            return None

        action_dict = {
            'activate': True,
            'deactivate': False
        }

        player.update_status(action_dict[action])
        # self.number_of_active_players = self.count_active_players()

        return None


    def team_results(self, active_only=False):

        _total_score = 0
        _number_of_events = 0

        if self.roster:
            if active_only:
                _roster = self.active_roster

            else:
                _roster = self.roster

            for player in _roster:
                _total_score += player.total_score
                _number_of_events += player.number_of_events

            if _number_of_events:
                _average_score = _total_score / _number_of_events

                _message = f"""Number of events: {_number_of_events}
Total score: {_total_score}
Average score: {_average_score:.3f}
Weighted average: {round(_total_score / (_number_of_events * 0.5), 3):.3f}
"""     

            else:
                _message = f'The players on {self.name} have not played in any events.'

        else:
            _message = f'{self.name} has no players.'

        print(_message)

        return None



