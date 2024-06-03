import requests
import os
from urllib.parse import urlparse, parse_qs
import sqlite3
from bs4 import BeautifulSoup

def create_connection():
    conn = sqlite3.connect('mtg.db')
    return conn

def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS cards
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                       mtg_a_id INTEGER,
                       mtg_d_id INTEGER,
                       card_name TEXT,
                       special_id TEXT,
                       tcgplayer_id TEXT,
                       scryfall_id TEXT,
                       cardkingdom_id TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS decks
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       mt8_d_id INTEGER,
                       mt8_a_id INTEGER,
                       mt8_e_id INTEGER,
                       mt8_meta_id INTEGER,
                       name TEXT,
                       player_name TEXT,
                       event_name TEXT,
                       event_strength INTEGER,
                       event_date TEXT)''')
    conn.commit()

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

def save_deck_to_database(conn, deck, archetype_id):
    cursor = conn.cursor()
    data = (
        deck['event_id'],
        deck['deck_id'],
        archetype_id,
        deck['name'],
        deck['player_name'],
        deck['event_name'],
        deck['event_strength'],
        deck['event_date']
    )
    cursor.execute('''INSERT OR IGNORE INTO decks
                      (mt8_e_id, mt8_d_id, mt8_a_id, name, player_name, event_name, event_strength, event_date)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()

def save_card_to_database(conn, card, deck_id, archetype_id):
    cursor = conn.cursor()
    special_id = f"a_{archetype_id}{card.replace(' ', '').lower()}"
    cursor.execute("SELECT special_id FROM cards WHERE special_id = ?", (special_id,))
    existing_card = cursor.fetchone()
    if existing_card:
        print("Card with this special_id already exists in the database.")
        return
    data = (
        archetype_id,
        deck_id,
        card,
        special_id
    )
    cursor.execute('''INSERT INTO cards
                      (mtg_a_id, mtg_d_id, card_name, tcgplayer_id)
                      VALUES (?, ?, ?, ?)''', data)
    conn.commit()

    return card

if __name__ == "__main__":
    conn = create_connection()
    create_tables(conn)

    favorite_modern_archetypes = {
        918: "Rakdos Scam",
        300: "Zoo",
        636: "Death's Shadow",
        351: "Prowess",
        819: "Mono B Rack",
        191: "Yawg",
        302: "Coffers",
        1592: "Ring Control",
        375: "UR Control",
        233: "Living End",
        998: "Creativity",
        348: "Titan",
        312: "Goryo's"
    }

    new_spice = {}

    for archetype_id in favorite_modern_archetypes.keys():
        archetype_html = scrape_archetypes(archetype_id)
        decks = extract_event_decks(archetype_html)

        for deck in decks:
            save_deck_to_database(conn, deck, archetype_id)

            event_html = scrape_event(deck['event_id'], deck['deck_id'])
            cards = extract_cards(event_html)

            for card in cards:
                saved_card = save_card_to_database(conn, card, deck['deck_id'], archetype_id)

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

    conn.close()
