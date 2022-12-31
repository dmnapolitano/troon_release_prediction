import re
from datetime import datetime, timedelta
from os.path import getmtime
from calendar import month_name
import argparse

import pandas
from numpy import nan
from spacy.lang.en import English
from nltk.corpus import stopwords
from nltk.util import ngrams


weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

nlp = English()
nlp.add_pipe('sentencizer')
tokenizer = nlp.tokenizer

stopwords_list = (stopwords.words("english") +
                  ["n't", "'s", "'re", "'ll", "-pron-", "'m", "'d"] +
                  [":", ".", ",", "!", "/", "-", "?", "*", "(",
                   ")", "#", '"', "'ve", "...", "$", "+", "wo", "'"])
stopwords_list.remove("out")


def get_date_from_age(x, last_modified):
    if type(x) is not str:
        return nan
    
    if re.search(r'[A-Z]+\s[0-9]+,\s20[0-9]{2}', x):
        return datetime.strptime(x, "%B %d, %Y")
    elif re.search(r'[A-Z]+\s[0-9]+', x):
        return datetime.strptime(x + ", 2020", "%B %d, %Y")

    if "DAYS" in x:
        days_ago = int(re.search(r'([0-9]+) DAYS AGO', x).groups(0)[0])
        return last_modified - timedelta(days=days_ago)
    if re.search(r'[0-9]+[dD]', x):
        days_ago = int(re.search(r'([0-9]+)[dD]', x).groups(0)[0])
        return last_modified - timedelta(days=days_ago)
    if re.search(r'[0-9]+[wW]', x):
        weeks_ago = int(re.search(r'([0-9]+)[wW]', x).groups(0)[0])
        return last_modified - timedelta(weeks=weeks_ago)
    # TODO: when we become interested in exact release times
    #hours_ago = int(re.search(r'([0-9]+) HOURS AGO', x).groups(0)[0])
    return last_modified


def get_release_times(x):
    # pre-filtered on release_post == True
    # second regex allows too many false positives
    release_times = re.findall(r'([0-9]{1,2}:[0-9]{2}\s*[apAP]?[mM]?)', x)#|[0-9]{1,2}\s*[apAP][mM])', x)
    # the notion of time is missing from some of the older posts
    if len(release_times) == 0:
        return nan

    release_times_as_datetime = []
    for t in release_times:
        info = list(re.search(r'([0-9]{1,2}):?([0-9]{0,2})\s*([apAP]?[mM]?)', t).groups())
        if len(info[1]) == 0:
            info[1] = "00"
        if len(info[2]) == 0 or info[2] == "m":
            info[2] = ("am" if int(info[0]) >= 9 and int(info[0]) < 12 else "pm")
        if len(info[2]) == 1:
            info[2] = info[2] + "m"
        dt = datetime.strptime(info[0] + ":" + info[1] + " " + info[2], "%I:%M %p")
        release_times_as_datetime.append(dt)
    return sorted(release_times_as_datetime)


def tokenize(x): 
    if type(x) is str: 
        doc = nlp(x) 
        tokens = [] 
        for s in doc.sents: 
            t = [y.text.lower() for y in tokenizer(re.sub(r"can't", r'can not', s.text, re.I))]
            tokens += [y for y in t if y not in stopwords_list and len(y.strip()) > 0]
        return tokens 
    return []


def get_cans(x):
    found = []
    for (a, b) in x:
        if re.search(r'[0-9]+', a):
            found.append(int(a.replace("ish", "")))
        # it's never in b lol
    if len(found) > 0:
        return max(found)
    return nan


def get_pp(x):
    # usually 1-3 pp
    if len(x) == 0:
        return nan
    if len(x) == 1 and x[0][1] == "pp" and re.search(r'[0-9]+', x[0][0]):
        return int(x[0][0])
    found = []
    for (a, b) in x:
        if re.search(r'[0-9]+pp', a):
            found.append(int(re.search(r'([0-9]+)pp', a).groups(0)[0]))
        elif re.search(r'[0-9]+pp', b):
            found.append(int(re.search(r'([0-9]+)pp', b).groups(0)[0]))
        elif b == "pp" and re.search(r'[0-9]+', a):
            found.append(int(a))
        #else:
        #    print(">" + a + "<", "[" + b + "]")
    if len(found) > 0:
        return max([f for f in found if f < 10])
    return nan


def to_datetime(row):
    try:
        return datetime(year=row["post_year"],
                        month=list(month_name).index(row["post_month"]),
                        day=row["post_day"],
                        hour=row["release_start"].hour,
                        minute=row["release_start"].minute,
                        second=row["release_start"].second)
    except:
        return nan

    
def get_name_desc_and_abv(post_text):
    if type(post_text) is str and "%-" in post_text:
        (name, abv, description) = re.search(r'(\n|^)(.+?)[,\s]*([0-9]{1,2}\.?[0-9]?[0-9]?%)-\s*(.+)',
                                             post_text).groups()[1:]
        return (name, abv, description)
    return (nan, nan, nan)

    
def go(input_file, output_file, update_existing_data=False):
    df = pandas.read_csv(input_file, index_col="id", dtype={"likes" : "Int64"})
    df.dropna(how="all", subset=["age", "likes", "post_text"], inplace=True)

    if not update_existing_data:
        out_df = pandas.read_csv(output_file, index_col="id", dtype={"likes" : "Int64"})
        df = df[~df.index.isin(out_df.index)]
        if len(df) == 0:
            return

    last_modified = datetime.utcfromtimestamp(float(getmtime(input_file)))
    last_modified = last_modified.replace(hour=0, minute=0, second=0, microsecond=0)

    if "post_date" in df.columns:
        df["post_date"] = df["post_date"].apply(lambda x : nan if type(x) is not str else
                                                (datetime.fromisoformat(x.rstrip("Z") + "+00:00")
                                                 if x.endswith(".000Z") else datetime.fromisoformat(x)))
        
    df["post_date_from_age"] = df["age"].apply(lambda x : get_date_from_age(x, last_modified))
    del df["age"]

    df["post_date"] = df["post_date"].fillna(df["post_date_from_age"])
    del df["post_date_from_age"]
    df["post_date"] = df["post_date"].dt.tz_convert("US/Eastern")

    df["post_weekday"] = df["post_date"].apply(lambda x : weekdays[x.weekday()])
    df["post_month"] = df["post_date"].apply(lambda x : "{0:%B}".format(x))
    df["post_day"] = df["post_date"].apply(lambda x : int(x.day))
    df["post_year"] = df["post_date"].apply(lambda x : int(x.year))

    df["release_post"] = df["post_text"].apply(lambda x : (True if type(x) is str
                                                           and (re.search(r'\bsold\s+out\b', x, re.I) or
                                                                re.search(r'\bcans\s+are\s+gone\b', x, re.I) or
                                                                re.search(r'\bclosing\s+up\s+shop\b', x, re.I))
                                                           else False))
    
    # TODO: Troon posts don't seem to contain the time at which they sold out anymore :(
    # df["times"] = df.apply(lambda x : (get_release_times(x["post_text"]) if x["release_post"] else nan), axis=1)
    # pandemic times lol
    df["times"] = df.apply(lambda x : [x["post_date"], x["post_date"] + timedelta(0, 30)]
                           if x["release_post"] and ".square.site" in x["post_text"] else
                           ([x["post_date"], x["post_date"] + timedelta(0, 60)] if x["release_post"] else nan),
                           axis=1) #else x["times"]), axis=1)
        
    df["release_start"] = df["times"].apply(lambda x : (x[0] if type(x) is list else nan))
    df["release_end"] = df["times"].apply(lambda x : (x[-1] if type(x) is list else nan))

    del df["times"]
    
    df["release_duration_min"] = df["release_end"] - df["release_start"]
    df["release_duration_min"] = df["release_duration_min"].apply(lambda x : x.total_seconds() / 60
                                                                  if type(x) is not float else nan)
    df["release_start_hour_24"] = df["release_start"].apply(lambda x : x.hour
                                                            if type(x) is not float else nan)
    df["release_end_hour_24"] = df["release_end"].apply(lambda x : x.hour
                                                        if type(x) is not float else nan)

    df["release_start"] = pandas.to_datetime(df["release_start"])
    df = df.sort_values(by=["post_date"])
    df["release_start_diff"] = df["post_date"].diff(periods=1)
    df["days_since_previous_release"] = df["release_start_diff"].apply(lambda x : x.days)
    
    del df["release_start"]
    del df["release_start_diff"]
    del df["release_end"]
    del df["post_date"]

    # TODO: do more with these tokens and ngrams
    df["post_tokens"] = df["post_text"].apply(tokenize)
    df["post_bigrams"] = df["post_tokens"].apply(lambda x : list(ngrams(x, 2)))
    df["release_pp_tokens"] = df["post_bigrams"].apply(lambda x : [b for b in x if b[1].endswith("pp")])
    df["release_cans_tokens"] = df["post_bigrams"].apply(lambda x : [b for b in x if b[1] == "cans"])
    del df["post_bigrams"]
    df["release_cans"] = df["release_cans_tokens"].apply(get_cans)
    del df["release_cans_tokens"]
    df["release_pp"] = df["release_pp_tokens"].apply(get_pp)
    del df["release_pp_tokens"]

    del df["post_tokens"]

    df["beer_info"] = df["post_text"].apply(get_name_desc_and_abv)
    del df["post_text"]
    df["beer_name"] = df["beer_info"].apply(lambda x : x[0])
    df["beer_abv"] = df["beer_info"].apply(lambda x : float(x[1].replace("%", ""))
                                           if type(x[1]) is str else x[1])
    df["beer_description"] = df["beer_info"].apply(lambda x : x[2])
    del df["beer_info"]

    df["release_post"] = df.apply(lambda x : (True if x["release_post"] or
                                              type(x["beer_name"]) is str else False), axis=1)

    print(df[df["release_post"] == True]["post_weekday"].value_counts())

    df = df.sort_index()
    if update_existing_data:
        df.to_csv(output_file)
    else:
        df.to_csv(output_file, mode="a", header=False)


if __name__ == "__main__":
    input_csv_file = "troon_instagram_raw_post_data.csv"
    output_csv_file = "troon_instagram_clean_post_data.csv"

    parser = argparse.ArgumentParser()
    parser.add_argument("--update_existing_clean_data", action="store_true", default=False)
    args = parser.parse_args()
    
    go(input_csv_file, output_csv_file, update_existing_data=args.update_existing_clean_data)
