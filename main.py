import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from phone import number

pepnumber = phonenumbers.parse(number)
location = geocoder.description_for_number(pepnumber, "en")
service_provider = carrier.name_for_number(pepnumber, "en")
time_zone = timezone.time_zones_for_number(pepnumber)
print(location)