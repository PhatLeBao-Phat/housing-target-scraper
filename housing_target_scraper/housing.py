class Listing:
    def __init__(
        self,
        link : str = None,
        rent : str = None, 
        size : str = None,
        property_type : str = None, 
        location : str = None, 
        title : str = None, 
        street : str = None, 
        description : str = None, 
        seo : str = None,
    ):
        self.link = link 
        self.size = size
        self.rent = rent 
        self.property_type = property_type
        self.location = location
        self.title = title
        self.street = street 
        self.description = description
        self.seo = seo

        