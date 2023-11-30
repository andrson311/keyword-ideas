import os
from google.ads.googleads.client import GoogleAdsClient

ROOT = os.path.dirname(__file__)

client = GoogleAdsClient.load_from_storage(os.path.join(ROOT, 'google-ads.yaml'))


