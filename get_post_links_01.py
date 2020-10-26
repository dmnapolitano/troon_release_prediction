# Based on https://medium.com/swlh/tutorial-web-scraping-instagrams-most-precious-resource-corgis-235bf0389b0c

from time import sleep
from datetime import datetime

import chromedriver_binary
from selenium.webdriver import Chrome


url = "https://www.instagram.com/troonbrewing/"
scroll_down = "window.scrollTo(0, document.body.scrollHeight);"
post_url_base = "https://www.instagram.com/p/"
today = datetime.now()
output_file = "troon_instagram_post_links_{}.lst".format(today.strftime("%m-%d-%Y"))

browser = Chrome()
browser.get(url)

post_links = set([])
while True:
    links = [a.get_attribute("href") for a in browser.find_elements_by_tag_name("a")]
    new_links = set([link for link in links if post_url_base in link and link not in post_links])
    if new_links.issubset(post_links):
        break
    post_links = post_links.union(new_links)
    browser.execute_script(scroll_down)
    sleep(10)

with open(output_file, 'w') as fh:
    for link in post_links:
        fh.write(link + "\n")

print("Wrote {}.".format(output_file))
