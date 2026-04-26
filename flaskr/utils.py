""" Handful of utility methods for reuse in several areas """


import requests
import werkzeug
import flask


"""
_api_request formulates an API GET request to the dnd5e api, returning the payload from the 
https action. 
"""
def _api_request(field: str=""):
    """
    Generate and send a GET request for the input field to the API. 
    Input: field string to request from API 
    Output: Output of a GET request to the API for the requested field 
    """
    base_url = "https://www.dnd5eapi.co/api/2014/"
    request_url = base_url + field
    payload = {}
    headers = {
        'Accept': 'application/json'
    }
    response = requests.request("GET", request_url, headers=headers, data=payload)
    ## Convert response to dict and return 
    response = response.json()
    return response


""" 
Extract item extracts the specified dict key:val item from a list of dicts 
and returns as a list of the dtype of the value at that index in the dict
"""
def _extract_index(data: dict, tgt: str) -> list:
    """
    Extract the specified dict key:val item from a list of dicts and 
    return as a list of the dtype of the value at that index in the dict
    Input: data: dict containing list of dicts to extract from 
    tgt: string key to extract from
    Output: list of the dtype of the value at that index in the dict
    """
    return [item[tgt] for item in data['results']]
    
