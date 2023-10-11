import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
import itertools


def soupify(url):
    page = requests.get(url)
    soup = bs(page.content, "html.parser")
    return soup


def events_list(url):
    soup = soupify(url)
    events_with_links_raw = soup.select('a[href*="https://www.pdga.com/tour/event/"]')
    events_with_links = [(e.text,e['href']) for e in events_with_links_raw]
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


def results(event_name, event_url, save_df=False, file_path=''):
    
    soup = soupify(event_url)
    results_table_raw = soup.find_all(class_="table-container")[1]
    odd_rows = results_table_raw.find_all(class_="odd")
    even_rows = results_table_raw.find_all(class_="even")
    results_raw = [x for x in itertools.chain.from_iterable(itertools.zip_longest(odd_rows,even_rows)) if x]
    results_list = [parse_rows(row) for row in results_raw]
    results_df = pd.DataFrame(data=results_list) #.set_index('Place')
    
    if save_df:
        file_name = f'Results_{event_name.replace(" ","-")}.csv'
        results_df.to_csv(file_path + file_name)
        print(f'{file_name} has been saved.')
        
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


