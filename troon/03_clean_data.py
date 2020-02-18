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


###
df = pandas.read_csv(csv_file, index_col="id")
df.dropna(how="all", subset=["age", "likes", "post_text"], inplace=True)

df["post_date"] = df["age"].apply(convert_date)
del df["age"]
df["post_weekday"] = df["post_date"].apply(lambda x : weekdays[x.weekday()])
df["post_month"] = df["post_date"].apply(lambda x : "{0:%B}".format(x))
df["post_year"] = df["post_date"].apply(lambda x : x.year)

df["drop_post"] = df["post_text"].apply(lambda x : (True if type(x) is str
                                                    and re.search(r'\bsold\s+out\b', x, re.I)
                                                    else False))
print(df["drop_post"].value_counts())
