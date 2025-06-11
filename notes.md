## Ideen
- Hannover öffentliche Sensordaten https://hidd.io/karte
	- Fahrradzähler, Wetter, Boden
- Armed Conflict Location & Event Data (ACLED)
	- https://acleddata.com
	- dates, actors, locations, fatalities, and types of all reported political violence and protest events around the world
	- Ukraine_Infrastructure_Tags_2025-04-30.xlxs
- Komoot GPX
- SerWisS
	- https://serwiss.bib.hs-hannover.de/home
	- Graph
- Basketball data
- NASA

## Idea
- map sub-event types
	- assign colors and sub-colors by event/sub-event type
		- red-ish for all _battle_ events, different sub-event-types different shades of red
- line graph fatalities
	- current one is cumulative, add non-cumulative

## Presentation Notes:
#### 1. Why this dataset?
- important current political events
- well curated, feature rich data
	- source:
		- acleddata.com
		- non-profit organization
		- many different datasets available
	- visualization goal:
		- __where__ is the war happening?
		- changes over __time__ in location, event-types, fatalities
		- changes in methods of warfare
		- total fatalities/cost
#### 2. Feature Showcase
- map with events
- time-slider to select time-frame
- questions:
	- __where__ is the war happening?
		- -> map with color=time
	- changes over __time__ in location, event-types, fatalities
		- -> map with color=time
		- event plots
#### 3. Tech-Stack
- dash.plotly.com
- python :)
#### 4. Future Work
- search functionality
- animated plots
- conflict selector

## Grading Notes
- chart types:
	- map:
		- `px.scatter_map`
		- modes:
			- `country`/ `event-type`
				- qualitative data
				- `px.colors.qualitative.Alphabet`
			- `time`
				- continuous data
				- `px.colors.sequential.Plasma`
			- `fatalities`
				- continuous data
				- `px.colors.sequential.matter`
				- additional property `size`, some events overlap in coordinates
	- stacked histogram:
		- `px.area`, stacked area plot
		- multi-variate aggregated data (event types, frequency of occurrence)
		- x-axis is time
		- used in:
			- _Events Over Time_
	- stacked bar chart:
		- `px.bar(..., barmode='stack')`
		- x-axis is nominal
		- used in:
			- _Event Type Breakdown by Sub Event Type_		
			- _Top 5 Reporting Sources and Sub Event Types_
			- _events-over-time_
	- line graph:
		- `px.line`
		- cardinal data over time
		- used in:
			- _Fatalities Over Time_ (cumulative)
			- _Fatalities Per Day_ (non-cumulative)
	- pie chart:
		- relatively low amount of armed clashes, but high fatality rate
		- used in:
			- _Fatalities by Sub Event Type_
