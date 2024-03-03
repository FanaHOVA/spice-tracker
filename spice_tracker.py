import requests
import os
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup
from supabase import create_client, Client

from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

'''
MTG Top8

Archetypes list
https://www.mtgtop8.com/archetype?a=226

archetype_id: int, marked as `a` in the URL

Decks from metagame
https://www.mtgtop8.com/archetype?a=351&meta=54&f=MO

archetype_id: int, marked as `a` in the URL
meta_id: int, marked as `meta` in the URL

Decklist in event
https://www.mtgtop8.com/event?e=52837&d=592372&

event_id: int, marked as `e` in the URL
deck_id: int, marked as `d` in the URL
'''

'''
Cards table schema
created_at: datetime
mtg_a_id: int
mtg_d_id: int
card_name: str
tcgplayer_id: str
scryfall_id: str
cardkingdom_id: str

Decks table schema
mt8_d_id: int
mt8_a_id: int
mt8_e_id: int
mt8_meta_id: int	
name: str	
player_name: str	
event_name: str	
event_strength: int	
event_date: date	
'''

def scrape_archetypes(archetype_id):
    url = 'https://www.mtgtop8.com/archetype'
    params = {'a': archetype_id}
    response = requests.get(url, params=params)
    return response.text

def scrape_metagame(archetype_id, meta_id):
    url = 'https://www.mtgtop8.com/archetype'
    params = {'a': archetype_id, 'meta': meta_id, 'f': 'MO'}
    response = requests.get(url, params=params)
    return response.text

def scrape_event(event_id, deck_id):
    url = 'https://www.mtgtop8.com/event'
    params = {'e': event_id, 'd': deck_id, 'f': 'MO'}
    response = requests.get(url, params=params)
    
    return response.text
  
def extract_event_decks(archetype_page_html):
    soup = BeautifulSoup(archetype_page_html, 'html.parser')
    table = soup.find('table', {'class': 'Stable', 'align': 'center', 'width': '99%'})
    event_deck_ids = []
    for row in table.find_all('tr', {'class': 'hover_tr'}):
        columns = row.find_all('td')
        a = columns[1].find('a', href=True)
        if 'event?' in a['href']:
            query = urlparse(a['href']).query
            params = parse_qs(query)
            event_deck_ids.append({
                'event_id': params['e'][0],
                'deck_id': params['d'][0],
                'name': a.text,
                'player_name': columns[2].text,
                'event_name': columns[3].text,
                'event_strength': len(columns[4].find_all('img')),
                'event_date': columns[6].text
            })
    return event_deck_ids
  
def extract_cards(event_page_html):
    soup = BeautifulSoup(event_page_html, 'html.parser')
    cards = [card.text for card in soup.find_all('span', {'class': 'L14'})]
    return cards

def save_deck_to_database(deck, archetype_id):
    table = "decks"
    data = {
        "mt8_e_id": deck['event_id'],
        "mt8_d_id": deck['deck_id'],
        "mt8_a_id": archetype_id,
        "name": deck['name'],
        "player_name": deck['player_name'],
        "event_name": deck['event_name'],
        "event_strength": deck['event_strength'],
        "event_date": deck['event_date']
    }
    response = supabase.table(table).upsert(data, ignore_duplicates=True).execute()
    return response

def save_card_to_database(card, deck_id, archetype_id):
    table = "cards"
    data = {
        "mtg_a_id": archetype_id,
        "mtg_d_id": deck_id,
        "card_name": card,
        "special_id": f"a_{archetype_id}_{card.replace(' ', '_').lower()}"
    }
    existing_card = supabase.table(table).select('special_id').eq('special_id', data['special_id']).execute()
    if existing_card.data:
        print("Card with this special_id already exists in the database.")
        return
    
    supabase.table(table).insert(data).execute()
    
    return card
  
if __name__ == "__main__":
    favorite_archetypes = [985]

    new_spice = {}
    
    for archetype_id in favorite_archetypes:
        archetype_html = scrape_archetypes(archetype_id)
        decks = extract_event_decks(archetype_html)
        
        for deck in decks:
            save_deck_to_database(deck, archetype_id)
            
            event_html = scrape_event(deck['event_id'], deck['deck_id'])
            cards = extract_cards(event_html)
            
            for card in cards:
                saved_card = save_card_to_database(card, deck['deck_id'], archetype_id)
                
                if saved_card is None:
                    continue
                  
                if deck['name'] not in new_spice:
                    new_spice[deck['name']] = [saved_card]
                else:
                    new_spice[deck['name']].append(saved_card)
    
    for archetype, cards in new_spice.items():
        print(f"New cards for archetype {archetype}:")
        for card in cards:
            print(card)
    

