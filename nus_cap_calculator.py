import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.io as pio

import xlsxwriter
import base64
import io
import requests
import datetime

from collections import Counter


@st.experimental_singleton
def get_initial_data():
    # Obtaining up-to-date data for application
    now = datetime.datetime.now()

    current_yr = int(now.strftime('%Y'))
    current_mth_day = now.strftime('%m-%d')

    if current_mth_day < "08-06":
        yr_1, yr_2 = current_yr - 1, current_yr

    elif current_mth_day >= "08-06":
        yr_1, yr_2 = current_yr, current_yr + 1

    api_url = f'https://api.nusmods.com/v2/{yr_1}-{yr_2}/moduleInfo.json'
    data = requests.get(api_url).json()

    unique_mcs = sorted(list(set([float(module['moduleCredit']) for module in data if float(module['moduleCredit']) > 0])))
    
    return data, unique_mcs, yr_1, yr_2, now


def main():
    st.title('NUS Module CAP Calculator')
    
    with st.sidebar:   
        st.header(':twisted_rightwards_arrows: &nbsp; Navigation Bar')
        feature = st.radio('Select a feature:', ['Current CAP Analysis', 
                                                 'Future CAP Calculation', 
                                                 'CAP Sensitivity', 
                                                 'CAP Calculation Explanation'])                            
        st.markdown('***')
        st.header(':male-technologist: &nbsp; View Source Code &nbsp; :female-technologist:')
        st.components.v1.html("""<a href="https://github.com/tsu2000/nus_cap_calculator" target="_blank"><img src="https://img.shields.io/static/v1?label=tsu2000&message=nus_cap_calculator
    &color=blue&logo=github" alt="_blank"></a><a href="https://github.com/tsu2000/nus_cap_calculator" target="_blank"><img src="https://img.shields.io/github/stars/tsu2000/nus_cap_calculator?style=social" alt="tsu2000 - NUS Module CAP Calculator"></a>""", 
                        height = 28)                                                  
    
    # Select option
    if feature == 'Current CAP Analysis':
        calc(data = get_initial_data()[0], yr_1 = get_initial_data()[2], yr_2 = get_initial_data()[3], now = get_initial_data()[4])
        
    elif feature == 'Future CAP Calculation':
        future(unique_mcs = get_initial_data()[1])
        
    elif feature == 'CAP Sensitivity':
        sense(unique_mcs = get_initial_data()[1])
        
    elif feature == 'CAP Calculation Explanation':
        explain()
    
    
def calc(data, yr_1, yr_2, now):
    st.markdown('#### :bar_chart: &nbsp; Current CAP Analysis')

    st.markdown('This feature allows users to select modules as listed in NUSMods for the current Academic Year (AY) to calculate their CAP and provides a brief analysis on the modules taken. It also allows users to download their selected module data to an Excel file. &nbsp; _**(View data source: [NUSMods API](https://api.nusmods.com/v2/))**_')

    st.markdown('---')

    if 'all_module_data' not in st.session_state:
        st.session_state['all_module_data'] = []

    if 'mod_list' not in st.session_state:
        st.session_state['mod_list'] = []

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

    selected_mod = st.selectbox(f'Select a module you have taken from the list: - (Current AY: {yr_1}/{yr_2})', 
                                mc_dict,
                                format_func = lambda key: key + f' - {str(mc_dict[key][0])} [{str(mc_dict[key][1])} MCs]')

    selected_grade = st.selectbox('Select grade you have obtained for the respective module:', grades_to_cap)

    def results(mod_code, grade):
        mod_title = mc_dict[mod_code][0]
        selected_mcs = mc_dict[mod_code][1]
        selected_score = grades_to_cap[grade]

        return [mod_code, mod_title, selected_mcs, grade, selected_score]

    amb_col, rmb_col, clear_col = st.columns([1, 4.2, 0.8]) 

    with amb_col:
        amb = st.button('Add Module')
        if amb: #and selected_mod not in st.session_state.mod_list:
            st.session_state.all_module_data.append(results(selected_mod, selected_grade))

    with rmb_col:
        rmb = st.button(u'\u21ba')
        if rmb and st.session_state['all_module_data'] != []:
            st.session_state.all_module_data.remove(st.session_state.all_module_data[-1])

    with clear_col:
        clear = st.button('Clear All')
        if clear:
            st.session_state['all_module_data'] = []


    st.session_state.mod_list = [st.session_state['all_module_data'][x][0] for x in range(0, len(st.session_state['all_module_data']))]
  

    df = pd.DataFrame(columns = ['Module Code', 'Module Title', 'No. of MCs', 'Grade', 'Grade Points'],
                      data = st.session_state['all_module_data'])

    st.markdown('###### Add a module and grade to view and download the data table:')
    if st.session_state['all_module_data'] != []:
        st.dataframe(df.style.format(precision = 1))

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

            c_string_template = workbook.add_format(
                {
                    'font_color': font_color, 
                    'align': 'center'
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
                'A': [string_template, 12.5],
                'B': [string_template, 60],
                'C': [float_template, 12.5],
                'D': [c_string_template, 12.5],
                'E': [float_template, 12.5]
            }

            for column in column_formats.keys():
                worksheet.set_column(f'{column}:{column}', column_formats[column][1], column_formats[column][0])
                worksheet.conditional_format(f'{column}1:{column}1', {'type': 'no_errors', 'format': header_template})

            # Saving and returning data
            writer.save()
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

        total_mcs = sum(df['No. of MCs'])
        total_mcs_cap = sum(df2['No. of MCs'])

        # Cumulative modules
        complete_total_mods = len(df)
        conv_mods = len(df2)
        sued_mods = len(df.loc[(df['Grade'] == 'U') | (df['Grade'] == 'S')])
        cscu_mods = len(df.loc[(df['Grade'] == 'CU') | (df['Grade'] == 'CS')])
        zero_mods = len(df.loc[df['No. of MCs'] == 0])
        weird_mods = len(df.loc[(df['Grade'] == 'EXE') | (df['Grade'] == 'IC') | (df['Grade'] == 'IP') | (df['Grade'] == 'W')])

        table_dict = {'Final CAP': final_cap,
                        'Degree Classification': degree_class,
                        'Your CAP (To 4 d.p.)': dp4_cap,
                        'Total No. of MCs used to calculate CAP': total_mcs_cap,
                        'Total No. of MCs attempted': total_mcs,
                        'Total No. of modules attempted': complete_total_mods,
                        'No. of modules accounted for in CAP': conv_mods,
                        'No. of modules which were S/Ued': sued_mods,
                        'No. of CS/CU modules taken': cscu_mods,
                        "No. of modules with a 'EXE', 'IC', 'IP' or 'W' grade": weird_mods,
                        'Date of Overview': now.strftime('%Y-%m-%d')}

        col_fill_colors = ['lightcyan']*2 + ['white']*8 + ['gainsboro']
        font_colors = ['crimson']*2 + ['black']*8 + ['darkgreen']

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

        fig.update_layout(height = 325, width = 700, margin = dict(l = 5, r = 5, t = 5, b = 5))
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

    st.markdown('This feature allows users to calculate how their current CAP will change with the addition of new modules with different grades and module credits.')
    
    if 'predicted_mod' not in st.session_state:
        st.session_state['predicted_mod'] = []
        
    if 'new_grade_count' not in st.session_state:
        st.session_state['new_grade_count'] = []  
        
    if 'new_mc_count' not in st.session_state:
        st.session_state['new_mc_count'] = []
        
    cap_col, mc_col = st.columns([1, 1]) 
    
    with cap_col:
        current_cap = st.number_input('Current CAP:', min_value = 0.00, max_value = 5.00, value = 3.50, step = 0.01)
        
    with mc_col:
        total_mcs = st.number_input('Number of MCs used to calculate current CAP:', min_value = 0.0, max_value = 160.0, value = 20.0, step = 0.5)
    
    st.markdown('---')    
    st.markdown('##### Select additional modules with their respective grades:')
    
    add_mod_grade_col, add_mod_mc_col = st.columns([1, 1])
    
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
    
    with add_mod_grade_col:
        additional_mod_grade = st.selectbox('Choose additional Module Grade:', valid_grades_to_cap.keys(), index = 3)

    with add_mod_mc_col:
        additional_mod_mcs = st.selectbox('Choose additional Module Credits:', unique_mcs, index = 6)
            
    grade_w_mcs = f'Module w Grade: {additional_mod_grade} | MC: {additional_mod_mcs}'
        
    amb2_col, rmb2_col, clear2_col = st.columns([1, 4.2, 0.8]) 

    with amb2_col:
        amb2 = st.button('Add Module')
        if amb2:
            st.session_state['predicted_mod'].append(grade_w_mcs)
            st.session_state['new_grade_count'].append(additional_mod_grade)
            st.session_state['new_mc_count'].append(additional_mod_mcs)

    with rmb2_col:
        rmb2 = st.button(u'\u21ba')
        if rmb2 and st.session_state['predicted_mod'] != []:
            st.session_state['predicted_mod'].remove(st.session_state['predicted_mod'][-1])
            st.session_state['new_grade_count'].remove(st.session_state['new_grade_count'][-1])
            st.session_state['new_mc_count'].remove(st.session_state['new_mc_count'][-1])

    with clear2_col:
        clear2 = st.button('Clear All')
        if clear2:
            st.session_state['predicted_mod'] = []
            st.session_state['new_grade_count'] = []
            st.session_state['new_mc_count'] = []
            
    df = pd.DataFrame(columns = ['Count'],
                      index = Counter(st.session_state['predicted_mod']).keys(),
                      data = Counter(st.session_state['predicted_mod']).values())
    
    df_col, stats_col = st.columns([1, 1]) 
    
    with df_col:
        st.markdown('###### Table of Modules with respective grades and MCs:')
        if st.session_state['predicted_mod'] != []:
            st.dataframe(df)
        
    with stats_col:
        st.markdown(f"No. of Module Credits Added: &emsp; &emsp; &emsp; **{sum(st.session_state['new_mc_count'])}**")
 
        if st.button('Compute new CAP'):
            grade2pt_arr = np.array([valid_grades_to_cap[key] for key in st.session_state['new_grade_count']])
            new_mcs_arr = np.array(st.session_state['new_mc_count'])
            
            new_cap = ((current_cap * total_mcs) + sum(grade2pt_arr * new_mcs_arr)) / (total_mcs + sum(new_mcs_arr))
            new_mcs = total_mcs + sum(new_mcs_arr)
            
            st.markdown(f'New CAP after computation: &emsp; &emsp; &emsp; &emsp; &emsp; &nbsp; **{round(new_cap, 2)}**')
            st.markdown(f'MCs used to calculate new CAP: &emsp; &emsp; &emsp; **{round(new_mcs, 2)}**')
           
            
def sense(unique_mcs):
    st.markdown('#### :thermometer: &nbsp; CAP Sensitivity')
    
    st.markdown("This feature aims to provide an overview on how much your CAP changes by upon the addition of a single module with differing grades and module credits, from the stated current CAP and module credits.")

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
    
    # DataFrame for change in CAP
    cap_change_df = cap_1_more_mod_df - current_cap
    
    def future_plotting(cap_type, chart_type, df_type):
    
        fig, ax = plt.subplots(figsize = (12, 12), dpi = 100)

        sns.heatmap(df_type, annot = True, fmt = '.3f', linewidth = 0.25, cmap = f'{chart_type}') 
        ax.xaxis.tick_top()

        plt.title(f'{cap_type}' + r'$\bf{' + str(round(current_cap, 2)) + '}$' + ' at ' + r'$\bf{' + str(total_mcs) + '}$' + ' MCs after addition of a single module', y = 1.035)

        return st.pyplot(fig)

    plottype = st.radio('Choose visualisation type:', ['Show new CAP', 'Show change in CAP'])
    
    if plottype == 'Show new CAP':
        future_plotting('New CAP with intial CAP of ', 'gray', cap_1_more_mod_df)
        
    elif plottype == 'Show change in CAP':
        future_plotting('Change in CAP of ', 'RdBu', cap_change_df)
    
    st.markdown('---')
        
        
def explain():
    st.markdown('#### :bulb: &nbsp; CAP Calculation Explanation')

    st.markdown('This feature describes how Cumulative Average Point (CAP) at NUS is calculated in detail.')

    st.markdown('---')
    
    st.markdown('###### To calculate the CAP for $n$ number of modules:')
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
    main()
