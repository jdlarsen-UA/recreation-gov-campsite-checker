#!/usr/bin/env python3

import json
import logging
import webbrowser
import datetime as dt
from dateutil import rrule
from itertools import count, groupby

import requests
from fake_useragent import UserAgent

LOG = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(process)s - %(levelname)s - %(message)s")
sh = logging.StreamHandler()
sh.setFormatter(formatter)
LOG.addHandler(sh)

BASE_URL = "https://www.recreation.gov"
AVAILABILITY_ENDPOINT = "/api/camps/availability/campground/"
MAIN_PAGE_ENDPOINT = "/api/camps/campgrounds/"
WEB_ENDPOINT = "/camping/campsites/"


INPUT_DATE_FORMAT = "%Y-%m-%d"
ISO_DATE_FORMAT_REQUEST = "%Y-%m-%dT00:00:00.000Z"
ISO_DATE_FORMAT_RESPONSE = "%Y-%m-%dT00:00:00Z"

SUCCESS_EMOJI = "🏕"
FAILURE_EMOJI = "❌"


class FindCampsite():
    """
    Class method for finding a campsite in using the recreation.gov
    API.

    Parameters
    ----------
    campgrounds : list or str
        list or string of recreation.gov campgrounds ids
    start_date : str
        YYYY-MM-DD check in date
    end_date : str
        YYYY-MM-DD check out date
    site_type : str
        default is all types, also can accept "STANDARD NONELECTRIC" and
        other valid api parameters

    """
    def __init__(self, campgrounds, start_date='2020-11-6',
                 end_date='2020-11-8', site_type=""):
        if not isinstance(campgrounds, list):
            campgrounds = [campgrounds]

        self.campgrounds = campgrounds
        self.start_date = self._set_date(start_date)
        self.end_date = self._set_date(end_date)
        nights = self.end_date - self.start_date
        self.nights = int(nights.days)
        self.site_type = site_type
        self.headers = {"User-Agent": UserAgent().random}
        self.available = []

    @property
    def campground_names(self):
        names = []
        for i in self.campgrounds:
            names.append(self._get_site_name(i))
        return names

    def _set_date(self, dstr):
        y, m, d = [int(i) for i in dstr.split("-")]
        return dt.date(y, m, d)

    def _format_date(self, date_object,
                     format_string=ISO_DATE_FORMAT_REQUEST):
        """
        This function doesn't manipulate the date itself at all, it just
        formats the date in the format that the API wants.
        """
        date_formatted = dt.datetime.strftime(date_object, format_string)
        return date_formatted

    def _valid_date(self, s):
        try:
            return dt.datetime.strptime(s, INPUT_DATE_FORMAT)
        except ValueError:
            msg = "Not a valid date: '{0}'.".format(s)
            raise TypeError(msg)

    def __get_park_information(self, campground_id):
        """
        This function consumes the user intent, collects the necessary information
        from the recreation.gov API, and then presents it in a nice format for the
        rest of the program to work with. If the API changes in the future, this is
        the only function you should need to change.

        The only API to get availability information is the `month?` query param
        on the availability endpoint. You must query with the first of the month.
        This means if `start_date` and `end_date` cross a month bounday, we must
        hit the endpoint multiple times.

        The output of this function looks like this:

        {"<campsite_id>": [<date>, <date>]}

        Where the values are a list of ISO 8601 date strings representing dates
        where the campsite is available.

        Notably, the output doesn't tell you which sites are available. The rest of
        the script doesn't need to know this to determine whether sites are available.
        """

        # Get each first of the month for months in the range we care about.
        start_of_month = dt.datetime(self.start_date.year,
                                     self.start_date.month,
                                     1)
        months = list(rrule.rrule(rrule.MONTHLY,
                                  dtstart=start_of_month,
                                  until=self.end_date))

        # Get data for each month.
        api_data = []
        for month_date in months:
            params = {"start_date": self._format_date(month_date)}
            LOG.debug(
                "Querying for {} with these params: {}".format(campground_id,
                                                               params))
            url = "{}{}{}/month?".format(BASE_URL,
                                         AVAILABILITY_ENDPOINT,
                                         campground_id)
            resp = self._send_request(url, params)
            api_data.append(resp)

        # Collapse the data into the described output format.
        # Filter by campsite_type if necessary.
        data = {}
        for month_data in api_data:
            for campsite_id, campsite_data in month_data["campsites"].items():
                available = []
                for date, availability_value in campsite_data["availabilities"].items():
                    if availability_value != "Available":
                        continue
                    if self.site_type and self.site_type != campsite_data["campsite_type"]:
                        continue
                    available.append(date)
                if available:
                    a = data.setdefault(campsite_id, [])
                    a += available

        return data

    def _get_num_available_sites(self, park_information):

        maximum = len(park_information)
        num_available = 0
        num_days = (self.end_date - self.start_date).days
        dates = [self.end_date - dt.timedelta(days=i)
                 for i in range(1, num_days + 1)]

        dates = set(
            self._format_date(i, format_string=ISO_DATE_FORMAT_RESPONSE)
            for i in dates)

        if self.nights not in range(1, num_days + 1):
            self.nights = num_days
            LOG.debug('Setting number of nights to {}.'.format(self.nights))

        for site, availabilities in park_information.items():
            # List of dates that are in the desired range for this site.
            desired_available = []
            for date in availabilities:
                if date not in dates:
                    continue
                desired_available.append(date)
            if desired_available and self.consecutive_nights(desired_available,
                                                             self.nights):
                self.available.append(site)
                num_available += 1
                LOG.debug("Available site {}: {}".format(num_available, site))

        return num_available, maximum

    def consecutive_nights(self, available, nights):
        """
        Returns whether there are `nights` worth of consecutive nights.
        """
        ordinal_dates = [
            dt.datetime.strptime(dstr, ISO_DATE_FORMAT_RESPONSE).toordinal()
            for dstr in available]
        c = count()
        longest_consecutive = max((list(g) for _, g in groupby(ordinal_dates,
                                                               lambda
                                                                   x: x - next(
                                                                   c))),
                                  key=len)
        return len(longest_consecutive) >= nights

    def go_camp(self):
        out = []
        availabilities = False
        for park_id in self.campgrounds:
            park_information = self.__get_park_information(park_id)
            msg = "Information for park {}: {}".format(
                park_id,
                json.dumps(park_information, indent=2)
            )

            LOG.debug(msg)
            name_of_site = self._get_site_name(park_id)
            current, maximum = self._get_num_available_sites(park_information)

            if current:
                emoji = SUCCESS_EMOJI
                availabilities = True
            else:
                emoji = FAILURE_EMOJI

            out.append(
                "{} {} ({}): {} site(s) available out of {} site(s)".format(
                    emoji, name_of_site, park_id, current, maximum
                )
            )

        if availabilities:
            print(
                "There are campsites available from {} to {}!!!".format(
                    self.start_date.strftime(INPUT_DATE_FORMAT),
                    self.end_date.strftime(INPUT_DATE_FORMAT),
                )
            )
        else:
            print("There are no campsites available :(")
        print("\n".join(out))

        return availabilities

    def show_campsite(self):
        if len(self.available) > 5:
            available = self.available[0:5]
        else:
            available = self.available

        for site in available:
            url = "{}{}{}".format(BASE_URL, WEB_ENDPOINT, site)
            webbrowser.open(url)

    def _get_site_name(self, campground_id):
        url = "{}{}{}".format(BASE_URL, MAIN_PAGE_ENDPOINT, campground_id)
        resp = self._send_request(url, {})
        return resp["campground"]["facility_name"]

    def _send_request(self, url, params):
        resp = requests.get(url, params=params, headers=self.headers)
        if resp.status_code != 200:
            raise RuntimeError(
                "failedRequest",
                "ERROR, {} code received from {}: {}".format(
                    resp.status_code, url, resp.text
                ),
            )
        return resp.json()


if __name__ == "__main__":
    with open("master_list.json") as foo:
        parks = json.load(foo)

    park = parks['pinnacles']
    start_date = '2021-11-6'
    end_date = '2021-11-8'

    fc = FindCampsite(park, start_date, end_date)
    avail = fc.go_camp()
    if avail:
        fc.show_campsite()
