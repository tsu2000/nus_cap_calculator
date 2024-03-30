import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
import plotly.graph_objects as go
import plotly.io as pio

import xlsxwriter
import base64
import io
import requests
import datetime

from collections import Counter
from PIL import Image
from streamlit_extras.badges import badge


@st.cache_resource
def get_initial_data(rel_years):
    # Obtaining up-to-date data for application
    api_url = f'https://api.nusmods.com/v2/{rel_years}/moduleInfo.json'
    data = requests.get(api_url).json()

    unique_mcs = sorted(list(set([float(module['moduleCredit']) for module in data if float(module['moduleCredit']) > 0])))
    
    return data, unique_mcs 


def main():
    col1, col2, col3 = st.columns([0.034, 0.265, 0.035])
    
    with col1:
        url = 'https://github.com/tsu2000/nus_cap_calculator/raw/main/images/nus.png'
        response = requests.get(url)
        img = Image.open(io.BytesIO(response.content))
        st.image(img, output_format = 'png')

    with col2:
        st.title('&nbsp; NUS Module CAP Calculator')

    with col3:
        badge(type = 'github', name = 'tsu2000/nus_cap_calculator', url = 'https://github.com/tsu2000/nus_cap_calculator')

    # Obtain relevant years for modules
    now = datetime.datetime.now()

    current_year = int(now.strftime('%Y'))
    current_mth_day = now.strftime('%m-%d')

    if current_mth_day < '08-06':
        options = [f'AY {yr-1}/{yr}' for yr in np.arange(2019, current_year+1)]

    elif current_mth_day >= '08-06':
        options = [f'AY {yr}/{yr+1}' for yr in np.arange(2018, current_year+1)]

    # Create sidebar with options
    with st.sidebar:  
        st.markdown('# :twisted_rightwards_arrows: &nbsp; Navigation Bar :round_pushpin:')
        st.markdown('####')

        opt = st.selectbox('Select an Academic Year (AY):', options, index = len(options)-1)

        year_1, year_2 = opt[3:7], opt[8:]
        mod_years = f'{year_1}-{year_2}'

        feature = st.radio('Select a feature:', ['Current CAP Analysis', 
                                                 'Future CAP Calculation', 
                                                 'CAP Sensitivity', 
                                                 'CAP Calculation Explanation'])   

        st.write('#')
        st.write('##')
        st.write('##')

        st.markdown('---')     

        col_a, col_b = st.columns([1.3, 0.9])

        with col_a:
            st.markdown('This app is powered by:')
        with col_b:
            url2 = 'https://github.com/tsu2000/nus_cap_calculator/raw/main/images/nusmods_banner.png'
            response = requests.get(url2)
            img = Image.open(io.BytesIO(response.content))
            st.image(img, use_column_width = True, output_format = 'png')

    # Select option
    if feature == 'Current CAP Analysis':
        calc(data = get_initial_data(mod_years)[0],
             yr_1 = year_1, 
             yr_2 = year_2, 
             now = now,
             mod_years = mod_years,
             all_acad_years = options)
        
    elif feature == 'Future CAP Calculation':
        future(unique_mcs = get_initial_data(mod_years)[1])
        
    elif feature == 'CAP Sensitivity':
        sense(unique_mcs = get_initial_data(mod_years)[1])
        
    elif feature == 'CAP Calculation Explanation':
        explain()
    
    
def calc(data, yr_1, yr_2, now, mod_years, all_acad_years):
    st.markdown('#### :bar_chart: &nbsp; Current CAP Analysis')

    st.markdown('This feature allows users to select modules as listed in NUSMods for a selected Academic Year (AY) to calculate their CAP and provides a brief analysis on the modules taken. It also allows users to download their analysis as a PDF file and selected module data to an Excel file. &nbsp; _**(View data source: [NUSMods API](https://api.nusmods.com/v2/))**_')

    st.markdown('---')

    if 'all_module_data' not in st.session_state:
        st.session_state['all_module_data'] = []

    if 'upload_status' not in st.session_state:
        st.session_state['upload_status'] = False

    grades_to_cap = {'A+': 5.0,
                     'A': 5.0,
                     'A-': 4.5, 
                     'B+': 4.0, 
                     'B': 3.5, 
                     'B-': 3.0, 
                     'C+': 2.5, 
                     'C': 2.0, 
                     'D+': 1.5, 
                     'D': 1.0, 
                     'F': 0.0, 
                     'S': None, 
                     'U': None,
                     'CS': None,
                     'CU': None,
                     'EXE': None,
                     'IC': None,
                     'IP': None,
                     'W': None}

    mc_dict = {module['moduleCode']: [module['title'], float(module['moduleCredit'])] for module in data}

    selected_mod = st.selectbox(f'Select a module you have taken from the list - (For AY {yr_1}/{yr_2}):', 
                                mc_dict,
                                format_func = lambda key: key + f' - {str(mc_dict[key][0])} [{str(mc_dict[key][1])} MCs]')

    selected_grade = st.selectbox('Select grade you have obtained for the respective module:', grades_to_cap)

    final_mod_years = mod_years[:4] + '/' + mod_years[5:]

    def results(mod_code, grade):
        mod_title = mc_dict[mod_code][0]
        selected_mcs = mc_dict[mod_code][1]
        selected_score = grades_to_cap[grade]

        return [mod_code, mod_title, selected_mcs, grade, selected_score]

    amb_col, rmb_col, clear_col = st.columns([1, 4.2, 0.8]) 

    with amb_col:
        amb = st.button('Add Module')
        if amb:
            st.session_state.all_module_data.append(results(selected_mod, selected_grade) + [final_mod_years])

    with rmb_col:
        rmb = st.button(u'\u21ba')
        if rmb and st.session_state['all_module_data'] != []:
            st.session_state.all_module_data.remove(st.session_state.all_module_data[-1])

    with clear_col:
        clear = st.button('Clear All')
        if clear:
            st.session_state['all_module_data'] = []

    # Functionality to add mdoules to existing spreadsheet
    upload_xlsx = st.file_uploader('Or, upload an existing .xlsx file with recorded modules in the same format:')

    if upload_xlsx is not None and st.session_state['upload_status'] == False:
        df_upload = pd.read_excel(upload_xlsx)
        for row in range(len(df_upload)):
            st.session_state.all_module_data.append([i for i in df_upload.iloc[row]])
        st.session_state['upload_status'] = True

    elif upload_xlsx is None:
        st.session_state['upload_status'] = False

    df = pd.DataFrame(columns = ['Module Code', 'Module Title', 'No. of MCs', 'Grade', 'Grade Points', 'AY Taken'],
                      data = st.session_state['all_module_data'])
    
    # Change column categories
    df['Grade'] = df['Grade'].astype('category')
    df['Grade'] = pd.Categorical(df['Grade'], categories = list(grades_to_cap.keys()))

    all_AY = [yr[3:] for yr in all_acad_years]

    df['AY Taken'] = df['AY Taken'].astype('category')
    df['AY Taken'] = pd.Categorical(df['AY Taken'], categories = all_AY)

    # Show up-to-date dataframe
    st.markdown('###### Add a module and grade to view and download the data table:')

    # Display module data in DataFrame
    if st.session_state['all_module_data'] != []:
        st.dataframe(df.style.format(precision = 1),
                     hide_index = True,
                     use_container_width = True)
        
    analysis_col, export_col = st.columns([1, 0.265]) 

    with export_col:
        def to_excel(df):
            output = io.BytesIO()
            writer = pd.ExcelWriter(output, engine = 'xlsxwriter')

            df.to_excel(writer, sheet_name = 'nus_mods', index = False)
            workbook = writer.book
            worksheet = writer.sheets['nus_mods']

            # Add formats and templates here        
            font_color = '#000000'
            header_color = '#ffff00'

            string_template = workbook.add_format(
                {
                    'font_color': font_color, 
                }
            )

            grade_template = workbook.add_format(
                {
                    'font_color': font_color, 
                    'align': 'center',
                    'bold': True
                }
            )

            ay_template = workbook.add_format(
                {
                    'font_color': font_color, 
                    'align': 'right'
                }
            )

            float_template = workbook.add_format(
                {
                    'num_format': '0.0',
                    'font_color': font_color, 
                }
            )

            header_template = workbook.add_format(
                {
                    'bg_color': header_color, 
                    'border': 1
                }
            )

            column_formats = {
                'A': [string_template, 15],
                'B': [string_template, 50],
                'C': [float_template, 15],
                'D': [grade_template, 15],
                'E': [float_template, 15],
                'F': [ay_template, 15]
            }

            for column in column_formats.keys():
                worksheet.set_column(f'{column}:{column}', column_formats[column][1], column_formats[column][0])
                worksheet.conditional_format(f'{column}1:{column}1', {'type': 'no_errors', 'format': header_template})

            # Automatically apply Filter function on shape of dataframe
            worksheet.autofilter(0, 0, df.shape[0], df.shape[1]-1)

            # Saving and returning data
            writer.close()
            processed_data = output.getvalue()

            return processed_data

        def get_table_download_link(df):
            """Generates a link allowing the data in a given Pandas DataFrame to be downloaded
            in:  dataframe
            out: href string
            """
            val = to_excel(df)
            b64 = base64.b64encode(val)

            return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="mod_cap_details.xlsx">:inbox_tray: Download (.xlsx)</a>' 

        if st.session_state['all_module_data'] != []:
            st.markdown(get_table_download_link(df), unsafe_allow_html = True)

    with analysis_col:
        if st.session_state['all_module_data'] != []:
            analysis = st.button('View Analysis')
        else:
            analysis = None

    if analysis and st.session_state['all_module_data'] != []:

        df2 = df.dropna()
        cap = sum(df2['No. of MCs'] * df2['Grade Points']) / sum(df2['No. of MCs'])
        total_mcs_cap = sum(df2['No. of MCs'])

        final_cap = round(cap, 2)
        dp4_cap = round(cap, 4)

        # Degree classification
        if final_cap >= 4.50:
            degree_class = 'Honours (Highest Distinction)'
        elif final_cap >= 4.00:
            degree_class = 'Honours (Distinction)'
        elif final_cap >= 3.50:
            degree_class = 'Honours (Merit)'            
        elif final_cap >= 3.00:
            degree_class = 'Honours'        
        elif final_cap >= 2.00:
            degree_class = 'Pass'
        else:
            degree_class = 'Below requirements for graduation'

        mcs_not_counted = df.loc[(df['Grade'] == 'U') | (df['Grade'] == 'CU') | (df['Grade'] == 'EXE') | (df['Grade'] == 'IC') | (df['Grade'] == 'IP') | (df['Grade'] == 'W')]

        total_completed_mcs = sum(df['No. of MCs']) - sum(mcs_not_counted['No. of MCs'])

        # Cumulative modules
        complete_total_mods = len(df)
        conv_mods = len(df2)
        sued_mods = len(df.loc[(df['Grade'] == 'U') | (df['Grade'] == 'S')])
        cscu_mods = len(df.loc[(df['Grade'] == 'CU') | (df['Grade'] == 'CS')])
        unrq_mods = len(df.loc[(df['Grade'] == 'EXE') | (df['Grade'] == 'IC') | (df['Grade'] == 'IP') | (df['Grade'] == 'W')])

        table_dict = {'Final CAP': final_cap,
                      'Degree Classification': degree_class,
                      'Your CAP (To 4 d.p.)': dp4_cap,
                      'No. of MCs used to calculate CAP': total_mcs_cap,
                      'Total No. of MCs completed successfully': total_completed_mcs,
                      'Total No. of modules attempted (A + B + C + D)': complete_total_mods,
                      'No. of modules accounted for in CAP (A)': conv_mods,
                      'No. of modules which were S/Ued (B)': sued_mods,
                      'No. of CS/CU modules taken (C)': cscu_mods,
                      "No. of modules with a 'EXE', 'IC', 'IP' or 'W' grade (D)": unrq_mods,
                      'Date of Overview': now.strftime('%d %b %Y')}

        col_fill_colors = ['azure']*2 + ['lavender']*3 + ['cornsilk']*5 + ['honeydew']
        font_colors = ['mediumblue']*2 + ['indigo']*3 + ['saddlebrown']*5 + ['darkgreen']

        fig = go.Figure(data = [go.Table(columnwidth = [2.5, 1.5],
                                    header = dict(values = ['<b>Module Overview & Detailed Analysis<b>', 
                                                            '<b>Result<b>'],
                                                fill_color = 'lightskyblue',
                                                line_color = 'black',
                                                align = 'center',
                                                font = dict(color = 'black', 
                                                            size = 14,
                                                            family = 'Georgia')),
                                    cells = dict(values = [list(table_dict.keys()),
                                                        list(table_dict.values())], 
                                                fill_color = [col_fill_colors, col_fill_colors],
                                                line_color = 'black',
                                                align = ['right', 'left'],
                                                font = dict(color = [font_colors, font_colors], 
                                                            size = [14, 14],
                                                            family = ['Georgia', 'Georgia Bold']),
                                                height = 25))])

        fig.update_layout(height = 318, width = 700, margin = dict(l = 5, r = 5, t = 5, b = 5))
        st.plotly_chart(fig, use_container_width = True)

        # Create an in-memory buffer
        buffer = io.BytesIO()

        # Save the figure as a pdf to the buffer
        fig.write_image(file = buffer, scale = 6, format = 'pdf')

        # Download the pdf from the buffer
        st.download_button(
            label = 'Download Analysis as PDF',
            data = buffer,
            file_name = 'cap_overview.pdf',
            mime = 'application/octet-stream',
            help = 'Downloads the module analysis as a PDF File'
        )

    st.markdown('---')
                       
            
def future(unique_mcs):
    st.markdown('#### :question: &nbsp; Future CAP Calculation')

    st.markdown('This feature lets users to calculate calculate their future CAP will change from their current CAP (if any) through input of additional dummy modules with their respective grade points and module credits.')
        
    cap_col, mc_col = st.columns([1, 1]) 
    
    with cap_col:
        current_cap = st.number_input('Current CAP (If any):', min_value = 0.00, max_value = 5.00, value = 0.00, step = 0.01)
        
    with mc_col:
        current_mcs = st.number_input('Number of MCs used to calculate current CAP (If any):', min_value = 0.0, max_value = 500.0, value = 0.0, step = 0.5)
    
    st.markdown('---')    
    st.markdown('##### Select additional modules with their respective grades and MCs:')

    st.markdown('This dataframe is interactive! Click the bottom bar to add modules and select individual rows on the leftmost bar and press the delete or backspace button on your keyboard to delete a module.')

    valid_grades_to_cap = {'A+/A': 5.0,
                           'A-': 4.5, 
                           'B+': 4.0, 
                           'B': 3.5, 
                           'B-': 3.0, 
                           'C+': 2.5, 
                           'C': 2.0, 
                           'D+': 1.5, 
                           'D': 1.0, 
                           'F': 0.0,
                           'S/U': None}
    
    data = {'Module Name': ['Sample Module 1', 'Sample Module 2', 'Sample Module 3', 'Sample Module 4', 'Sample Module 5'],
            'Module Credits': [4, 4, 4, 4, 4],
            'Module Grade': ['A+/A', 'A-', 'B+', 'B', 'C+']}
    
    df = pd.DataFrame(data)

    # Adjust column data types
    df['Module Credits'] = df['Module Credits'].astype(float)
    df['Module Grade'] = df['Module Grade'].astype('category')
    df['Module Grade'] = df['Module Grade'].cat.add_categories(['B-', 'C', 'D+', 'D', 'F', 'S/U'])

    annotated = st.data_editor(df, 
                               column_config = {'Module Name': st.column_config.TextColumn(default = 'Another Sample Module', disabled = True),
                                                'Module Credits': st.column_config.NumberColumn(default = 4.0, min_value = 0.5, max_value = 100, step = 0.5),
                                                'Module Grade': st.column_config.SelectboxColumn(default = 'B+')}, 
                               num_rows = 'dynamic', 
                               use_container_width = False)
    
    col_i, col_ii = st.columns([1, 2])

    with col_i:
        st.markdown(f"No. of Modules Added: **{len(annotated)}**")
    
    with col_ii:
        st.markdown(f"No. of Module Credits Added: **{annotated['Module Credits'].sum()}**")

    button = st.button('Calculate New CAP')

    # Button to calculate new CAP
    if button and not annotated.empty:
        annotated['cap_score'] = annotated['Module Grade'].map(valid_grades_to_cap)
        annotated['weighted_cap'] = annotated['Module Credits'] * annotated['cap_score']

        new_cap = (current_cap * current_mcs + annotated['weighted_cap'].sum()) / (current_mcs + annotated['Module Credits'].sum())
        new_mcs = current_mcs + annotated['Module Credits'].sum()

        fig = go.Figure(data = [go.Table(columnwidth = [2.5, 1.5],
                            header = dict(values = ['<b>New CAP Stats<b>', 
                                                    '<b>Result<b>'],
                                        fill_color = 'lightcoral',
                                        line_color = 'black',
                                        align = 'center',
                                        font = dict(color = 'black', 
                                                    size = 14,
                                                    family = 'Georgia')),
                            cells = dict(values = [['New CAP after computation',
                                                    'New CAP (To 4 d.p.)',
                                                    'MCs used to calculate new CAP'],
                                                    [round(new_cap, 2),
                                                        round(new_cap, 4),
                                                        round(new_mcs, 2)]], 
                                        fill_color = 'wheat',
                                        line_color = 'black',
                                        align = ['left', 'center'],
                                        font = dict(color = 'black', 
                                                    size = [14, 14],
                                                    family = ['Georgia', 'Georgia Bold']),
                                        height = 25))])
        
        fig.update_layout(height = 170, width = 200, margin = dict(l = 5, r = 5, t = 5, b = 5))
        st.plotly_chart(fig, use_container_width = True)
           
            
def sense(unique_mcs):
    st.markdown('#### :thermometer: &nbsp; CAP Sensitivity')
    
    st.markdown("This feature aims to answer the question: **How much can my CAP change with the addition of a single module?** Users can input their current CAP and MCs to view the sensitivity of their CAP.")

    cap_col, mc_col = st.columns([1, 1]) 
    
    with cap_col:
        current_cap = st.number_input('Current CAP:', min_value = 0.00, max_value = 5.00, value = 3.50, step = 0.01)
        
    with mc_col:
        total_mcs = st.number_input('Number of MCs used to calculate current CAP:', min_value = 0.0, max_value = 160.0, value = 20.0, step = 0.5)
        
    valid_grades_to_cap = {'A+/A': 5.0,
                           'A-': 4.5, 
                           'B+': 4.0, 
                           'B': 3.5, 
                           'B-': 3.0, 
                           'C+': 2.5, 
                           'C': 2.0, 
                           'D+': 1.5, 
                           'D': 1.0, 
                           'F': 0.0}
    
    def mod_array_single(mcs):
        return np.array([current_cap * total_mcs + valid_grades_to_cap[key] * mcs for key in valid_grades_to_cap]) / (total_mcs + mcs)

    df_mod = {f'+{num} MC Mod': mod_array_single(num) for num in unique_mcs}
    
    # DataFrame for new CAP
    cap_1_more_mod_df = pd.DataFrame(df_mod, index = valid_grades_to_cap.keys()).T

    cap_1_melted_df = cap_1_more_mod_df.reset_index().rename(columns = {'index': 'Module Credits'})
    cap_1_melted_df = cap_1_melted_df.melt('Module Credits', var_name = 'Grade', value_name = 'New CAP')
    
    # DataFrame for change in CAP
    cap_change_df = cap_1_more_mod_df - current_cap

    cap_cmelted_df = cap_change_df.reset_index().rename(columns = {'index': 'Module Credits'})
    cap_cmelted_df = cap_cmelted_df.melt('Module Credits', var_name = 'Grade', value_name = 'Δin CAP')

    # Return Altair Heatmap
    def future_plotting(cap_type, chart_scheme, df_type):

        # Order chart
        grade_order = df_type['Grade'].unique().tolist()
        mod_order = df_type['Module Credits'].unique().tolist()

        # Define base chart
        base_chart = alt.Chart(df_type).encode(
            x = alt.X('Grade',
                      sort = grade_order,
                      axis = alt.Axis(orient = 'top')),
            y = alt.Y('Module Credits',
                      sort = mod_order)
        ).properties(
            title = f'{cap_type}' + str(round(current_cap, 2)) + ' at ' + str(total_mcs) + ' MCs after addition of a single module',
            width = 700,
            height = 800
        )

        # Define heatmap layer
        if chart_scheme == 'red_to_green':
            used_scheme = alt.Scale(domain = (df_type.iloc[:,2].min(),
                                              0,
                                              df_type.iloc[:,2].max()),
                                              range = ['red', 'black', 'green'])
        
        if chart_scheme == 'grayscale':
            used_scheme = alt.Scale(domain = (df_type.iloc[:,2].min(),
                                              current_cap,
                                              df_type.iloc[:,2].max()),
                                              range = ['grey', 'gainsboro', 'white'])

        heatmap = base_chart.mark_rect().encode(
            color = alt.Color(df_type.columns[2],
                              scale = used_scheme
            )
        )

        # Define text layer
        if chart_scheme == 'red_to_green':
            text_gradient = alt.Scale(domain = (df_type.iloc[:,2].min(), df_type.iloc[:,2].max()),
                                      range = ['seashell', 'honeydew'])

        elif chart_scheme == 'grayscale':
            text_gradient = alt.Scale(domain = (df_type.iloc[:,2].min(),
                                                current_cap,
                                                df_type.iloc[:,2].max()),
                                      range = ['maroon', 'black', 'green'])

        text = base_chart.mark_text(baseline = 'middle').encode(
            text = alt.Text(df_type.columns[2] + ':Q', format = ',.2f'),
            color = alt.Color(df_type.columns[2],
                              scale = text_gradient,
                              legend = None)
            #color = alt.condition(alt.datum[df_type.columns[2]] < 0, alt.value('#dddddd'), alt.value('#222222'))
        )

        # Setting up final object
        final = (heatmap + text).configure_axisX(
            labelAngle = 0
            ).configure_title(
                fontSize = 15,
                offset = 15).configure_legend(
                   labelLimit = 10
                ).resolve_scale(
                    color = 'independent'
                )

        return st.altair_chart(final, use_container_width = True)

    # Switch between 2 different heatmaps
    plottype = st.radio('Choose visualisation type:', ['Show change in CAP', 'Show new CAP'])

    if plottype == 'Show change in CAP':
        future_plotting('Change in CAP of ', 'red_to_green', cap_cmelted_df)    

    elif plottype == 'Show new CAP':
        future_plotting('New CAP with intial CAP of ', 'grayscale', cap_1_melted_df)

    st.markdown('---')
        
        
def explain():
    st.markdown('#### :bulb: &nbsp; CAP Calculation Explanation')

    st.markdown('This feature describes how Cumulative Average Point (CAP) at NUS is calculated in detail.')

    st.markdown('---')
    
    st.markdown('To calculate the CAP for $n$ number of modules:')
    st.write('&nbsp;')
    
    st.markdown(r'''$G = \text{Module Grade Points}$''')
    st.markdown(r'''$G_n = \text{Specific Module Grade Points for the } n^\text{th} \text{ module used in CAP calculation}$''')
    st.markdown(r'''$MC = \text{Module Credits}$''')
    st.markdown(r'''$MC_n = \text{Specific Module Credits for the } n^\text{th} \text{ module used in CAP calculation}$''')
    
    st.write('&nbsp;')
    
    st.latex(r'''\text{CAP} = \frac{G_1\times{MC_1} + G_2\times{MC_2} + ... + G_n\times{MC_n}}{MC_1 + MC_2 + ... + MC_n}''')
   
    st.latex(r'''= \sum\limits_{i=1}^{n} \frac{{G_i}\times{MC_i}}{MC_i}''')
    
    st.markdown('&nbsp;')
    
    st.markdown('Each module taken at NUS is usually graded on a modular basis, meaning that each module has a fixed number of Module Credits (or MCs), and that each letter grade given after the completion of a module corresponds to a specific number of grade points. To get your Cumulative Average Points or CAP, simply do the following:')
                
    st.markdown("1. Obtain the grade points for the module by converting your grade given to the grade points allocated. (E.g. 'A+/A' is 5 grade points, 'B' is 3.5 grade points etc.)")          
    st.markdown('2. Multiply the grade points you have obtained for each module by the number of module credits assigned to it.')
    st.markdown('3. Repeat steps 1 and 2 for all relevant modules.*')
    st.markdown('4. Sum the results of step 3 to get the numerator of the CAP equation.')
    st.markdown('5. Finally, divide the result of step 4 by the total number of module credits (denominator of CAP equation) used to calculate the numerator to get your CAP.')
    
    st.markdown('**(*) Important Note**: _Modules which are graded on a CS/CU may or have MCs assigned to them. While some of these modules may be essential degree requirements, they are not factored into the calculation of CAP **at all**. Likewise, modules which have 0 MCs but are essential degree requirements are also not factored into the calculation of CAP. Lastly, other grades not in the range of A+ to F (such as W for Withdrawn, IC for Incomplete, modules which have been S/Ued etc.) also do not factor into the calculation of CAP._')
    
    st.markdown('---')
    
    st.markdown('Click the link below to obtain more information about how CAP is calculated at NUS and the relevant grade points for each grade:')
    st.markdown("[**NUS Registrar's Office - Modular System**](https://www.nus.edu.sg/registrar/academic-information-policies/non-graduating/modular-system)")
    
    
if __name__ == "__main__":
    st.set_page_config(page_title = 'NUS Module CAP Calculator', page_icon = '📝')
    main()
    
