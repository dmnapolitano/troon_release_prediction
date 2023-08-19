import re
from collections import Counter

import pandas
from numpy import nan
from nltk.util import ngrams

from clean_data_03 import tokenize


more_stopwords = ['amounts', 'especial', 'pink', 'weekend', 'amount', 'busiest', '8lbs',
                  'unflappable', 'old', 'use', 'really', 'staple', 'met', 'missive', 'brewed',
                  'prepare', 'approximately', 'golden', 'metal', 'inspired', 'youth', 'little',
                  'food', 'tough', 'upcoming', 'different', 'previously', 'bashing', 'date',
                  'dozen', 'composed', 'interviews', 'logical', 'bunch', 'grown', 'intensely',
                  'tasteful', 'first', 'state', 'slow', 'duh', '7lbs', 'coast', 'blend',
                  'arguably', 'smattering', 'world', 'half', 'unreasonable', 'vetting', 'totally',
                  'hyphenated', 'trendy', 'lot', 'ago', 'announce', 'want', 'yellow', 'gallons',
                  'bine', 'countless', 'ceremony', 'part', 'w', 'west', 'ghoulish', 'heavily',
                  'cold', 'one', 'time', 'ever', 'left', 'end', 'hare', 'drinking', 'exhaustive',
                  'planet', 'included', 'tavern', 'even', 'nearly', 'revelatory', 'beguiling',
                  'numbing', 'roaster', 'exact', 'quantities', 'drier', 'showcasing', 'house',
                  'billing', 'nj', 'otter', 'packaging', 'shows', 'mix', 'lightly', 'happy',
                  'brick', 'large', 'leashedin', 'implacable', 'like', 'body', 'equal', 'learning',
                  'modified', 'financially', 'well', 'around', 'stupefying', 'gorgeous', 'market',
                  'sick', 'art', 'could', 'fucking', 'ludicrous', '@brickfarmmarket', 'hyperbaric',
                  'usual', 'followed', 'absurd', 'year', 'mixed', 'specifically', 'utilizing', 'e.',
                  'befuddling', 'volume', 'flavors', 'continuation', 'read', 'hours', 'inimitable',
                  'key', 'quantity', 'going', 'tiny', 'brew', 'irresponsible', 'five', 'celebration',
                  'july', 'gobs', 'extraordinary', 'outrageous', 'satisfying', 'conditions', '50/50',
                  'perpetual', 'heavenly', 'letting', 'ending', 'folks', 'comprised', 'style',
                  'months', 'experience', 'classic', 'newest', 'out', 'calmly', 'minuscule', 'get',
                  'another', 'pleasant', 'closest', 'staff', 'caned', 'made', 'finest', 'two',
                  'shown', 'stones', 'almost', 'delighted', 'desk', 'solely', 'tried', 'three',
                  'flavor', 'addition', 'consolamentum', 'immoderate', 'thanks', 'artificial', 'rate',
                  'lightest', 'buried', 'grade', 'judiciously', 'taste', 'ridiculous', 'twice', 'take',
                  'crafted', 'dumped', 'department', 'healthy', 'dude', 'birds', 'modern', 'hybrid',
                  'many', 'purify', 'ovens', 'matter', 'weight', 'luscious', 'delicate',
                  'encapsulating', 'touch', 'name', 'freshly', 'lend', '6#', 'firework', 'ballooned',
                  'loaded', 'abc', 'never', 'concentrate', 'find', 'tons', 'ultra', 'vibe', 'bowtie',
                  'change', 'texture', 'varieties', 'round', 'hoppiest', 'us', 'th', 'commiserate',
                  'whole', 'ton', 'recognition', 'still', 'know', 'combination', 'someone',
                  'thousands', 'navigating', 'beer', 'performed', 'panicked', 'friends', 'slightest',
                  'judicious', 'luggage', 'entirely', '4th', 'anniversary', 'available', 'farm',
                  'favorite', 'processed', 'added', 'dining', 'james', 'contemplation', 'years',
                  'paperwork', 'beautiful', 'minutes', 'holiday', 'good', 'blue', 'extension',
                  'shitload', 'total', 'summer', 'person', 'kinds', 'think', 'posted', 'singularly',
                  'consideration', 'timor', 'enormous', 'offering', 'quite', 'new', 'used', 'sensible',
                  'weeks', 'merely', 'literal', 'lots', 'mind', 'come', 'process', 'bar', 'childhood',
                  'sexy', 'abdon', 'line', 'boatload', 'brett', 'room', 'dose', 'bludgeoningly',
                  'phenomenal', 'help', 'troon', 'huge', 'malted', 'everyone', 'application',
                  'primarily', 'batch', 'massive', 'oiliest', 'day', 'one', 'friends', 'monstrous',
                  'many', 'friends', 'great', 'sorry', 'bottle', 'made', 'wax', 'label',
                  'red', 'purple', 'white', 'mountains', 'copper', 'best', 'hand', 'drink', 'maximum',
                  'intensity', 'favorite', 'melange', 'pounds']

input_file = "troon_instagram_clean_post_data.csv"
input_df = pandas.read_csv(input_file, index_col="id", dtype={"likes" : "Int64"})

df = pandas.read_csv("troon_instagram_post_beer_attributes.csv", dtype={"id" : "Int64"})
known_characteristics = {tuple(r["attribute"].split(" ")) : r["count"] for (i, r) in
                         df.groupby(["attribute"]).agg({"count" : sum}).reset_index().iterrows()}

to_consider = []
for (i, row) in input_df[~input_df.index.isin(df["id"])].iterrows():
    tokens = [re.sub(r'[/+]$', '', t) for t in tokenize(row["beer_description"]) if
              len(t) > 1 and not re.search(r'^[0-9]+$', t) and "bbl" not in t]
    for l in [1, 2, 3]:
        for (ngram, c) in Counter(ngrams(tokens, l)).items():
            if ngram in known_characteristics:
                new_row = {"id" : i, "attribute" : " ".join(ngram), "count" : c}
                df = pandas.concat([df, pandas.DataFrame([new_row])], ignore_index=True)
            else:
                ngram_stopwords = [t for t in ngram if t in more_stopwords]
                if len(ngram_stopwords) < len(ngram):
                    substring = [known for known in known_characteristics if
                                 len([t for t in ngram if t in known]) > 0]
                    if len(substring) == 0:
                        to_consider.append(ngram)
                    
if len(to_consider) == 0:
    df = df.set_index("id")
    df.index = df.index.astype("Int64")
    df["count"] = df["count"].astype("Int64")
    df.to_csv("troon_instagram_post_beer_attributes.csv")
else:
    print(Counter(to_consider))

