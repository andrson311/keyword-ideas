import os
import argparse
import pandas as pd
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

load_dotenv()
ROOT = os.path.dirname(__file__)
CUSTOMER_ID = os.getenv('CUSTOMER_ID')

LOCALE = 'en'
COUNTRY_CODE = 'US'

_DEFAULT_LOCATIONS = ['United States']
_DEFAULT_LANGUAGE_ID = '1000'

def get_keywords(client, keyword_texts, 
                 locations=_DEFAULT_LOCATIONS, 
                 language_id=_DEFAULT_LANGUAGE_ID, 
                 page_url=None):

    keyword_plan_idea_service = client.get_service('KeywordPlanIdeaService')

    keyword_plan_network = (
        client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
    )

    location_rns = []
    gtc_service = client.get_service('GeoTargetConstantService')
    gtc_request = client.get_type('SuggestGeoTargetConstantsRequest')
    gtc_request.locale = LOCALE
    gtc_request.country_code = COUNTRY_CODE
    gtc_request.location_names.names.extend(
        locations
    )
    gtc_results = gtc_service.suggest_geo_target_constants(gtc_request)
    for suggestion in gtc_results.geo_target_constant_suggestions:
        location_rns.append(suggestion.geo_target_constant.resource_name)

    language_rn = client.get_service('GoogleAdsService').language_constant_path(language_id)

    if not (keyword_texts or page_url):
        raise ValueError(
            'At least one of keywords or page URL is required'
        )

    request = client.get_type('GenerateKeywordIdeasRequest')
    request.customer_id = CUSTOMER_ID
    request.language = language_rn
    request.geo_target_constants = location_rns
    request.include_adult_keywords = False
    request.keyword_plan_network = keyword_plan_network

    if not keyword_texts and page_url:
        request.url_seed.url = page_url
    
    if keyword_texts and not page_url:
        request.keyword_seed.keywords.extend(keyword_texts)
        print('Keywords', request.keyword_seed.keywords)
    
    if keyword_texts and page_url:
        request.keyword_and_url_seed.url = page_url
        request.keyword_and_url_seed.keywords.extend(keyword_texts)
    
    keyword_ideas = keyword_plan_idea_service.generate_keyword_ideas(request)

    return keyword_ideas

def list_of_items(arg):
    return arg.split(',')

if __name__ == '__main__':
    
    google_ads_client = GoogleAdsClient.load_from_storage(os.path.join(ROOT, 'google-ads.yaml'))

    parser = argparse.ArgumentParser(
        description='Returns keyword ideas including their Google search metric data.'
    )

    parser.add_argument(
        '-k',
        '--keyword_texts',
        type=list_of_items,
        required=False,
        default=[],
        help='List of starter keywords'
    )

    parser.add_argument(
        '-l',
        '--locations',
        type=list_of_items,
        required=False,
        default=_DEFAULT_LOCATIONS,
        help='List of location names'
    )

    parser.add_argument(
        '-i',
        '--language_id',
        type=str,
        required=False,
        default=_DEFAULT_LANGUAGE_ID,
        help='The language criterion ID'
    )

    parser.add_argument(
        '-p',
        '--page_url',
        type=str,
        required=False,
        help='A URL address for extracting relevant keywords from'
    )

    args = parser.parse_args()

    try:
        keyword_ideas = get_keywords(
            client=google_ads_client,
            keyword_texts=args.keyword_texts,
            locations=args.locations,
            language_id=args.language_id,
            page_url=args.page_url
        )

        result = []

        for idea in keyword_ideas:
            result.append([
                idea.text, 
                idea.keyword_idea_metrics.avg_monthly_searches,
                idea.keyword_idea_metrics.competition.name
            ])
        
        df = pd.DataFrame(result)
        df.to_excel(
            os.path.join(ROOT, 'output.xlsx'),
            header=['Keyword', 'Average monthly searches', 'Competition'],
            index=False
        )

    except GoogleAdsException as ex:
        print(
            f'Request with ID "{ex.request_id}" failed with status '
            f'"{ex.error.code().name}" and includes the following errors:'
        )
        for error in ex.failure.errors:
            print(f'\tError with message "{error.message}".')
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    print(f"\t\tOn field: {field_path_element.field_name}")