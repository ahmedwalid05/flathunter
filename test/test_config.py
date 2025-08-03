import unittest
import tempfile
import os.path
import os
from flathunter.config import Config
from test.utils.config import StringConfig

class ConfigTest(unittest.TestCase):

    DUMMY_CONFIG = """
urls:
  - https://www.immowelt.de/liste/berlin/wohnungen/mieten?roomi=2&prima=1500&wflmi=70&sort=createdate%2Bdesc
    """

    EMPTY_FILTERS_CONFIG = """
urls:
  - https://www.immowelt.de/liste/berlin/wohnungen/mieten?roomi=2&prima=1500&wflmi=70&sort=createdate%2Bdesc

filters:

"""

    LEGACY_FILTERS_CONFIG = """
urls:
  - https://www.immowelt.de/liste/berlin/wohnungen/mieten?roomi=2&prima=1500&wflmi=70&sort=createdate%2Bdesc

excluded_titles:
  - Title
  - Another
"""

    FILTERS_CONFIG = """
urls:
  - https://www.immowelt.de/liste/berlin/wohnungen/mieten?roomi=2&prima=1500&wflmi=70&sort=createdate%2Bdesc

filters:
    excluded_titles:
        - fish
    min_size: 30
    max_size: 100
    min_price: 500
    max_price: 1500
    min_rooms: 2
    max_rooms: 5
"""

    def test_loads_config(self):
        created = False
        if not os.path.isfile("config.yaml"):
            config_file = open("config.yaml", "w")
            config_file.write(self.DUMMY_CONFIG)
            config_file.flush()
            config_file.close()
            created = True
        config = Config("config.yaml")
        self.assertTrue(len(config.get('urls', [])) > 0, "Expected URLs in config file")
        if created:
            os.remove("config.yaml")

    def test_loads_config_at_file(self):
       with tempfile.NamedTemporaryFile(mode='w+') as temp:
          temp.write(self.DUMMY_CONFIG)
          temp.flush()
          config = Config(temp.name) 
       self.assertTrue(len(config.get('urls', [])) > 0, "Expected URLs in config file")

    def test_loads_config_from_string(self):
       config = StringConfig(string=self.EMPTY_FILTERS_CONFIG)
       self.assertIsNotNone(config)
       my_filter = config.get_filter()
       self.assertIsNotNone(my_filter)

    def test_loads_legacy_config_from_string(self):
       config = StringConfig(string=self.LEGACY_FILTERS_CONFIG)
       self.assertIsNotNone(config)
       my_filter = config.get_filter()
       self.assertIsNotNone(my_filter)
       self.assertTrue(len(my_filter.filters) > 0)

    def test_loads_filters_config_from_string(self):
       config = StringConfig(string=self.FILTERS_CONFIG)
       self.assertIsNotNone(config)
       my_filter = config.get_filter()
       self.assertIsNotNone(my_filter)

    def test_defaults_fields(self):
       config = StringConfig(string=self.FILTERS_CONFIG)
       self.assertIsNotNone(config)
       self.assertEqual(config.database_location(), os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/.."))

    def test_contact_form_config(self):
        """Test that contact form configuration is read correctly"""
        contact_form_config = """
urls:
  - https://www.immowelt.de/liste/berlin/wohnungen/mieten?roomi=2&prima=1500&wflmi=70&sort=createdate%2Bdesc

contact_form:
  firstname: "Test"
  lastname: "User"
  emailAddress: "test@example.com"
  phoneNumber: "+49 123 456789"
  address:
    postcode: "12345"
    houseNumber: "1"
    street: "Test Street"
    city: "Berlin"
  employmentRelationship: "EMPLOYEE"
  income: "OVER_3000"
  numberOfPersons: "ONE_PERSON"
  applicationPackageCompleted: true
  hasPets: false
  petsInHousehold: ""
  message: "Test message"
  sendProfile: true
  profileImageUrl: "https://example.com/image.jpg"
"""
        config = StringConfig(string=contact_form_config)
        contact_config = config.contact_form_config()
        
        self.assertEqual(contact_config.get("firstname"), "Test")
        self.assertEqual(contact_config.get("lastname"), "User")
        self.assertEqual(contact_config.get("emailAddress"), "test@example.com")
        self.assertEqual(contact_config.get("phoneNumber"), "+49 123 456789")
        self.assertEqual(contact_config.get("address", {}).get("postcode"), "12345")
        self.assertEqual(contact_config.get("employmentRelationship"), "EMPLOYEE")
        self.assertEqual(contact_config.get("income"), "OVER_3000")
        self.assertEqual(contact_config.get("numberOfPersons"), "ONE_PERSON")
        self.assertTrue(contact_config.get("applicationPackageCompleted"))
        self.assertFalse(contact_config.get("hasPets"))
        self.assertEqual(contact_config.get("petsInHousehold"), "")
        self.assertEqual(contact_config.get("message"), "Test message")
        self.assertTrue(contact_config.get("sendProfile"))
        self.assertEqual(contact_config.get("profileImageUrl"), "https://example.com/image.jpg")

    def test_contact_form_config_empty(self):
        """Test that contact form configuration returns empty dict when not present"""
        config = StringConfig(string=self.FILTERS_CONFIG)
        contact_config = config.contact_form_config()
        self.assertEqual(contact_config, {})
