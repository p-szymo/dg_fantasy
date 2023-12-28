import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
import itertools
from datetime import date as dt
import re
import pickle


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


def table_exists(table_name):

    table_exists_query = f"""SELECT 1
FROM information_schema.tables
WHERE table_name='{table_name}'"""

    return table_exists_query


def create_table(table_name, table_columns):

    columns_list = [f"{column} {datatype}" for column,datatype in table_columns.items()]
    columns_query = ',\n\t'.join(columns_list)

    create_table_query = f'''CREATE TABLE "{table_name}" (
    {columns_query}
);'''

    return create_table_query


def player_table_dict():

    return {
        'Name': 'varchar(200)',
        'PDGA Number': 'bigint',
        'Event Name': 'varchar(500)',
        'Place': 'int',
        'Event Year': 'int',
        'Event Status': 'varchar(50)'
    }


def event_table_dict():

    return {
        'Place': 'int',
        'Player': 'varchar(200)',
        'PDGA Number': 'bigint',
        'Player Rating': 'int',
        'Score': 'varchar(10)'
    }


def insert_data(table_name, table_columns, data):

    column_names = table_columns.keys()

    insert_list = []

    for i,_dict in enumerate(data):

        data_to_insert = []

        for i,(column_name,datum) in _dict.items():
            if "varchar" in table_columns[column_name]:
                datum = "'" + datum.replace("'", "''") + "'"

            data_to_insert.append(datum)

        insert_list.append('(' + ','.join(data_to_insert) + ')')

    insert_values = '\n\t,'.join(insert_list) + '\n;'

    insert_query = f'''TRUNCATE TABLE "{table_name}";

INSERT INTO "{table_name}" ({",".join(column_names)})
VALUES {insert_values}'''

    return insert_query


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

        # print(self.url)

        self.table_name = self.event_namer()

        self.results_df = self.event_parser(self.url)

        _exists, _create, _insert = self.sql_queries()

        self.table_exists_query = table_exists(self.table_name)

        self.create_table_query = create_table(self.table_name, event_table_dict())

        self.insert_values_query = insert_data(
            self.table_name, 
            event_table_dict(), 
            self.results_df.to_dict('records')
        )



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

        return None


    def event_namer(self):
        _name = self.official_name.upper().split(' - ')[-1]
        if 'PRESENT' in _name:
            if 'PRESENTED' in _name:
                event_name = _name.split('PRESENTED')[0].strip()
            elif 'PRESENTS' in _name:
                event_name = _name.split('PRESENTS')[-1].strip()
                
        elif 'POWERED' in _name:
            event_name = _name.split('POWERED')[0].strip()
                
        else:
            event_name = _name.strip()
            
        event_name = event_name.replace(str(self.year), '').replace('PLAY IT AGAIN SPORTS', '').replace('  ', ' ').strip()
            
        return f"{event_name}, {self.year}"


    def sql_queries(self):

        table_exists_query = f"""SELECT 1
FROM information_schema.tables
WHERE table_name='{self.table_name}'"""

        create_table_query = f'''CREATE TABLE "{self.table_name}" (
     "Place" int
    ,"Player" varchar(100)
    ,"PDGA Number" bigint
    ,"Player Rating" int
    ,"Score" varchar(10)
);'''

        insert_query = f'''TRUNCATE TABLE "{self.table_name}";

INSERT INTO "{self.table_name}"
VALUES'''

        for i,(place,player,pdga_number,player_rating,score) in self.results_df.iterrows():
            if i:
                comma = ','
                
            else:
                comma = ' '

            if "'" in player:
                player = player.replace("'", "''")
                
            insert_value = f"{comma}({place},'{player}',{pdga_number},{player_rating},'{score}')"
            
            insert_query += "\n\t" + insert_value
    
        insert_query += "\n;"

        return table_exists_query, create_table_query, insert_query

#     def pickle_that_shit(self, file_path=''):

#         if file_path[-4:] != '.pkl':
#             if '.' in file_path:
#                 file_path = file_path.split('.')[0]

#             file_path = file_path + '.pkl'

#         with open(file_path, 'wb') as outp:
#     company1 = Company('banana', 40)
#     pickle.dump(company1, outp, pickle.HIGHEST_PROTOCOL)

#     company2 = Company('spam', 42)
#     pickle.dump(company2, outp, pickle.HIGHEST_PROTOCOL)

# class Company(object):
#     def __init__(self, name, value):
#         self.name = name
#         self.value = value



# del company1
# del company2

# with open('company_data.pkl', 'rb') as inp:
#     company1 = pickle.load(inp)
#     print(company1.name)  # -> banana
#     print(company1.value)  # -> 40

#     company2 = pickle.load(inp)
#     print(company2.name) # -> spam
#     print(company2.value)  # -> 42


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

    def __eq__(self, val):
        return self.official_name == val


    def fantasy_score(self, event, verbose=0):

        player = self.official_name
        results = event.results_df
        year = event.year
        event_name = event.table_name

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


class League:
    def __init__(
        self, 
        name=None, 
        teams=[], 
        players=[], 
        team_total_limit=9, 
        team_active_limit=5, 
        year=dt.today().year,
        player_table_name='Players'
    ):

        self.name = name.strip()
        self.teams = teams
        self.players = players
        self.team_names = [team.name for team in self.teams]
        self.team_owners = [team.owner for team in self.teams]
        self.team_rosters = [team.roster for team in self.teams]
        self._team_total_limit = team_total_limit
        self._team_active_limit = team_active_limit
        self.player_table_name = player_table_name
        self.player_data = self.create_player_data()

        _exists, _create, _insert = self.sql_queries()
        self.table_exists_query = _exists
        self.create_table_query = _create
        self.insert_values_query = _insert


    def __repr__(self):
        return self.name


    def create_player_data(self):
        players_for_postgres = []

        for player in self.players:
            for year, results in player.player_results.items():
                for event_name, place in results.items():
                    _dict = {
                        'Name': player.official_name,
                        'PDGA Number': player.pdga_number,
                        'Event Name': event_name,
                        'Place': place,
                        'Event Year': year,
                        'Event Status': 'Complete'
                    }
                    
                    players_for_postgres.append(_dict)

        return players_for_postgres


    def sql_queries(self):


    def table_exists(self, table_name):

        table_exists_query = f"""SELECT 1
FROM information_schema.tables
WHERE table_name='{table_name}'"""

        return table_exists_query


    def create_table(self, table_name, ):

        table_exists_query = f"""SELECT 1
FROM information_schema.tables
WHERE table_name='{table_name}'"""

        return table_exists_query

        create_table_query = f'''CREATE TABLE "{self.player_table_name}" (
     "Name" varchar(200)
    ,"PDGA Number" bigint
    ,"Event Name" varchar(500)
    ,"Place" int
    ,"Event Year" int
    ,"Event Status" varchar(50)
);'''

        insert_query = f'''TRUNCATE TABLE "{self.player_table_name}";

INSERT INTO "{self.player_table_name}"
VALUES'''

        for i,_dict in enumerate(self.player_data):
            if i:
                comma = ','
                
            else:
                comma = ' '

            player = _dict['Name'].replace("'", "''")
            pdga_number = _dict['PDGA Number']
            event_name = _dict['Event Name'].replace("'", "''")
            place = _dict['Place']
            event_year = _dict['Event Year']
            event_status = _dict['Event Status']
                
            insert_value = f"{comma}('{player}',{pdga_number},'{event_name}',{place},{event_year},'{event_status}')"
            
            insert_query += "\n\t" + insert_value
    
        insert_query += "\n;"

        return table_exists_query, create_table_query, insert_query


    
class Team:
    
    def __init__(self, owner, name, available_players, roster=[]):

        self.owner = owner.strip().title()
        self.name = name.strip().title()
        self.roster = roster
        self.player_count = len(self.roster)
        self.league = None

    def __repr__(self):
        return f'{self.name}, owned by {self.owner}'

    def __iadd__(self, player):

        if type(player) in [Player, str]:

            if player in available_players:

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

            else:
                _message = print(f'{player} is not available')

            print(_message + '.')

            return self

        else:
            raise TypeError(f"must be Player or str, not {_type}")
        

    def __isub__(self, player):

        _type = type(player)

        if _type in [Player, str]:

            if player in self.roster:

                _index = self.roster.index(player)

                self.roster[_index].is_active = False

                del self.roster[_index]

                print(f'{player} has been dropped from {self.name}')

            else:
                print(f'{player} is not a member of {self.name}')

            return self

        else:
            raise TypeError(f"must be Player or str, not {_type}")

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


import psycopg2

def connect_to_sql():

    connection = psycopg2.connect(
        host='localhost', 
        database='dg_fantasy', 
        port=5433, 
        user='postgres', 
        password='GE$malone'
    )

    executor = connection.cursor()

    return connection, executor


def close_connection(connection, executor):

    executor.close()

    connection.commit()

    connection.close()

    return None
