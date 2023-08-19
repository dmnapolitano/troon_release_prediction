## Background

In a state with [almost 150 craft breweries](https://newjerseycraftbeer.com/new-jersey-breweries/) (roughly one brewery every 58 square miles), beers produced by the [Troon Brewing Company](https://www.instagram.com/troonbrewing/) are considered to be some of the best.  They are also, most likely, one of the smallest, sharing property with [Brick Farm Tavern](https://brickfarmtavern.com/) under the agreement that Troon brews exclusively for them, with whatever BFT doesn't purchase left available for on-site retail.

This arrangement, along with Troon's size, create a few issues for craft beer fans: beer is made available for sale the day it's completed and the time canning wraps up, which not only varies but can be hard to pinpoint exactly.  Availability is announced via Instagram, so if, pre-COVID, one isn't at BFT to pick it up almost immediately, or post-COVID, one doesn't place an order for cans within a second (:warning:) of the announcement...

The goal of this project is collect data surrounding Troon releases scraped from Instagram and to attempt to predict when--date and time--how much, and possibly what type of beer will be released.

Please feel free to explore what's here so far and view the data/features/visualizations.  And please make suggestions and pull requests, of course. :beers:

## Collaborators

* [Me!](https://github.com/dmnapolitano)
* [Jeremy Biggs](https://github.com/jbiggsets)

## "Known Unknowns"

There's an upper bound on how good any model can be at predicting when Troon will release beer.  This is due to several "known unknowns", information I'd only have (some level of) access to if I worked at the brewery.  And if I worked at the brewery, I'd probably already know when releases were going to or about to happen, so this project wouldn't need to exist.  "Known unknowns" here include how many beers Troon is brewing at any given time along with the duration of each beer's brewing process.  Furthermore, some may be ready earlier than expected, some later than expected.  We also don't know the schedules of the brewery staff -- although, it does look like there are periods of lengthy (one or two weeks) vacations where the brewery is basically not functioning.  I might be able to predict those... :grin:

Anyway, because of this, we can't really treat any model here as anything more than "just for fun".  Based on what we _can_ know about patterns in Troon releases, here's the _most likely_ days on which they'll occur, so on those days, keep your Instagram app open and your alerts on.  And keep thinking about ways in which we can address both the "known unknowns" and "unknown unknowns" :wink:

## "Wins" with the Current Model

* 7/10/2023 with a probability of 61% :tada:

### "Interesting" "Wins"

* 8/12/2023: No release predicted (probability of a release of 35%), but, on that day there was a "pick up is tomorrow, 8/13" release, and the predicted probability of a release on the 13th was 60%. :thinking:

## "Losses" with the Current Model

* 7/12/2022 with a probabilty of 22% :confused: