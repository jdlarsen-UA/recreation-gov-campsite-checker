from campfinder import FindCampsite
import json
import time
import os


class IneedToCamp(object):
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
        self.start_date = start_date
        self.end_date = end_date
        self.site_type = site_type

    def notify(self, times=100):
        """
        Method to play a tone and notify of available camping

        Returns
        -------
            None
        """
        try:
            import playsound
        except ImportError:
            return

        ws = os.path.abspath(os.path.dirname(__file__))
        audio = os.path.join(ws, "data", "swinging-617.mp3")
        time.sleep(5)
        n = 0
        while n < times:
            playsound.playsound(audio)

    def go_camp(self, popup=True):
        """
        Method to continue scraping until a camping option is available.

        Parameters
        ----------
        popup : bool
            if true, opens the reservation.gov site
        """
        avail = False
        n = 0
        m = 0
        while not avail:
            fc = FindCampsite(self.campgrounds, self.start_date,
                              self.end_date, self.site_type)
            try:
                avail = fc.go_camp()
            except:
                print('exception: {}'.format(n))
                n += 1
                time.sleep(5)
            if avail:
                if popup:
                    fc.show_campsite()
            else:
                print('try number: {}'.format(m))
                m += 1
                time.sleep(7)


if __name__ == "__main__":
    with open("master_list.json") as foo:
        parks = json.load(foo)

    park = parks['pinnacles']
    start_date = '2021-3-6'
    end_date = '2021-3-7'

    intc = IneedToCamp(park, start_date, end_date)
    avail = intc.go_camp()
