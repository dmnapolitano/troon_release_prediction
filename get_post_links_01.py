"""Get the Troon links from Instagram
"""
import time
from argparse import ArgumentParser
from typing import Optional, Set

from playwright._impl._page import Page
from playwright.sync_api import Playwright, sync_playwright


class Scroller:
    """Scroll through an infinite-scroll page
    and collect all of the links

    Args:
        page: The page to scroll
        url: The URL to append to the link (optional)
        pause: The amount of time time to pause between scrolls (optional)
    """

    def __init__(
        self,
        page: Page,
        url: str = "",
        pause: int = 1
    ):
        self.url = url
        self.page = page
        self.pause = pause
        self._hrefs = None

    @property
    def hrefs(self) -> Optional[Set[str]]:
        """Get the hrefs
        """
        if self._hrefs is not None:
            return set(self._hrefs)
    
    def _get_hrefs(
        self,
    ):
        """Get all of the `a` elements, and extract the hrefs
        """
        assert isinstance(self._hrefs, list)

        # get all of the `a` elements
        # TODO: Make the locator configurable
        elements = self.page.locator("a[href^='/p/']")
        count = elements.count()

        # loop through and extract
        for i in range(count):
            href = elements.nth(i).get_attribute("href")
            self._hrefs.append(f"{self.url}{href}")

    def scroll(
        self,
    ):
        """Scroll through the pages
        """
        # reset the hrefs
        self._hrefs = []

        # get the hrefs
        self._get_hrefs()

        # create interval ID variable to determine the scrolling
        self.page.evaluate(
            """
            var intervalID = setInterval(function () {
                var scrollingElement = (document.scrollingElement || document.body);
                scrollingElement.scrollTop = scrollingElement.scrollHeight;
            }, 200);
            """
        )
        prev_height = None
        while True:
            # get the hrefs from the current page 
            try:
                self._get_hrefs()
            except:
                continue

            # get the current scroll height
            curr_height = self.page.evaluate("(window.innerHeight + window.scrollY)")

            # check the condition and break when we reach the end of the page
            if not prev_height:
                prev_height = curr_height
                time.sleep(self.pause)
            elif prev_height == curr_height:
                self.page.evaluate("clearInterval(intervalID)")
                break
            else:
                prev_height = curr_height
                time.sleep(self.pause)

def run(
    outputfile: str,
    playwright: Playwright,
    username: str,
    password: str,
    headless: bool = True
) -> None:
    """Run the script 

    Args:
        outputfile: The outputfile path
        playwright: The playwright object
        username: The Instagram username
        password: The Instagram password
        headless: Whether to run in headless mode
    """
    url = "https://www.instagram.com"

    # start the browser
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()

    # browse to Instagram
    page = context.new_page()
    page.goto(url)

    # log in to Instagram with credentials
    page.get_by_label("Phone number, username, or email").click()
    page.get_by_label("Phone number, username, or email").fill(username)
    page.get_by_label("Password").click()
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Log in").first.click()
    page.get_by_role("button", name="Not Now").click()
    page.get_by_role("button", name="Not Now").click()

    # search for Troon and grab the posts
    page.get_by_role("button", name="Search Search").click()
    page.get_by_placeholder("Search").fill("troon")
    page.get_by_role("link", name="troonbrewing").filter(has_text="troonbrewing").click()
    page.get_by_role("tab", name="Posts").click()

    # scroll through and get the hrefs
    scroller = Scroller(page, url)
    scroller.scroll()

    # get the hrefs
    hrefs = scroller.hrefs
    assert hrefs is not None

    # write out the file
    with open(outputfile, "w") as fh:
        for link in hrefs:
            fh.write(link + "\n")

    # close the browser
    context.close()
    browser.close()


if __name__ == "__main__":

    # get the arguments
    parser = ArgumentParser("Get the links from Instagram")
    parser.add_argument("-u", "--username")
    parser.add_argument("-p", "--password")   
    parser.add_argument("-o", "--outputfile")

    args = parser.parse_args()

    # run the scraping process
    with sync_playwright() as play:
        run(args.outputfile, play, args.username, args.password)
