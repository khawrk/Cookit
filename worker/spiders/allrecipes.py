"""AllRecipes spider.

Run via: scrapy runspider worker/spiders/allrecipes.py
"""
import json
import logging
import os

import scrapy
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Scrapy settings applied at spider level
custom_settings = {
    "DOWNLOAD_DELAY": 2,
    "AUTOTHROTTLE_ENABLED": True,
    "ROBOTSTXT_OBEY": True,
    "USER_AGENT": "Cookit/1.0 (educational project; contact: admin@example.com)",
    "LOG_LEVEL": "INFO",
}


class AllRecipesSpider(scrapy.Spider):
    name = "allrecipes"
    allowed_domains = ["allrecipes.com"]
    start_urls = ["https://www.allrecipes.com/recipes/"]
    custom_settings = custom_settings

    def parse(self, response):
        for link in response.css("a[href*='/recipe/']::attr(href)").getall():
            if "/recipe/" in link:
                yield response.follow(link, self.parse_recipe)

        next_page = response.css("a.next-page::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_recipe(self, response):
        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            return

        ingredients = []
        for li in soup.select("[class*='ingredient']"):
            text = li.get_text(strip=True)
            if text:
                ingredients.append({"name": text, "quantity": None, "unit": None})

        steps = []
        for idx, li in enumerate(soup.select("[class*='step'] p, [class*='instructions'] li"), start=1):
            text = li.get_text(strip=True)
            if text:
                steps.append({"step_number": idx, "instruction": text})

        if not ingredients or not steps:
            return

        yield {
            "title": title,
            "source_url": response.url,
            "ingredients": ingredients,
            "steps": steps,
            "cuisine": None,
            "tags": [],
        }
