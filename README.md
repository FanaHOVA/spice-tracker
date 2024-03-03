# Spice Tracker

Look at all [mtgtop8 results](https://www.mtgtop8.com/) and flag any cards that
haven't been previously seen in a specific archetype. 

Uses Supabase for storage but can replace with any other data store, not using
any pg-specific feature. 

# Usage

- Create `.env` based on `.env.sample` and add your credentials
- Install reqs `pip install -r requirements.txt`
- In `spice_tracker.py`, add the id of archetypes you want to track. To get the
  archetype_id, just open a format and click on a deck from the metagame
  breakdown on the left. It's the `a` id in the url (i.e.
  `https://www.mtgtop8.com/archetype?a=985&meta=54&f=MO`).
- Run the script (`python spice_tracker.py`)
- At first run, it will return a list of all cards seen in the archetype to seed
  the database. Going forward, you can run it anytime and it will only return
  cards that it hadn't seen before.

# Todos

- Make it easy to host as a cron job, maybe on val.town
- Add email support so that I can get a daily email about new cards instead of
  running manually
