import re
from datetime import datetime
from os.path import getmtime

import pandas
from numpy import nan


csv_file = "troon_instagram_raw_post_data.csv"
last_modified = datetime.utcfromtimestamp(float(getmtime(csv_file)))
last_modified = last_modified.replace(hour=0, minute=0, second=0, microsecond=0)

weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def convert_date(x):
    if re.search(r'[A-Z]+\s[0-9]+,\s20[0-9]{2}', x):
        return datetime.strptime(x, "%B %d, %Y")
    elif re.search(r'[A-Z]+\s[0-9]+', x):
        return datetime.strptime(x + ", 2020", "%B %d, %Y")
    days_ago = int(re.search(r'([0-9]+) DAYS AGO', x).groups(0)[0])
    return last_modified.replace(day=last_modified.day - days_ago)


def get_drop_times(x):
    # pre-filtered on drop_post == True
    drop_times = re.findall(r'([0-9]{1,2}:[0-9]{2}\s*[apAP]?[mM]?|[0-9]{1,2}\s*[apAP][mM])', x)
    # the notion of time is missing from some of the older posts
    if len(drop_times) == 0:
        return nan

    drop_times_as_datetime = []
    for t in drop_times:
        info = list(re.search(r'([0-9]{1,2}):?([0-9]{0,2})\s*([apAP]?[mM]?)', t).groups())
        if len(info[1]) == 0:
            info[1] = "00"
        if len(info[2]) == 0:
            info[2] = ("am" if int(info[0]) < 12 else "pm")
        if len(info[2]) == 1:
            info[2] = info[2] + "m"
        dt = datetime.strptime(info[0] + ":" + info[1] + " " + info[2], "%I:%M %p")
        drop_times_as_datetime.append(dt)
    return sorted(drop_times_as_datetime)
            

###
df = pandas.read_csv(csv_file, index_col="id")
df.dropna(how="all", subset=["age", "likes", "post_text"], inplace=True)

df["post_date"] = df["age"].apply(convert_date)
del df["age"]
df["post_weekday"] = df["post_date"].apply(lambda x : weekdays[x.weekday()])
df["post_month"] = df["post_date"].apply(lambda x : "{0:%B}".format(x))
df["post_day"] = df["post_date"].apply(lambda x : x.day)
df["post_year"] = df["post_date"].apply(lambda x : x.year)
del df["post_date"]

df["drop_post"] = df["post_text"].apply(lambda x : (True if type(x) is str
                                                    and re.search(r'\bsold\s+out\b', x, re.I)
                                                    else False))

df["times"] = df.apply(lambda x : (get_drop_times(x["post_text"]) if x["drop_post"] else nan), axis=1)
df["drop_start"] = df["times"].apply(lambda x : (x[0] if type(x) is list else nan))
df["drop_end"] = df["times"].apply(lambda x : (x[-1] if type(x) is list else nan))
del df["times"]
df["drop_duration_min"] = df["drop_end"] - df["drop_start"]
df["drop_duration_min"] = df["drop_duration_min"].apply(lambda x : x.total_seconds() / 60)
df["drop_start_hour_24"] = df["drop_start"].apply(lambda x : x.hour)
df["drop_end_hour_24"] = df["drop_end"].apply(lambda x : x.hour)
del df["drop_start"]
del df["drop_end"]

del df["post_text"]

print(df[df["drop_post"] == True]["post_weekday"].value_counts())

df.to_csv("troon_instagram_clean_post_data.csv")
