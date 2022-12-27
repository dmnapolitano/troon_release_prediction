# Based on https://medium.com/swlh/tutorial-web-scraping-instagrams-most-precious-resource-corgis-235bf0389b0c
# and https://github.com/jnawjux/web_scraping_corgis/blob/master/insta_scrape.py

# THIS ALMOST WORKS
# Log in to Instagram, exit Chrome, then
# start Google Chrome from the command line with the `--remote-debugging-port=9222` argument.
# The issue is that Instagram DRAMATICALLY changed the generated code per post :(

from time import sleep
import argparse
from os.path import exists
from html import unescape

from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas
from numpy import nan


def get_data(url):
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    browser = Chrome(options=options)
    browser.get(url)

    likes = nan
    age = nan
    comment = nan
    post_date = nan

    try:
        # This captures the standard like count. 
        likes = browser.find_element(By.XPATH,
            """//*[@id="react-root"]/section/main/div/div/
            article/div[2]/section[2]/div/div/button""").text.split()[0]
        likes = int(likes.replace(",", ""))

        age = browser.find_element_by_css_selector("a time").text

        comment = unescape(browser.find_element(By.XPATH,
            """//*[@id="react-root"]/section/main/div/div/
            article/div[2]/div[1]/ul/div/li/div/div/div[2]/span""").text)
    except:
        from bs4 import BeautifulSoup
        import json
        soup = BeautifulSoup(browser.page_source, features="html5lib")
        info = json.loads(soup.findAll("script", type="application/ld+json")[0].string)
        comment = unescape(info["caption"])
        post_date = info["uploadDate"]
        likes = int(info["interactionStatistic"]["userInteractionCount"])

    browser.close()

    return {"URL" : url, "likes" : likes, "age" : age,
            "post_text" : comment, "post_date" : post_date}


def go(post_urls, df):
    for url in post_urls:
        try:
            data = get_data(url)
            print(data)
            df = df.append(data, ignore_index=True)
            sleep(10)
        except IndexError as e:
            break

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=("Scrape data from TROON Instagram posts.  "
                                                  + "Will either create or append to "
                                                  + "troon_instagram_raw_post_data.csv."))
    parser.add_argument("url_file", help=("Path to a file containing a list of TROON Instagram "
                                          + "post URLs, one per line, typicaly created by "
                                          + "get_post_links_01.py.  URLs in this file that "
                                          + "have already been scraped will be skipped."))
    args = parser.parse_args()
    
    with open(args.url_file, 'r') as fh:
        post_urls = [line.strip() for line in fh]

    output_file = "troon_instagram_raw_post_data.csv"

    if exists(output_file):
        df = pandas.read_csv(output_file, index_col="id")
        new_urls = set(post_urls).difference(set(df["URL"]))
        df = go(new_urls, df)
    else:
        df = pandas.DataFrame()
        df = go(post_urls, df)

    df.index.name = "id"
    df["likes"] = df["likes"].astype("Int64")
    df.to_csv(output_file)
