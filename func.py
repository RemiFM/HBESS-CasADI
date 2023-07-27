import altair as alt

color_range = ["#0072BD", "#D95319", "#EDB120"]

def get_SOC(P, E, dt):
    # P     [W]
    # E     [kWh]
    # dt    [s]
    dSOC = P*(dt)/(E*3.6e6)
    return dSOC

def plot_power(df_load):
    # Scale inputs
    chart_data = df_load.copy()                                  #copy of DataFrame for scaling
    chart_data.loc[:, 't'] = chart_data.loc[:, 't'] / 60            #seconds to hours
    chart_data.loc[:, 'P'] = chart_data.loc[:, 'P'] / 1000          #watts to kilowatts

    # Restructure DataFrame
    chart_data = (chart_data
                  .loc[:, ['t', 'P']]
                  .rename(columns = {'P':'Total power demand'})
                  .melt('t'))

    # Create chart object
    chart = (
        alt.Chart(data = chart_data)
        .mark_line(interpolate='linear')
        .encode(
        x = alt.X('t', axis = alt.Axis(title = 'Time (min)', grid = True)),
        y = alt.Y('value', axis = alt.Axis(title = 'Power (kW)')),
        color = alt.Color('variable', sort = ['Total power demand'], scale=alt.Scale(range=color_range[0:1]), legend = alt.Legend(orient = 'bottom', title = 'None', titleOpacity = 0, titlePadding = 0, titleFontSize = 0)) 
        )
        .properties(
            height = 380,
        )
        .interactive()
    )
    return chart

def plot_powers(df_loads):
    # Scale inputs
    chart_data = df_loads.copy()                                  #copy of DataFrame for scaling
    chart_data.loc[:, 't'] = chart_data.loc[:, 't'] / 60            #seconds to hours
    chart_data.loc[:, 'P'] = chart_data.loc[:, 'P'] / 1000          #watts to kilowatts
    chart_data.loc[:, 'P_HE'] = chart_data.loc[:, 'P_HE'] / 1000          #watts to kilowatts
    chart_data.loc[:, 'P_HP'] = chart_data.loc[:, 'P_HP'] / 1000          #watts to kilowatts

    # Restructure DataFrame
    chart_data = (chart_data
                  .loc[:, ['t', 'P', 'P_HE', 'P_HP']]
                  .rename(columns = {'P':'Total power demand', 'P_HE':'Power from HE', 'P_HP':'Power from HP'})
                  .melt('t'))

    # Create chart object
    chart = (
        alt.Chart(data = chart_data)
        .mark_line(interpolate='linear')
        .encode(
        x = alt.X('t', axis = alt.Axis(title = 'Time (min)', grid = True)),
        y = alt.Y('value', axis = alt.Axis(title = 'Power (kW)')),
        color = alt.Color('variable', sort = ['Total power demand'], scale=alt.Scale(range=color_range), legend = alt.Legend(orient = 'bottom', title = 'None', titleOpacity = 0, titlePadding = 0, titleFontSize = 0)) 
        )
        .properties(
            height = 380,
        )
        .interactive()
    )
    return chart

def plot_SOC(df_SOC):
    # Scale inputs
    chart_data = df_SOC.copy()                                  #copy of DataFrame for scaling
    chart_data.loc[:, 't'] = chart_data.loc[:, 't'] / 60            #seconds to hours
    chart_data.loc[:, 'SOC_HE'] = chart_data.loc[:, 'SOC_HE'] * 100  
    chart_data.loc[:, 'SOC_HP'] = chart_data.loc[:, 'SOC_HP'] * 100 

    # Restructure DataFrame
    chart_data = (chart_data
                  .loc[:, ['t', 'SOC_HE', 'SOC_HP']]
                  .melt('t'))

    # Create chart object
    chart = (
        alt.Chart(data = chart_data)
        .mark_line(interpolate='linear')
        .encode(
        x = alt.X('t', axis = alt.Axis(title = 'Time (min)', grid = True)),
        y = alt.Y('value', axis = alt.Axis(title = 'SOC (%)'), scale=alt.Scale(domain=[0, 100])),
        color = alt.Color('variable', sort = ['SOC_HE'], scale=alt.Scale(range=color_range[1:3]), legend = alt.Legend(orient = 'bottom', title = 'None', titleOpacity = 0, titlePadding = 0, titleFontSize = 0)) 
        )
        .properties(
            height = 380,
        )
        .interactive()
    )
    return chart

def plot_currents(df_current):
    # Scale inputs
    chart_data = df_current.copy()                                  #copy of DataFrame for scaling
    chart_data.loc[:, 't'] = chart_data.loc[:, 't'] / 60            #seconds to hours

    # Restructure DataFrame
    chart_data = (chart_data
                  .loc[:, ['t', 'I_HE', 'I_HP']]
                  .melt('t'))

    # Create chart object
    chart = (
        alt.Chart(data = chart_data)
        .mark_line(interpolate='linear')
        .encode(
        x = alt.X('t', axis = alt.Axis(title = 'Time (min)', grid = True)),
        y = alt.Y('value', axis = alt.Axis(title = 'Current (A)')),
        color = alt.Color('variable', sort = ['I_HE'], scale=alt.Scale(range=color_range[1:3]), legend = alt.Legend(orient = 'bottom', title = 'None', titleOpacity = 0, titlePadding = 0, titleFontSize = 0)) 
        )
        .properties(
            height = 380,
        )
        .interactive()
    )
    return chart



def display_pack(df_pack):
    styler = df_pack.style
    styler.set_table_styles([
        {
            'selector': 'th',
            'props': [
                ('text-align', 'left'),
                ('font-weight', 'bold'),
                ('color', '#5F565E'),
                ('background-color', '#F0F2F6'),
                ('height', '26px')
            ]
        },
        {
            'selector': 'td',
            'props':[
                ('height', '26px')
            ]
        },
        {
            'selector': 'tbody tr:hover',
            'props': [('background-color', '#95C11E')]
        }
    ])
    
    return styler