"""DF Triage program for inventory matching

Given an inventory of available blocks and a forecast from a customer, this
program will generate 3 separate dispatches, optimizing for minimal yield
delta, carat weight, and relative value. Visit README in the distribution
folder for more detail.

Written by Alex Chen and Andrzej Skoskiewicz 1/11/2021
"""

import os
"""
Modules for accessing Google sheets, which contain the input, output file and
Program Rough Sizing Bible, which is used as a configuration file for gem type
data
"""
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
"""
Modules used for the binary integer programming process
"""
import numpy as np
import pandas as pd
from pulp import *
"""
Used to write the resulting data into a temporary Excel file, which is then
transformed into a Google Sheets
"""
from datetime import datetime
import openpyxl
import xlsxwriter



# IMPORTANT: Do not change these following global variables unless changes are 
# made to the Program Rough Sizing Bible. If additional gems are added to the 
# gem types, currently at 15, then extend the variable PRSB_range, using the 
# standard Excel cell range format.

PRSB_V4 = "1yjpE4utVIDWf1HAp0gZqwXsWvURZJaLsLJDt7Wt1Moc"
PRSB_range = 'Wiring!A4:T18'
block_range = "Blocks"
forecast_range = "Forecast"
status_dict = {1: "Optimal", 0: "Not Solved", -1: "Infeasible", -2: "Unbounded", 
                -3: "Undefined"}

# This scope allows this program to access Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def load_sheet(sheet_id, sample_range):
    """Load a Google Sheet

    Given a sheet_id, which can be found in the URL of a Google Sheet, and a 
    sample_range, return the values found in that range
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id,
                                range=sample_range).execute()
    values = result.get('values', [])

    if not values:
        raise Exception("No data found")
    else:
        return values

def write_sheet(sheet_id, list_of_dfs):
    """Write a list of dataframes into a Google Sheet.

    Each dataframe in the list will be written in its entirity to a new sheet
    of the Google Sheet, with titles "Dashboard", "Yield", "Weight", "Value"
    """
    SAMPLE_SPREADSHEET_ID = sheet_id

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    requests = []
    new_sheets = ["Dashboard", "Yield", "Weight", "Value"]
    for each_sheet in new_sheets:
        requests.append({'addSheet': {'properties': {'title': each_sheet}}})

    body = {'requests': requests}

    result = sheet.batchUpdate(spreadsheetId=SAMPLE_SPREADSHEET_ID, 
                               body=body).execute()

    # Writes contents of dataframe to the sheet
    for df_index in range(len(list_of_dfs)):
        contents = list_of_dfs[df_index].T.reset_index().T.values.tolist()
        response_date = sheet.values().update(
            spreadsheetId=SAMPLE_SPREADSHEET_ID,
            valueInputOption='RAW',
            range=new_sheets[df_index],
            body=dict(
                majorDimension='ROWS',
                values=contents[1:])
        ).execute()

def get_df():
    """Loads the Program Rough Sizing bible.

    Extracts all information in the given range (specified in the global 
    variables). This information is returned in a Pandas dataframe.
    """
    PRSB_info = load_sheet(PRSB_V4, PRSB_range)
    column_labels = PRSB_info[0][1:]
    row_labels = [PRSB_info[i][0] for i in range(1,len(PRSB_info))]
    PRSB_data = [PRSB_info[i][1:] for i in range(1,len(PRSB_info))]
    PRSB_df = pd.DataFrame(PRSB_data, columns = column_labels, 
                           index = row_labels)
    return PRSB_df  


# The following functions are used for formatting cells in the output

def replace(x):
    """Replace - with _ in strings

    PuLP does not allow for "-" in its variable names, and some serial numbers
    contain this character. Therefore, we replace it with a PuLP-recognizable 
    character.
    """
    try:
        y= x.replace("-","_")
        return y
    except:
        return x

def percentage(x):
    """Format any floats as percentages.

    Headers are left as they should be
    """
    try:
        y = "{:.1%}".format(float(x))
        return y
    except:
        return x

def one_dp(x):
    """Formats any floats to 1 decimal place. 

    Headers are left as they should be 
    """
    try:
        y = float("{:.1f}".format(float(x)))
        return y
    except:
        return x

def get_input(input_file):
    """Loads input file into dataframes.

    Uses the load_sheet function to load the contents of the input Google
    Sheet, storing each sheet in the input file as a dataframe, and returning 
    two dataframes in total.
    """
    input_info_blocks = load_sheet(input_file, block_range)
    input_info_forecast = load_sheet(input_file, forecast_range)
    blocks_column_labels = input_info_blocks[0]
    blocks_data = [input_info_blocks[i] for i in range(1,
                                                       len(input_info_blocks))]
    blocks_df = pd.DataFrame(blocks_data, columns = blocks_column_labels)
    blocks_df["Serial Number"] = blocks_df["Serial Number"].apply(replace)
    blocks_df.set_index("Serial Number", inplace = True)
    blocks_df.drop_duplicates(inplace = True)
    forecast_column_labels = input_info_forecast[0]
    forecast_data = input_info_forecast[1:]
    forecast_df = pd.DataFrame(forecast_data, 
                               columns = forecast_column_labels)
    return blocks_df, forecast_df

def get_input_file():
    """Asks user for URL of input Google Sheet

    Gets a sheet_id from a URL, by identifying that the sheet_id of a Google
    Sheet comes after "d/" in the URL
    """
    print("Welcome to the DF Triage program.")
    print("First, check if your input sheet has been formatted correctly.")
    input_url = str(input("Paste your input Google Sheet URL: "))
    input_list = input_url.split("/")
    location_d = input_list.index("d")
    input_file = input_list[location_d+1]
    return input_file

def get_output_name():
    """Generates unique file name using datatime information

    For debugging processes, this names the temporary Excel file, which will
    be deleted from the system after successful completion
    """
    now = datetime.now()
    timestamp = str(now.strftime("%m-%d_%H_%M"))
    input_name = "Triage"
    output_file = f"{input_name}_{timestamp}.xlsx"
    return output_file


# Main section of the code

input_file = get_input_file()
PRSB_df = get_df()
df1, df2 = get_input(input_file)


# Cleaning the two input dataframes, so that they can be processed by our binary
# integer programming function
data_columns = ["X","Y","Z","Carats"]
for column in data_columns:
    df1[column] = df1[column].replace(r"^\s*$", np.nan, regex=True)
    df1[column] = df1[column].fillna(0)
    if column == "Z":
        try:
            df1[column] = df1[column].apply(lambda x: float(locale.atoi(x)))
        except:
            pass
    else:
        df1[column] = pd.to_numeric(df1[column])

# This checks if the Z column is formatted in mm or micrometers. If the latter,
# divides this value by 1000
try:
    if float(df1["Z"].to_list()[0]) > 500:
        df1["Z"] = df1["Z"].apply(lambda x: float(x/1000))
except:
    print("Empty data!")

numeric_columns = ["Forecast", "Relative Value"]
for column in numeric_columns:
    df2[column] = pd.to_numeric(df2[column])

# Converts the yield filters from string percentages to decimals
df2.loc[:, "Planned Yield Filter"]= df2.loc[:, "Planned Yield Filter"].apply(lambda x : float(x.strip("%"))/100)

# Boolean if the Apply Filter option has been triggered by the operator
filter_toggle = 1 if df2["Apply Filter?"].to_list()[0] == "Yes" else 0

# Establish forecast information from second sheet of excel file
types = list(df2["Type"])
num_types = len(types)
forecast_dict = dict(zip(types, df2["Forecast"]))
rel_values_dict = dict(zip(types, df2["Relative Value"]))
filter_dict = dict(zip(types, df2["Planned Yield Filter"]))

# Initialize lists to hold block data
serial_numbers = list(df1.index.values)
num_blocks = len(serial_numbers)
block_weights = list(df1["Carats"])

# This section takes the dimensional data provided by the input sheet, hardcoded
# data from the Program Rough Sizing Bible and combines them to calculate Planned
# Yield, Ideal Yield, Yield Delta, and Number of Gems produced for each block and 
# each type of gem in the forecast. The variables and equations follow the naming
# convention and equations in the Excel sheet, for easy debugging.

for each_type in types:
    num_list, yield_delta_list, planned_yield_list, ideal_yield_list = [],[],[],[]
    for block in serial_numbers:
        A22 = A38 = float(df1.loc[block, "X"])
        A23 = A37 = float(df1.loc[block, "Y"])
        A24 = A39 = float(df1.loc[block, "Z"])
        A8 = float(PRSB_df.loc["Brick Size, X (width)", each_type])
        A10 = float(PRSB_df.loc["Brick Size, Y (length)", each_type])
        A11 = float(PRSB_df.loc["Brick Size, Z (thickness)", each_type])
        A12 = float(PRSB_df.loc["# of gems in a brick", each_type])
        A13 = float(PRSB_df.loc["Gem Volume", each_type])
        A14 = float(PRSB_df.loc["Inter-brick gap (overlap), x (width)", each_type])
        A15 = float(PRSB_df.loc["Inter-brick gap, y (length)", each_type])
        A16 = float(PRSB_df.loc["Inter-layer gap, z (thickness)", each_type])
        A17 = float(PRSB_df.loc["Brick Volume", each_type])
        A18 = float(PRSB_df.loc["Brick Yield", each_type].strip('%'))/100
        A25 = A40 = A22*A23*A24
        A26 = int((A22+A14)/(A8+A14))
        A27 = int((A23+A15)/(A10+A15))
        A28 =  1 if int((A24+A16)/(A11+A16)) > 1 else int((A24+A16)/(A11+A16))
        A29 = A26*A27*A28*A12
        A30 = A29*A13
        A31 = np.nan if A25 == 0 else A30/A25
        A32 = A29*A13/((A26*A8+(A26-1)*A14)*(A27*A10+(A27-1)*A15)*(A28*A11+(A28-1)
                *A16)) if A30 > 0 else np.nan
        A33 = A32-A31 if A30 > 0 else np.nan
        A41 = int((A37+A14)/(A8+A14))
        A42 = int((A38+A15)/(A10+A15))
        A43 =  1 if int((A39+A16)/(A11+A16)) > 1 else int((A39+A16)/(A11+A16))
        A44 = A41*A42*A43*A12
        A45 = A44*A13
        A46 = np.nan if A40 == 0 else A45/A40
        A47 = A44*A13/((A41*A8+(A41-1)*A14)*(A42*A10+(A42-1)*A15)*(A43*A11+(A43-1)
            *A16)) if A45 > 0 else np.nan
        A48 = A47-A46 if A45 > 0 else np.nan

        if A33 is np.nan:
            if A48 is np.nan:
                A52 = np.nan
            else:
                A52 = 2
        else:
            if A48 is np.nan:
                A52 = 1
            else:
                A52 = 2 if A33>A48 else 1

        if A52 == 1:
            ideal_yield = A32
            planned_yield = A31
            yield_delta = A33
            num_gems = A29
        else:
            ideal_yield = A47 if A52 == 2 else np.nan
            planned_yield = A46 if A52 == 2 else np.nan
            yield_delta = A48 if A52 == 2 else np.nan
            num_gems = A44 if A52 == 2 else np.nan  

        num_list.append(num_gems)
        ideal_yield_list.append(ideal_yield)
        planned_yield_list.append(planned_yield)
        yield_delta_list.append(yield_delta)

    df1[f"Num {each_type}"] = num_list
    df1[f"Ideal Yield {each_type}"] = ideal_yield_list
    df1[f"Planned Yield {each_type}"] = planned_yield_list
    df1[f"Yield Delta {each_type}"] = yield_delta_list


# These two will be lists of dictionaries, one for each type of stone
# Each dictionary will match the block id to its yield and num data

yield_list = []
num_list = []

# These 4 lists hold yield, number, weight, value data
yield_complete = []
num_complete = []
weight_complete = []
value_complete = []

for each_type in types:
    # If N/A, fill the number of gems produced as 0, and the yield delta as 100%
    # so they are never picked by the algorithm
    df1[f'Num {each_type}'] = df1[f'Num {each_type}'].fillna(0)
    df1[f'Planned Yield {each_type}'] = df1[f'Planned Yield {each_type}'].fillna(0)
    df1[f'Ideal Yield {each_type}'] = df1[f'Ideal Yield {each_type}'].fillna(0)
    df1[f'Yield Delta {each_type}'] = df1[f'Yield Delta {each_type}'].fillna(100)


# Work out value of each stone, based on the maximum relative value possibly 
# achievable (Principle of maximum utility)
value_list = []
for block in serial_numbers:
    value_array = np.array([df1.loc[block, "Num "+str(each_type)] *
                           rel_values_dict[each_type] for each_type in types])
    max_value = np.nanmax(value_array)
    value_list.append(float(max_value))

# If a block cannot be cut into any type of gem, then set its value to be 
# arbitrarily high so it will never be picked
clean_value_list = [9999 if x == 0 else x for x in value_list]

# For each type of block i.e. BG 0.4
for each_type in types:
    # Construct lists to hold the yield delta, number of gems, weight,
    # and value data
    yield_list.append(dict(zip(serial_numbers,df1[f'Yield Delta {each_type}'])))
    num_list.append(dict(zip(serial_numbers,df1[f'Num {each_type}'])))
    yield_complete += list(df1[f'Yield Delta {each_type}'])
    num_complete += list(df1[f'Num {each_type}'])
    weight_complete += list(df1["Carats"])
    value_complete += clean_value_list

# labels variable holds header names for the dispatches
labels = ["Serial Number", "Yield Delta", "Carat Weight", "Value", "No. of Gems"]
# shorter_labels variable holds header names for the residual blocks
shorter_labels = ["Serial Number", "Carat Weight", "Value", "Block Information"] \
                 + [f"Planned Yield {each_type}" for each_type in types]


# If the Yield Filter is on, we have to find all blocks whose planned yields are 
# too high, and remove them from the serial_numbers list. To do this, initialize
# a new list of "good_serial_numbers", which is equal to serial_numbers if the 
# Yield Filter is not on
good_serial_numbers = []
if int(filter_toggle) == 1:
    for block in serial_numbers:
        filter_list = [df1.loc[block, f"Planned Yield {each_type}"] \
                       > filter_dict[each_type] for each_type in types]
        passes_filter = any(filter_list)
        if passes_filter:
            good_serial_numbers.append(block)
else:
    good_serial_numbers = serial_numbers


# This dictionary stores additional information about each block for 
# post-optimization analysis. To understand why a certain block wasn't chosen
# for the dispatch, consult the following options:
#
# 1) A dimension was missing in the data entry
# 2) The weight of the block was missing in the data entry
# 3) The dimensions of the block were such that no gems could be cut out of it
#    (generally the block is too thin in this case)
# 4) The yields of the block are simply too low, there is no point wasting value
#    of the block on this process, even if it could be used to produce gems.
# 5) This block doesn't perform well enough compared to the blocks chosen for the
#    dispath. If the optimization is done on Yield, this option implies its yield
#    delta was higher than the other blocks chosen for the yield dispatch.


info_dict = {}
for block in serial_numbers:
    block_yield_list = [df1.loc[block, f"Planned Yield {each_type}"] 
                        for each_type in types]
    best_planned_yield = max(block_yield_list)
    max_index = block_yield_list.index(best_planned_yield)
    if df1.loc[block, "X"] == 0 or df1.loc[block, "Y"] == 0 or \
       df1.loc[block, "Z"] == 0:
        info_dict[block] = "Dimension missing"
    elif df1.loc[block, "Carats"] == 0:
        info_dict[block] = "Weight missing"
    elif best_planned_yield == 0:
        info_dict[block] = "Size too small to cut out gems"
    elif block not in good_serial_numbers:
        info_dict[block] = "Filtered out"
    else:
        info_dict[block] = "Leftover"

def optimize(choice):
    """Initalize and Solve Binary Integer Programming

    Initialise indicator variables that will be used in our BIP problem
    If variable 10509_0 is set to value 1, then 10509 will be used for the first
    type of gem.

    Similarly, if 56935_2 is set to value 1, then 56935 will be used for the 
    third type of gem. 

    Each block can only be used for one type of gem
    """
    indicators_list = []
    good_indicators_list = []
    for i in range(num_types):
        # "No" is an arbitrary string that we know will not appear in any serial
        # number, and simply acts as a separator between the serial number, and
        # its indicator suffix
        indicator_helper = [f"{block}No{str(i)}" for block in serial_numbers]
        good_indicator_helper = [f"{block}No{str(i)}"
                                 for block in good_serial_numbers]
        indicators_list += indicator_helper
        good_indicators_list += good_indicator_helper
    yield_dict = dict(zip(indicators_list, yield_complete))
    num_dict = dict(zip(indicators_list, num_complete))
    weight_dict = dict(zip(indicators_list, weight_complete))
    value_dict = dict(zip(indicators_list, value_complete))


    # Set up the Integer linear program
    prob = LpProblem("Inventory Problem",LpMinimize)

    # Establish dictionary between indicators and their LP variable equivalents
    block_vars = {i: LpVariable(name=f"{i}", cat = "Binary") 
                  for i in good_indicators_list}


    if choice == 0:
        # This is the objective function for minimising total yield delta
        prob += lpSum([yield_dict[i]*block_vars[i] for i in good_indicators_list])
    elif choice == 1:
        # This is the objective function for minimising total carat input
        prob += lpSum([weight_dict[i]*block_vars[i] for i in good_indicators_list])
    elif choice == 2:
        prob += lpSum([value_dict[i]*block_vars[i] for i in good_indicators_list])
    
    # Put all conditions for our linear program below

    # Make sure each indicator is set to 0,1
    for any_id in good_serial_numbers:
        prob += (lpSum([block_vars[str(any_id)+"No"+str(num_type)] 
                 for num_type in range(num_types)]) <= 1)

    # Make sure the forecast is met
    for each_type in types:
        prob += (lpSum([num_list[types.index(each_type)][i]*block_vars[str(i)
                 +"No"+ str(types.index(each_type))] for i in good_serial_numbers])
                 >= forecast_dict[each_type])


    # Solves the integer linear programming problem
    status = prob.solve()   
    status = prob.status

    
    #Returns the results of the L.P. algorithm in an Excel spreadsheet
    chosen_blocks = []
    for var in block_vars.values():
        if var.value() == 1:
            print(f"{var.name}: {var.value()}")
            chosen_blocks.append(var.name)

    dataframe_list = [pd.DataFrame(columns = labels) for _ in range(num_types)]

    # The chosen_blocks list contains variables that look like 10357No4. 
    # This extracts the serial number and stores it in clean_chosen_blocks
    clean_chosen_blocks = []
    for name in chosen_blocks:
        name_components = name.split("No")
        box = int(name_components[1])
        clean_name = name_components[0]
        clean_chosen_blocks.append(clean_name)
        dataframe_list[box] = dataframe_list[box].append({labels[0]:clean_name,
                    labels[1]:yield_dict[name], labels[2]:weight_dict[name], 
                    labels[3]:value_dict[name], labels[4]:num_dict[name]}, 
                    ignore_index=True)
    
    for df in dataframe_list:
        # Sort the dataframe such that the yield dispatch starts with the block
        # with the best yield
        df.sort_values(by=[labels[choice+1]], inplace=True)

    for df in dataframe_list:
        # Format certain columns of the dataframe
        df.iloc[:, 1] = df.iloc[:,1].apply(percentage)
        df.iloc[:, 3] = df.iloc[:,3].apply(one_dp)

    #Creates a special dataframe with different headers for residual block data
    residual_df = pd.DataFrame(columns = shorter_labels)
    clean_residual_blocks = [block for block in serial_numbers if str(block) 
                             not in clean_chosen_blocks]
    for name in clean_residual_blocks:
        name_long = f"{name}No0"
        residual_dict = dict(zip(shorter_labels, [name, weight_dict[name_long], 
                                 value_dict[name_long], info_dict[name]] 
                                 + [df1.loc[name, f"Planned Yield {each_type}"] 
                                 for each_type in types]))
        residual_df = residual_df.append(residual_dict, ignore_index=True)
        residual_df["Value"] = residual_df["Value"].apply(one_dp)
        for counter in range(num_types):
            residual_df.iloc[:,4 + counter] = \
            residual_df.iloc[:,4 + counter].apply(percentage)
    dataframe_list.append(residual_df)
    return dataframe_list, prob.status


# Writes the dataframes generated above into a temporary Excel file.

output_file_name = get_output_name()
with xlsxwriter.Workbook(output_file_name) as workbook:
    percentage_format = workbook.add_format({'num_format': '0.0%'})
    one_dp_format = workbook.add_format({'num_format': '0.0'})
    bold = workbook.add_format({'bold': True})
    italic = workbook.add_format({'italic': True})
    summary_sheet = workbook.add_worksheet("Dashboard")
    yield_sheet = workbook.add_worksheet("Yield")
    weight_sheet = workbook.add_worksheet("Weight")
    value_sheet = workbook.add_worksheet("Value")
    sheets = [yield_sheet, weight_sheet, value_sheet]
    remaining_gems = [[] for _ in range(3)]
    sums_averages = [[] for _ in range(3)]

    for sheet in sheets:
        # Writes the dispatch information in each of the three triage sheets
        starting_column = 0
        yield_sum = 0
        weight_sum = 0
        value_sum = 0
        dataframes, status = optimize(sheets.index(sheet))
        length_of_data = len(labels)
        for index in range(num_types):
            sums = list(np.sum(dataframes[index][labels[2:]], axis=0))
            try:
                numeric_yields = dataframes[index][labels[1]].apply(lambda x: \
                    float(x.strip("%"))/100)
                yield_average = percentage(float(np.average(numeric_yields, 
                                                            axis=0)))
            except:
                yield_average = 0
            sums = [yield_average] + sums
            num_sum = sums[3] - forecast_dict[types[index]]
            remaining_gems[sheets.index(sheet)].append(num_sum)
            yield_sum += float(sums[0].strip("%"))/100
            weight_sum += sums[1]
            value_sum += sums[2]
            sheet.write(0, starting_column, types[index], bold)
            sheet.write_row(0,starting_column + 1, ["Yield Average", "Carat Total",
                                                    "Value Total", "Gem Total"], 
                                                    italic)
            sheet.write_row(1,starting_column + 1, sums)
            sheet.write_row(2,starting_column,labels, italic)
            value_list = dataframes[index].values.tolist()
            for each_block in value_list:
                sheet.write_row(value_list.index(each_block)+3,starting_column,
                                each_block)
            sheet.set_column(starting_column+1,starting_column+1,None, 
                             percentage_format)
            sheet.set_column(starting_column+3,starting_column+3,None, 
                             one_dp_format)
            sheet.write(0, starting_column+5, "Forecast", bold)
            sheet.write(1, starting_column+5, forecast_dict[types[index]])
            sheet.write(2, starting_column+5, "Relative Value", bold)
            sheet.write(3, starting_column+5, rel_values_dict[types[index]])
            sheet.write(4, starting_column+5, "Planned Yield Filter", bold)
            sheet.write(5, starting_column+5, filter_dict[types[index]])
            starting_column += length_of_data + 2

        # Write the Residual column information.
        sums = list(np.sum(dataframes[-1][shorter_labels[1:3]], axis=0))
        sheet.write(0,starting_column,"Residual Blocks", bold)
        sheet.write_row(0,starting_column + 1, ["Carat Total", "Value Total"], 
                        italic)
        sheet.write_row(1,starting_column + 1, sums)
        sheet.write_row(2,starting_column,shorter_labels, italic)
        values_list = dataframes[-1].values.tolist()
        for each_block in values_list:
            sheet.write_row(values_list.index(each_block)+3,starting_column,
                            each_block)
        sheet.set_column(starting_column+2,starting_column+2,None, one_dp_format)
        sheet.set_column(starting_column+4, starting_column+4+num_types, None,
                         percentage_format)
        yield_average = percentage(yield_sum/num_types)
        
        sums_averages[sheets.index(sheet)] = [yield_average, weight_sum, 
                                              value_sum, sums[0], sums[1]]

    # Writes the summary statistics on the Dashboard
    summary_sheet.write(0,0, status_dict[status], bold)
    summary_sheet.write(1,2,"Dispatch", bold)
    summary_sheet.write(0,3,"Summary Statistics", bold)
    summary_sheet.write(4,2,"Residual", bold)
    summary_sheet.write(1,3,"Yield Delta Average", italic)
    summary_sheet.write(2,3,"Weight Sum", italic)
    summary_sheet.write(3,3,"Value Sum", italic)
    summary_sheet.write(4,3,"Weight Sum", italic)
    summary_sheet.write(5,3,"Value Sum", italic)
    optimizations = ["Yield Triage", "Weight Triage", "Value Triage"]
    for i in range(3):
        summary_sheet.write(0, i+4, optimizations[i], italic)
        summary_sheet.write(1, i+4, sums_averages[i][0], percentage_format)
        summary_sheet.write_column(2, i+4, sums_averages[i][1:], one_dp_format)

    # This writes the Extra gem information on the Dashboard
    summary_sheet.write(2,8,"Extra Gems", bold)
    summary_sheet.write(3,8,"Yield", italic)
    summary_sheet.write(4,8,"Weight", italic)
    summary_sheet.write(5,8,"Value", italic)
    summary_sheet.write_row(1,8,["Forecast"] + [forecast_dict[each_type] 
                                                for each_type in types])
    for each_type in types:
        summary_sheet.write(0, types.index(each_type)+9, each_type, italic)
        summary_sheet.write(3, types.index(each_type)+9, 
                            remaining_gems[0][types.index(each_type)])
        summary_sheet.write(4, types.index(each_type)+9, 
                            remaining_gems[1][types.index(each_type)])
        summary_sheet.write(5, types.index(each_type)+9, 
                            remaining_gems[2][types.index(each_type)])

# Reads the Excel sheet into a dataframe and writes this dataframe into the 
# Google Sheet
list_of_dfs = [pd.read_excel(output_file_name, sheet_name, header=None, 
                             engine='openpyxl') for sheet_name in range(4)]
clean_list_of_dfs = [df.fillna('') for df in list_of_dfs]
write_sheet(input_file, clean_list_of_dfs)
print("Finished. Google Sheet has been updated")
# Removes the Excel file from the system
try:
    os.remove(output_file_name)
except:
    pass
input("Press enter to exit program:")