# Nicholas Urban
# 09/14/2018

import requests
import json
import config
from re import sub
import pandas as pd
from getpass import getpass
from os import path

requests.packages.urllib3.disable_warnings() 

def authenticate(USERNAME, PASSWORD):
    
    if len(USERNAME) > 0 & len(PASSWORD) > 0:
        pass
    else:
        USERNAME = input('Please enter your Viome email address: ')
        PASSWORD = getpass('Please enter your password: ')

    auth_body = json.dumps({
        "email": USERNAME,
        "rememberMe": json.loads("true"), # Escape the stupid "true" that the API cannot read for some reasons
        "password": PASSWORD
    })
    
    try:
        r = requests.post(config.AUTH_HOST, 
            data=auth_body, 
            headers=config.HEADERS, 
            verify=False)
        
        print('\nAuthenticating to Viome status code: [{}]'.format(r.status_code))
        
        if(r.status_code != 200):
            print('Invalid credentials\n')
            abort = input('Type (R) to retry, (Q) to quit: ')
            raise Exception
        else:
            return r.headers['Set-Cookie']

    except:
        if(abort.upper() == 'R'):
            authenticate(USERNAME,PASSWORD)
        else:
            return ''

def get_recommendations(cookie):
    '''
    After authenticating to API, get the JSON response containing all recommendation data. Note that the reponse payload contains HTML, so we must deal with that accordingly.
    
        Args:
            cookie: the cookie file generated from authentication. 
        
        Returns:
            The food recommendations list as a JSON object.
    '''

    config.HEADERS['Cookie'] = cookie

    r = requests.get(config.REC_HOST, 
        headers=config.HEADERS, 
        verify=False)
    
    # Strip non-unicode characters. Fetch only the recommendations necessary for our purposes. Convert string into JSON object.
    r = sub(r'[^\x00-\x7F]+',' ', (str(r.content)))
    r = r.replace('b\'{', '{').split('payload":')[1].split('supplementDisclaimer')[0]
    r = r[:-2] + "}}" 
    return json.loads(r)

def create_dataframe(response):
    ''' 
    Builds a dataframe from the "foods" object in the Viome response.

        Args:
            response: food list JSON object generated from get_recommendations def.
        
        Returns:
            Pandas DataFrame of all food sorted by consumption recommendations (Superfood, Indulge, EnjoY, Minimize, Avoid).
    '''
    
    veggies = response['foodList'][0]['foods']
    meats = response['foodList'][1]['foods']
    fruits_grains = response['foodList'][2]['foods']
    fats_proteins = response['foodList'][3]['foods']
    foods = veggies + meats + fruits_grains + fats_proteins

    df = pd.DataFrame(foods, columns=['foodTitle', 'dietRankTitle', 'servingSize'], )
    print('Processing: {} records'.format(df.shape[0]))

    df.columns = ['Food', 'Amount', 'Servings']
    df.fillna(value='-', axis=1, inplace=True)
    df.replace(to_replace='', value='-', inplace=True)

    df['Amount'] = pd.Categorical(df['Amount'], ['Superfood', 'Indulge', 'Enjoy', 'Minimize', 'Avoid'])
    df['Servings'] = df['Servings'].str.title()

    df = df.sort_values(by=['Amount', 'Food'], ascending=[True, True])
    return df

def write_files(df):
    '''
    Generate a CSV and HTML file for the Viome results in the same directory as the file, named "viome_food.csv" and "viome_food.html". The HTML file is formatted by the style.css file
    
        Args: 
            df: DataFrame containing all food recommendations.
    '''

    FILE_PATH = path.dirname(path.realpath(__file__)) + "/viome_food."
    print('Writing files to: ' + FILE_PATH[:-1], end="")
    pd.set_option('colheader_justify', 'center')   # FOR TABLE <th>

    html_string = '''
        <html>
        <head><title>HTML Pandas Dataframe with CSS</title></head>
        <link rel="stylesheet" type="text/css" href="style.css"/>
        <body>
            {table}
        </body>
        </html>
    '''

    # Output the HTML and CSV files
    with open(FILE_PATH + 'html', 'w') as f:
        f.write(html_string.format(table=df.to_html(classes='mystyle', index=False)))
        df.to_csv(FILE_PATH + 'csv', index=False)
    
    print(' [SUCCESS]\n')

if __name__ == "__main__":
    
    # Try to authenticate first. Handle errors differently here than the rest of the program.
    try:
        cookie = authenticate(config.USERNAME, config.PASSWORD)
    except Exception as e:
        pass

    try:
        response = get_recommendations(cookie)
        df = create_dataframe(response)
        write_files(df)
    except Exception as e:
        print('An error occurred\n')
        print(e)