User Flow
User adds trip constraints:
destination
dates / number of days
budget
travel style
group size
User pastes TikTok / Instagram URLs
App ingests the post content

AI extracts:
Places
city / country
activities
vibe
tags like food, nature, shopping, nightlife

App turns those into real map locations

 Planner generates:
recommended destination or area
day-by-day itinerary
map route
backup options


User edits itinerary with prompts


Create an app where we scrape through saved videos

Ask 6 questions:
Where, will u be going, plus cities 
When. how long would would u be staying for
Budget 
Ask ur personalization questions for recommendation spots 
Group size 
age


Use tik tok or instagram 
Use api calls to access saved or listed videos manually
Use captions to find popular locations
If not in captions do not worry about



Paste url links 


Front End: 

Questions page
landing page / home
Insta/Tik-tok login 
paste-links input area
list of imported posts
extracted places/interests view
trip settings form
itinerary page
map view
chat/edit controls

Back End: 
Google maps api 

Link Ingestion:
Normalize object example: 
{
  "url": "...",
  "platform": "tiktok",
  "caption": "...",
  "transcript": "...",
  "thumbnail_url": "...",
  "creator": "...",
  "detected_text": "...",
  "raw_text": "combined text here"
}

Input:

caption
transcript
OCR text from screenshot/thumbnail
comments if available
creator description/title

Output:

mentioned places
likely city/region
activity type
food type
vibe
recommended time of day
confidence score

Example Extraction Output: 
{
  "post_id": "123",
  "destination_candidates": ["Tokyo", "Shibuya"],
  "place_candidates": ["Shibuya Sky", "Uobei Shibuya Dogenzaka"],
  "activities": ["viewpoint", "sushi", "city walk"],
  "vibe_tags": ["trendy", "night", "photogenic"],
  "best_time": ["evening"],
  "confidence": 0.82
}



Locate Place

We need: 
map extracted place names to real POIs
geocode them
get opening hours
get address
get ratings or popularity
estimate duration
get travel time between places

We need: 
geocoding API
places/details API
routing/travel time API

Example Output for the object:
{
  "name": "Du Pain et des Idees",
  "lat": 48.872,
  "lng": 2.359,
  "category": "bakery",
  "opening_hours": "...",
  "estimated_visit_minutes": 45,
  "source_posts": ["post_1", "post_5"]
}

Trip Planning Engine
This is the second major AI/system logic piece.

Inputs:
resolved places
user constraints
trip duration
open hours
travel times
preferences learned from saves


Outputs:

daily plan
time slots
grouped neighborhoods
alternates

The planner should do 2 jobs:

1. Ranking

Choose what matters most:

places mentioned multiple times
places that fit the user’s vibe
high-confidence travel spots
geographically sensible options

2. Scheduling

Create a realistic plan:

cluster by geography
avoid zig-zag routes
respect opening hours
avoid overpacked days
mix meals and activities
account for morning / afternoon / evening fit

Model Example: 
{
  "days": [
    {
      "day": 1,
      "area": "Shibuya + Harajuku",
      "items": [
        {
          "time": "09:00",
          "place": "Cafe X",
          "type": "breakfast"
        },
        {
          "time": "11:00",
          "place": "Shopping Street Y",
          "type": "shopping"
        }
      ]
    }
  ]
}

Database

users
pasted links
extracted signals
resolved places
trip plans
edits


users

id
name/email

posts

id
user_id
url
platform
raw_text
metadata_json

extractions

post_id
places
vibes
destination_candidates
confidence

places

id
normalized_name
lat/lng
metadata

trips

id
user_id
destination
constraints_json
itinerary_json

We need:
Postgres with JSON fields
or Supabase
or Firebase if team prefers fast setup

AI Modules 

Module 1: Post parser

Takes raw post text and outputs structured travel signals.

Prompt goal:

extract locations
classify activity
infer vibe
decide whether this is actually travel-relevant

Module 2: Preference summarizer

Looks across all saved posts and determines user taste.

Example result:

likes scenic viewpoints
likes aesthetic cafés
prefers dense walking neighborhoods
likes casual food over fine dining

Module 3: Itinerary composer

Given a structured candidate list, builds a multi-day plan.

Module 4: Itinerary editor

Handles follow-up commands like:

make it cheaper
reduce transit time
add nightlife
keep only food spots

Non-AI logic you still need

A lot of the product quality will come from non-LLM logic.

You need:

URL validation
duplicate link detection
place deduplication
clustering places by neighborhood
scoring places
travel time matrix
schedule validation
fallback if extraction is uncertain










Back-end data pipeline


Step 1: Paste URLs

User pastes 5 to 20 links.

Step 2: Ingest raw content

For each link:

collect caption/title/transcript/thumbnail text
combine into raw text blob

Step 3: AI extraction

For each link:

extract destinations
extract place names
extract categories and vibe

Step 4: Aggregate
Across all links:

dedupe place candidates
build user taste profile
identify dominant city or ask user to pick one
Step 5: Resolve real-world POIs

Use map/place API to convert candidates to real locations.

Step 6: Rank

Score by:

mention frequency
fit to user taste
confidence
travel practicality
Step 7: Plan itinerary

Generate day-by-day structure.

Step 8: Render UI

Show:

itinerary cards
map pins
reasoning
edit controls


MVP Feauture
paste TikTok/Instagram URLs
parse some text from posts
extract place names and vibes with AI
resolve at least some places to map pins
generate 2-4 day itinerary
let user refine once with natural language


Frontend person:

Build:

homepage
paste URL input
link list
trip preferences form



Build:

results page
itinerary cards
map panel
editable trip interactions


Back-end preson:
Person 1 Own:

/import-links
/posts
DB schema
link parsing
normalization
Persistence


Backend person 2

Own:

/extract
/generate-trip
/revise-trip
prompt design
structured outputs
scoring/ranking logic


Integrator

place resolution
maps API
end-to-end wiring
deployment
demo prep
QA
