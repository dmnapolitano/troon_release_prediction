import re
from datetime import datetime
from os.path import getmtime

import pandas
from numpy import nan


# TODO: try to extract the number of cans per release and the per-person allotment.


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
        if len(info[2]) == 0:
            info[2] = ("am" if int(info[0]) >= 9 and int(info[0]) < 12 else "pm")
        if len(info[2]) == 1:
            info[2] = info[2] + "m"
        dt = datetime.strptime(info[0] + ":" + info[1] + " " + info[2], "%I:%M %p")
        release_times_as_datetime.append(dt)
    return sorted(release_times_as_datetime)
            

###
if __name__ == "__main__":
    df = pandas.read_csv(csv_file, index_col="id")
    df.dropna(how="all", subset=["age", "likes", "post_text"], inplace=True)

    df["post_date"] = df["age"].apply(convert_date)
    del df["age"]
    df["post_weekday"] = df["post_date"].apply(lambda x : weekdays[x.weekday()])
    df["post_month"] = df["post_date"].apply(lambda x : "{0:%B}".format(x))
    df["post_day"] = df["post_date"].apply(lambda x : x.day)
    df["post_year"] = df["post_date"].apply(lambda x : x.year)
    del df["post_date"]

    df["release_post"] = df["post_text"].apply(lambda x : (True if type(x) is str
                                                           and re.search(r'\bsold\s+out\b', x, re.I)
                                                           else False))
    
    df["times"] = df.apply(lambda x : (get_release_times(x["post_text"]) if x["release_post"] else nan), axis=1)
    df["release_start"] = df["times"].apply(lambda x : (x[0] if type(x) is list else nan))
    df["release_end"] = df["times"].apply(lambda x : (x[-1] if type(x) is list else nan))
    del df["times"]
    df["release_duration_min"] = df["release_end"] - df["release_start"]
    df["release_duration_min"] = df["release_duration_min"].apply(lambda x : x.total_seconds() / 60)
    df["release_start_hour_24"] = df["release_start"].apply(lambda x : x.hour)
    df["release_end_hour_24"] = df["release_end"].apply(lambda x : x.hour)
    del df["release_start"]
    del df["release_end"]
    
    del df["post_text"]
    
    print(df[df["release_post"] == True]["post_weekday"].value_counts())
    
    df.to_csv("troon_instagram_clean_post_data.csv")
