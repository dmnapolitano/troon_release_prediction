# Based on https://medium.com/swlh/tutorial-web-scraping-instagrams-most-precious-resource-corgis-235bf0389b0c
# and https://github.com/jnawjux/web_scraping_corgis/blob/master/insta_scrape.py

from time import sleep
import sys

from selenium.webdriver import Chrome
import pandas
from numpy import nan


def get_data(url):
    browser = Chrome()
    browser.get(url)

    try:
        # This captures the standard like count. 
        likes = browser.find_element_by_xpath(
            """//*[@id="react-root"]/section/main/div/div/
            article/div[2]/section[2]/div/div/button""").text.split()[0]
        likes = int(likes.replace(",", ""))
    except:
        # probably a video
        likes = nan

    try:
        age = browser.find_element_by_css_selector("a time").text
    except:
        # TODO
        age = nan

    try:
        comment = browser.find_element_by_xpath(
            """//*[@id="react-root"]/section/main/div/div/
            article/div[2]/div[1]/ul/div/li/div/div/div[2]/span""").text
    except:
        # TODO
        comment = nan

    browser.close()

    return {"URL" : url, "likes" : likes, "age" : age, "post_text" : comment}


###
with open(sys.argv[1], 'r') as fh:
    post_urls = [line.strip() for line in fh]

df = pandas.DataFrame()
for url in post_urls:
    data = get_data(url)
    print(data)
    df = df.append(data, ignore_index=True)
    sleep(10)

df.index.name = "id"
df.to_csv("troon_instagram_raw_post_data.csv")
