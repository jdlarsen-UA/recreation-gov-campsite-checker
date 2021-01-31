from campfinder import FindCampsite
import time


class ThatAsehole(object):
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

    def go_camp(self, popup=True):
        """
        Method to continue scraping until a camping option is available.

        Parameters
        ----------
        popup : bool
            if true, opens the reservation.gov site
        """
        avail = False
        while not avail:
            fc = FindCampsite(self.campgrounds, self.start_date,
                              self.end_date, self.site_type)
            avail = fc.go_camp()
            if avail:
                fc.show_campsite()

if __name__ == "__main__":
    parks = ['234015', ]
    start_date = '2021-11-6'
    end_date = '2021-11-8'

    that = ThatAsehole(parks, start_date, end_date)
    avail = that.go_camp()
