import casadi       as ca
import scipy       # Optimization toolbox
import streamlit    as st       # Web app toolbox
import pandas       as pd       # DataFrame manipulation
import numpy        as np       # List manipulation
from scipy.interpolate import interp1d
from scipy.integrate import cumtrapz
import math
import func

opti = ca.Opti() #Casadi helper classes

bool_discrete = False
bool_monotype = False

# Web page layout
st.set_page_config(layout="wide")
st.markdown("""
        <style>
               .block-container {
                    padding-top: 3rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)
#st.header("Discrete HBESS Sizing using CasADi optimization:zap:")
layout = st.columns([3, 5], gap="large")
layout_left = layout[0].columns(2, gap="large")
tabs = layout[1].tabs(["Primary Load Profile", "Secondary Load Profile"])
layout_right_primary = tabs[0].columns(2, gap="large")
layout_right_secondary = tabs[1].columns(2, gap="large")
layout_left[0].write("**High Energy Cell**")
layout_left[1].write("**High Power Cell**")
placeholder_right_primary = layout_right_primary[0].empty()
placeholder_right_secondary = layout_right_secondary[0].empty()

# User inputs - High Energy Battery
Q_cell_HE = layout_left[0].number_input("Rated capacity (Ah)", value=50)        # Ah 94
V_cell_HE = layout_left[0].number_input("Nominal voltage (V)", value=3.67, disabled=True)      # V
I_cell_HE = layout_left[0].number_input("Maximum current (A)", value=50)       # A 150
C_cell_HE = layout_left[0].number_input("Cost (€)", value=27)                   # € 62
E_cell_HE = (Q_cell_HE/1000) * V_cell_HE                                        # kWh
OCV_HE = [3.427, 3.508, 3.588, 3.621, 3.647, 3.684, 3.761, 3.829, 3.917, 4.019, 4.135]
OCV_SOC_HE = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1];


# User inputs - High Power Battery
Q_cell_HP = layout_left[1].number_input('Rated capacity (Ah)', value=23)        # Ah
V_cell_HP = layout_left[1].number_input('Nominal voltage (V)', value=2.3, disabled=True)       # V
I_cell_HP = layout_left[1].number_input('Maximum current (A)', value=92)        # A
C_cell_HP = layout_left[1].number_input('Cost (€)', value=20)                   # € 38
E_cell_HP = (Q_cell_HP/1000) * V_cell_HP                                        # kWh 
OCV_HP = [2.067, 2.113, 2.151, 2.183, 2.217, 2.265, 2.326, 2.361, 2.427, 2.516, 2.653]
OCV_SOC_HP = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
V_pack = layout[0].slider('Nominal Pack Voltage _(V)_', min_value=0, max_value=2000 ,value=1000)
layout_left = layout[0].columns(2, gap="large")
#bool_voltage = layout_left[0].checkbox('Manually set Pack Voltage')
bool_voltage = True
bool_neg = layout_left[0].checkbox('Allow packs to charge each other')
bool_monotype = layout_left[0].checkbox('Also calculate monotypes', help='Increases calculation time!')
bool_discrete = layout_left[0].checkbox('Discrete solution', help='Increases calculation time!')
#bool_OCV = layout_left[0].checkbox('Constant pack voltage')
bool_OCV = False
run = layout_left[1].button('Run CasADi optimization')
#V_pack = layout_left[1].number_input('Nominal Pack Voltage (V)', value=600, disabled= not bool_voltage)
#V_pack = V_pack if bool_voltage else 0;

#layout[0].divider()

# User inputs - Primary Load Profile
df_load_primary = pd.read_csv("tug_boat_1.csv")
df_load_primary.rename(columns={'time (s)': 't', 'power (W)': 'P'}, inplace=True)
t_primary       = df_load_primary['t'].values
P_primary       = df_load_primary['P'].values
N_primary       = t_primary.shape[0]
figure = func.plot_power(df_load_primary)
placeholder_right_primary.altair_chart(figure, use_container_width=True)

# User inputs - Secondary Load Profile
df_load_secondary = pd.read_csv("tug_boat_2.csv")   # W vs s
df_load_secondary.rename(columns={'time (s)': 't', 'power (W)': 'P'}, inplace=True)
t_secondary       = df_load_secondary['t'].values
P_secondary       = df_load_secondary['P'].values
N_secondary       = t_secondary.shape[0]
figure = func.plot_power(df_load_secondary)
placeholder_right_secondary.altair_chart(figure, use_container_width=True)

#########################################################################################
if run:
    with st.spinner('Calculating...'):
        # Define the decision variables
        P_HE_1 = opti.variable(N_primary, 1)
        P_HE_2 = opti.variable(N_secondary, 1)
        SERIES_HE = opti.variable(1, 1)
        PARALLEL_HE = opti.variable(1, 1)
        SOC_HE_1 = opti.variable(N_primary+1, 1)
        I_HE_1 = opti.variable(N_primary, 1)
        SOC_HE_2 = opti.variable(N_secondary+1, 1)
        I_HE_2 = opti.variable(N_secondary, 1)

        P_HP_1 = opti.variable(N_primary, 1)
        P_HP_2 = opti.variable(N_secondary, 1)
        SERIES_HP = opti.variable(1, 1)
        PARALLEL_HP = opti.variable(1, 1)
        SOC_HP_1 = opti.variable(N_primary+1, 1)
        I_HP_1 = opti.variable(N_primary, 1)
        SOC_HP_2 = opti.variable(N_secondary+1, 1)
        I_HP_2 = opti.variable(N_secondary, 1)

        # Define the objective function
        objective = C_cell_HE * SERIES_HE * PARALLEL_HE + C_cell_HP * SERIES_HP * PARALLEL_HP   # Total cost of the battery system (eur)

        # Define the constraints
        opti.subject_to(P_HE_1 + P_HP_1 == P_primary)
        opti.subject_to(P_HE_2 + P_HP_2 == P_secondary)

        if bool_voltage:
            opti.subject_to(SERIES_HE == round(V_pack / V_cell_HE))
            opti.subject_to(SERIES_HP == round(V_pack / V_cell_HP))

        opti.subject_to(SERIES_HE >= 0)
        opti.subject_to(PARALLEL_HE >= 0)
        #opti.subject_to(ca.remainder(SERIES_HE, 1) == 0)
        #opti.subject_to(ca.remainder(PARALLEL_HE, 1) == 0)
        if not bool_neg:
            opti.subject_to(P_HP_1 >= 0)
            opti.subject_to(P_HP_2 >= 0)
            opti.subject_to(P_HE_1 >= 0)
            opti.subject_to(P_HE_2 >= 0)

        opti.subject_to(SERIES_HP >= 0)
        opti.subject_to(PARALLEL_HP >= 0)
        #opti.subject_to(ca.remainder(SERIES_HP, 1) == 0)
        #opti.subject_to(ca.remainder(PARALLEL_HP, 1) == 0)
        

        # Define the SOC related parameters
        t_SOC_1 = df_load_primary['t'].tolist()
        t_SOC_1.append(t_SOC_1[-1] + (t_SOC_1[-1] - t_SOC_1[-2]))
        SOC_HE_1[0]=ca.DM(0.9)
        SOC_HP_1[0]=ca.DM(0.9)

        for i in range(0, N_primary):
                E_HE = SERIES_HE * PARALLEL_HE * E_cell_HE
                E_HP = SERIES_HP * PARALLEL_HP * E_cell_HP
                opti.subject_to(SOC_HE_1[i+1] == SOC_HE_1[i] - func.get_SOC(P_HE_1[i], E_HE,t_SOC_1[i+1] - t_SOC_1[i]))
                opti.subject_to(SOC_HP_1[i+1] == SOC_HP_1[i] - func.get_SOC(P_HP_1[i], E_HP,t_SOC_1[i+1] - t_SOC_1[i]))

        opti.subject_to(opti.bounded(0.1, SOC_HE_1, 0.9))
        opti.subject_to(opti.bounded(0.1, SOC_HP_1, 0.9))

        t_SOC_2 = df_load_secondary['t'].tolist()
        t_SOC_2.append(t_SOC_2[-1] + (t_SOC_2[-1] - t_SOC_2[-2]))
        SOC_HE_2[0]=ca.DM(0.9)
        SOC_HP_2[0]=ca.DM(0.9)

        for i in range(0, N_secondary):
                E_HE = SERIES_HE * PARALLEL_HE * E_cell_HE
                E_HP = SERIES_HP * PARALLEL_HP * E_cell_HP
                opti.subject_to(SOC_HE_2[i+1] == SOC_HE_2[i] - func.get_SOC(P_HE_2[i], E_HE,t_SOC_2[i+1] - t_SOC_2[i]))
                opti.subject_to(SOC_HP_2[i+1] == SOC_HP_2[i] - func.get_SOC(P_HP_2[i], E_HP,t_SOC_2[i+1] - t_SOC_2[i]))

        opti.subject_to(opti.bounded(0.1, SOC_HE_2, 0.9))
        opti.subject_to(opti.bounded(0.1, SOC_HP_2, 0.9))

        # Define the voltage and current related parameters
        SOC_TO_OCV_HE = ca.interpolant('LUT','bspline',[OCV_SOC_HE], OCV_HE)
        SOC_TO_OCV_HP = ca.interpolant('LUT','bspline',[OCV_SOC_HP], OCV_HP)

        for i in range(0, N_primary):
                if not bool_OCV:
                    V_HE = (SERIES_HE * SOC_TO_OCV_HE(SOC_HE_1[i]))
                    V_HP = (SERIES_HP * SOC_TO_OCV_HP(SOC_HP_1[i]))
                else:
                    V_HE = SERIES_HE * V_cell_HE
                    V_HP = SERIES_HE * V_cell_HP
                opti.subject_to(I_HE_1[i] == P_HE_1[i] / V_HE)
                opti.subject_to(I_HP_1[i] == P_HP_1[i] / V_HP)

        opti.subject_to(I_HE_1 <= (PARALLEL_HE * I_cell_HE))
        opti.subject_to(I_HP_1 <= (PARALLEL_HP * I_cell_HP))

        for i in range(0, N_secondary):
                if not bool_OCV:
                    V_HE = (SERIES_HE * SOC_TO_OCV_HE(SOC_HE_2[i]))
                    V_HP = (SERIES_HP * SOC_TO_OCV_HP(SOC_HP_2[i]))
                else:
                    V_HE = SERIES_HE * V_cell_HE
                    V_HP = SERIES_HE * V_cell_HP
                     
                opti.subject_to(I_HE_2[i] == P_HE_2[i] / V_HE)
                opti.subject_to(I_HP_2[i] == P_HP_2[i] / V_HP)

        opti.subject_to(I_HE_2 <= (PARALLEL_HE * I_cell_HE))
        opti.subject_to(I_HP_2 <= (PARALLEL_HP * I_cell_HP))

        # Set initial values
        if bool_voltage:
            opti.set_initial(SERIES_HE, round(V_pack / V_cell_HE))  # Set initial value of E_HE
            opti.set_initial(SERIES_HP, round(V_pack / V_cell_HP))  # Set initial value of E_HE
            
        else:
            opti.set_initial(SERIES_HE, 1)  # Set initial value of E_HE
            opti.set_initial(SERIES_HP, 1)  # Set initial value of E_HE
        opti.set_initial(PARALLEL_HE, 16)
        opti.set_initial(PARALLEL_HP, 25)

        # Define the solver and solve the problem
        opti.minimize(objective)
        options = {"ipopt": {"print_level": 5}}
        opti.solver('ipopt', options)
        sol = opti.solve()

        ###########################################

    layout[0].subheader(f"Optimal total cost: :green[**{'€ {:,.2f}'.format(sol.value(objective))} €**]")
    layout_left = layout[0].columns(2, gap="large")

    pack_HE = { 'parameter': ['series', 'parallel', 'total energy', 'nominal voltage', 'maximum current', 'rated current', 'total cost'],
                'value': [round(sol.value(SERIES_HE), 2), round(sol.value(PARALLEL_HE), 2), f'{round(sol.value(SERIES_HE)*sol.value(PARALLEL_HE)*E_cell_HE, 2)} kWh', f'{round(sol.value(SERIES_HE) * V_cell_HE, 2)} V',
                f'{round(max(max(sol.value(I_HE_1)), max(sol.value(I_HE_2))), 2)} A', f'{round(sol.value(PARALLEL_HE) * sol.value(I_cell_HE), 2)} A', f'{round(sol.value(SERIES_HE)*sol.value(PARALLEL_HE)*C_cell_HE, 2)} €']
    }

    pack_HP = { 'parameter': ['series', 'parallel', 'total energy', 'nominal voltage', 'maximum current', 'rated current', 'total cost'],
                'value': [round(sol.value(SERIES_HP), 2), round(sol.value(PARALLEL_HP), 2), f'{round(sol.value(SERIES_HP)*sol.value(PARALLEL_HP)*E_cell_HP, 2)} kWh', f'{round(sol.value(SERIES_HP) * V_cell_HP, 2)} V',
                f'{round(max(max(sol.value(I_HP_1)), max(sol.value(I_HP_2))), 2)} A', f'{round(sol.value(PARALLEL_HP) * sol.value(I_cell_HP), 2)} A', f'{round(sol.value(SERIES_HP)*sol.value(PARALLEL_HP)*C_cell_HP, 2)} €']
    }

    df_pack_HE = pd.DataFrame(pack_HE)
    df_pack_HP = pd.DataFrame(pack_HP)
    layout_left[0].table(func.display_pack(df_pack_HE))
    layout_left[1].table(func.display_pack(df_pack_HP))



    # Plot the power profiles
    placeholder_right_primary.empty()
    placeholder_right_secondary.empty()

    df_loads_primary = pd.DataFrame(dict(t = t_primary,
                            P = P_primary,
                            P_HE = sol.value(P_HE_1),
                            P_HP = sol.value(P_HP_1)))
    
    df_loads_secondary = pd.DataFrame(dict(t = t_secondary,
                            P = P_secondary,
                            P_HE = sol.value(P_HE_2),
                            P_HP = sol.value(P_HP_2)))

    figure = func.plot_powers(df_loads_primary)
    layout_right_primary[0].altair_chart(figure, use_container_width=True)
    figure = func.plot_powers(df_loads_secondary)
    layout_right_secondary[0].altair_chart(figure, use_container_width=True)

    # Plot the SOC
    df_SOC_1 = pd.DataFrame(dict(t = t_SOC_1,
                            SOC_HE = sol.value(SOC_HE_1),
                            SOC_HP = sol.value(SOC_HP_1),))
    
    df_SOC_2 = pd.DataFrame(dict(t = t_SOC_2,
                            SOC_HE = sol.value(SOC_HE_2),
                            SOC_HP = sol.value(SOC_HP_2),))

    figure = func.plot_SOC(df_SOC_1)
    layout_right_primary[1].altair_chart(figure, use_container_width=True)
    figure = func.plot_SOC(df_SOC_2)
    layout_right_secondary[1].altair_chart(figure, use_container_width=True)

    # Plot the current
    df_current_1 = pd.DataFrame(dict(t = t_primary,
                            I_HE = sol.value(I_HE_1),
                            I_HP = sol.value(I_HP_1)))
    
    df_current_2 = pd.DataFrame(dict(t = t_secondary,
                            I_HE = sol.value(I_HE_2),
                            I_HP = sol.value(I_HP_2)))

    figure = func.plot_currents(df_current_1)
    layout_right_primary[1].altair_chart(figure, use_container_width=True)
    figure = func.plot_currents(df_current_2)
    layout_right_secondary[1].altair_chart(figure, use_container_width=True)

    # Plot the voltage
    SOC_TO_OCV_HE = interp1d(OCV_SOC_HE, OCV_HE, kind='linear', fill_value='extrapolate')
    SOC_TO_OCV_HP = interp1d(OCV_SOC_HP, OCV_HP, kind='linear', fill_value='extrapolate')
    
    df_voltage_1 = df_SOC_1[['t']].copy()

    if not bool_OCV:
        df_voltage_1['V_HE'] = df_SOC_1['SOC_HE'].apply(lambda soc: SOC_TO_OCV_HE(soc))
        df_voltage_1['V_HP'] = df_SOC_1['SOC_HP'].apply(lambda soc: SOC_TO_OCV_HP(soc))
    else:
        df_voltage_1['V_HE'] = V_cell_HE
        df_voltage_1['V_HP'] = V_cell_HP

    df_voltage_1['V_HE'] *= round(sol.value(SERIES_HE))
    df_voltage_1['V_HP'] *= round(sol.value(SERIES_HP))

    df_voltage_2 = df_SOC_2[['t']].copy()

    if not bool_OCV:
        df_voltage_2['V_HE'] = df_SOC_2['SOC_HE'].apply(lambda soc: SOC_TO_OCV_HE(soc))
        df_voltage_2['V_HP'] = df_SOC_2['SOC_HP'].apply(lambda soc: SOC_TO_OCV_HP(soc))
    else:
        df_voltage_2['V_HE'] = V_cell_HE
        df_voltage_2['V_HP'] = V_cell_HP

    df_voltage_2['V_HE'] *= round(sol.value(SERIES_HE))
    df_voltage_2['V_HP'] *= round(sol.value(SERIES_HP))

    figure = func.plot_voltages(df_voltage_1)
    layout_right_primary[0].altair_chart(figure, use_container_width=True)
    figure = func.plot_voltages(df_voltage_2)
    layout_right_secondary[0].altair_chart(figure, use_container_width=True)





##MONOTYPE##################
    if bool_monotype:
        with st.spinner('Calculating...'):
            # Define the decision variables
            P_HE_1 = opti.variable(N_primary, 1)
            P_HE_2 = opti.variable(N_secondary, 1)
            SERIES_HE = opti.variable(1, 1)
            PARALLEL_HE = opti.variable(1, 1)
            SOC_HE_1 = opti.variable(N_primary+1, 1)
            I_HE_1 = opti.variable(N_primary, 1)
            SOC_HE_2 = opti.variable(N_secondary+1, 1)
            I_HE_2 = opti.variable(N_secondary, 1)

            # Define the objective function
            objective = C_cell_HE * SERIES_HE * PARALLEL_HE 
            # Define the constraints
            opti.subject_to(P_HE_1 == P_primary)
            opti.subject_to(P_HE_2 == P_secondary)
    
            if bool_voltage:
                opti.subject_to(SERIES_HE == round(V_pack / V_cell_HE))

            opti.subject_to(SERIES_HE >= 0)
            opti.subject_to(PARALLEL_HE >= 0)

            if not bool_neg:
                opti.subject_to(P_HE_1 >= 0)
                opti.subject_to(P_HE_2 >= 0)
          
            # Define the SOC related parameters
            t_SOC_1 = df_load_primary['t'].tolist()
            t_SOC_1.append(t_SOC_1[-1] + (t_SOC_1[-1] - t_SOC_1[-2]))
            SOC_HE_1[0]=ca.DM(0.9)

            for i in range(0, N_primary):
                    E_HE = SERIES_HE * PARALLEL_HE * E_cell_HE
                    opti.subject_to(SOC_HE_1[i+1] == SOC_HE_1[i] - func.get_SOC(P_HE_1[i], E_HE,t_SOC_1[i+1] - t_SOC_1[i]))

            opti.subject_to(opti.bounded(0.1, SOC_HE_1, 0.9))

            t_SOC_2 = df_load_secondary['t'].tolist()
            t_SOC_2.append(t_SOC_2[-1] + (t_SOC_2[-1] - t_SOC_2[-2]))
            SOC_HE_2[0]=ca.DM(0.9)

            for i in range(0, N_secondary):
                    E_HE = SERIES_HE * PARALLEL_HE * E_cell_HE
                    opti.subject_to(SOC_HE_2[i+1] == SOC_HE_2[i] - func.get_SOC(P_HE_2[i], E_HE,t_SOC_2[i+1] - t_SOC_2[i]))

            opti.subject_to(opti.bounded(0.1, SOC_HE_2, 0.9))

            # Define the voltage and current related parameters
            SOC_TO_OCV_HE = ca.interpolant('LUT','bspline',[OCV_SOC_HE], OCV_HE)

            for i in range(0, N_primary):
                    if not bool_OCV:
                        V_HE = (SERIES_HE * SOC_TO_OCV_HE(SOC_HE_1[i]))
                    else:
                        V_HE = SERIES_HE * V_cell_HE

                    opti.subject_to(I_HE_1[i] == P_HE_1[i] / V_HE)

            opti.subject_to(I_HE_1 <= (PARALLEL_HE * I_cell_HE))

            for i in range(0, N_secondary):
                    if not bool_OCV:
                        V_HE = (SERIES_HE * SOC_TO_OCV_HE(SOC_HE_2[i]))
                    else:
                        V_HE = SERIES_HE * V_cell_HE
                        
                    opti.subject_to(I_HE_2[i] == P_HE_2[i] / V_HE)

            opti.subject_to(I_HE_2 <= (PARALLEL_HE * I_cell_HE))

            # Set initial values
            if bool_voltage:
                opti.set_initial(SERIES_HE, round(V_pack / V_cell_HE))  # Set initial value of E_HE
                
            else:
                opti.set_initial(SERIES_HE, 1)  # Set initial value of E_HE
            opti.set_initial(PARALLEL_HE, 16)

            # Define the solver and solve the problem
            opti.minimize(objective)
            options = {"ipopt": {"print_level": 5}}
            opti.solver('ipopt', options)
            sol = opti.solve()

            ###########################################

        layout[0].subheader(f"Optimal total cost: :green[**{'€ {:,.2f}'.format(sol.value(objective))} €**]")
        layout_left = layout[0].columns(2, gap="large")

        pack_HE = { 'parameter': ['series', 'parallel', 'total energy', 'nominal voltage', 'maximum current', 'rated current', 'total cost'],
                    'value': [round(sol.value(SERIES_HE), 2), round(sol.value(PARALLEL_HE), 2), f'{round(sol.value(SERIES_HE)*sol.value(PARALLEL_HE)*E_cell_HE, 2)} kWh', f'{round(sol.value(SERIES_HE) * V_cell_HE, 2)} V',
                    f'{round(max(max(sol.value(I_HE_1)), max(sol.value(I_HE_2))), 2)} A', f'{round(sol.value(PARALLEL_HE) * sol.value(I_cell_HE), 2)} A', f'{round(sol.value(SERIES_HE)*sol.value(PARALLEL_HE)*C_cell_HE, 2)} €']
        }

        df_pack_HE = pd.DataFrame(pack_HE)
        layout_left[0].table(func.display_pack(df_pack_HE))



        # Plot the power profiles
        placeholder_right_primary.empty()
        placeholder_right_secondary.empty()

        df_loads_primary = pd.DataFrame(dict(t = t_primary,
                                P = P_primary,
                                P_HE = sol.value(P_HE_1),
                                P_HP = sol.value(P_HE_1)))
        
        df_loads_secondary = pd.DataFrame(dict(t = t_secondary,
                                P = P_secondary,
                                P_HE = sol.value(P_HE_2),
                                P_HP = sol.value(P_HE_2)))

        figure = func.plot_powers(df_loads_primary)
        layout_right_primary[0].altair_chart(figure, use_container_width=True)
        figure = func.plot_powers(df_loads_secondary)
        layout_right_secondary[0].altair_chart(figure, use_container_width=True)

        # Plot the SOC
        df_SOC_1 = pd.DataFrame(dict(t = t_SOC_1,
                                SOC_HE = sol.value(SOC_HE_1),
                                SOC_HP = sol.value(SOC_HE_1),))
        
        df_SOC_2 = pd.DataFrame(dict(t = t_SOC_2,
                                SOC_HE = sol.value(SOC_HE_2),
                                SOC_HP = sol.value(SOC_HE_2),))

        figure = func.plot_SOC(df_SOC_1)
        layout_right_primary[1].altair_chart(figure, use_container_width=True)
        figure = func.plot_SOC(df_SOC_2)
        layout_right_secondary[1].altair_chart(figure, use_container_width=True)

        # Plot the current
        df_current_1 = pd.DataFrame(dict(t = t_primary,
                                I_HE = sol.value(I_HE_1),
                                I_HP = sol.value(I_HE_1)))
        
        df_current_2 = pd.DataFrame(dict(t = t_secondary,
                                I_HE = sol.value(I_HE_2),
                                I_HP = sol.value(I_HE_2)))

        figure = func.plot_currents(df_current_1)
        layout_right_primary[1].altair_chart(figure, use_container_width=True)
        figure = func.plot_currents(df_current_2)
        layout_right_secondary[1].altair_chart(figure, use_container_width=True)


        ########### MONOTYPE HP ##########""

    if bool_monotype:
        with st.spinner('Calculating...'):
            # Define the decision variables
            P_HP_1 = opti.variable(N_primary, 1)
            P_HP_2 = opti.variable(N_secondary, 1)
            SERIES_HP = opti.variable(1, 1)
            PARALLEL_HP = opti.variable(1, 1)
            SOC_HP_1 = opti.variable(N_primary+1, 1)
            I_HP_1 = opti.variable(N_primary, 1)
            SOC_HP_2 = opti.variable(N_secondary+1, 1)
            I_HP_2 = opti.variable(N_secondary, 1)

            # Define the objective function
            objective = C_cell_HP * SERIES_HP * PARALLEL_HP   # Total cost of the battery system (eur)

            # Define the constraints
            opti.subject_to(P_HP_1 == P_primary)
            opti.subject_to(P_HP_2 == P_secondary)

            if bool_voltage:
                opti.subject_to(SERIES_HP == round(V_pack / V_cell_HP))

            if not bool_neg:
                opti.subject_to(P_HP_1 >= 0)
                opti.subject_to(P_HP_2 >= 0)

            opti.subject_to(SERIES_HP >= 0)
            opti.subject_to(PARALLEL_HP >= 0)
         
            # Define the SOC related parameters
            t_SOC_1 = df_load_primary['t'].tolist()
            t_SOC_1.append(t_SOC_1[-1] + (t_SOC_1[-1] - t_SOC_1[-2]))
            SOC_HP_1[0]=ca.DM(0.9)

            for i in range(0, N_primary):
                    E_HP = SERIES_HP * PARALLEL_HP * E_cell_HP
                    opti.subject_to(SOC_HP_1[i+1] == SOC_HP_1[i] - func.get_SOC(P_HP_1[i], E_HP,t_SOC_1[i+1] - t_SOC_1[i]))

            opti.subject_to(opti.bounded(0.1, SOC_HP_1, 0.9))

            t_SOC_2 = df_load_secondary['t'].tolist()
            t_SOC_2.append(t_SOC_2[-1] + (t_SOC_2[-1] - t_SOC_2[-2]))
            SOC_HP_2[0]=ca.DM(0.9)

            for i in range(0, N_secondary):
                    E_HP = SERIES_HP * PARALLEL_HP * E_cell_HP
                    opti.subject_to(SOC_HP_2[i+1] == SOC_HP_2[i] - func.get_SOC(P_HP_2[i], E_HP,t_SOC_2[i+1] - t_SOC_2[i]))

            opti.subject_to(opti.bounded(0.1, SOC_HP_2, 0.9))

            # Define the voltage and current related parameters
            SOC_TO_OCV_HP = ca.interpolant('LUT','bspline',[OCV_SOC_HP], OCV_HP)

            for i in range(0, N_primary):
                    if not bool_OCV:
                        V_HP = (SERIES_HP * SOC_TO_OCV_HP(SOC_HP_1[i]))
                    else:
                        V_HP = SERIES_HE * V_cell_HP
                    opti.subject_to(I_HP_1[i] == P_HP_1[i] / V_HP)

            opti.subject_to(I_HP_1 <= (PARALLEL_HP * I_cell_HP))

            for i in range(0, N_secondary):
                    if not bool_OCV:
                        V_HP = (SERIES_HP * SOC_TO_OCV_HP(SOC_HP_2[i]))
                    else:
                        V_HP = SERIES_HE * V_cell_HP
                        
                    opti.subject_to(I_HP_2[i] == P_HP_2[i] / V_HP)

            opti.subject_to(I_HP_2 <= (PARALLEL_HP * I_cell_HP))

            # Set initial values
            if bool_voltage:
                opti.set_initial(SERIES_HP, round(V_pack / V_cell_HP))  # Set initial value of E_HE
                
            else:
                opti.set_initial(SERIES_HP, 1)  # Set initial value of E_HE
            opti.set_initial(PARALLEL_HP, 25)

            # Define the solver and solve the problem
            opti.minimize(objective)
            options = {"ipopt": {"print_level": 5}}
            opti.solver('ipopt', options)
            sol = opti.solve()

            ###########################################

        layout[0].subheader(f"Optimal total cost: :green[**{'€ {:,.2f}'.format(sol.value(objective))} €**]")
        layout_left = layout[0].columns(2, gap="large")

        pack_HP = { 'parameter': ['series', 'parallel', 'total energy', 'nominal voltage', 'maximum current', 'rated current', 'total cost'],
                    'value': [round(sol.value(SERIES_HP), 2), round(sol.value(PARALLEL_HP), 2), f'{round(sol.value(SERIES_HP)*sol.value(PARALLEL_HP)*E_cell_HP, 2)} kWh', f'{round(sol.value(SERIES_HP) * V_cell_HP, 2)} V',
                    f'{round(max(max(sol.value(I_HP_1)), max(sol.value(I_HP_2))), 2)} A', f'{round(sol.value(PARALLEL_HP) * sol.value(I_cell_HP), 2)} A', f'{round(sol.value(SERIES_HP)*sol.value(PARALLEL_HP)*C_cell_HP, 2)} €']
        }

        df_pack_HP = pd.DataFrame(pack_HP)
        layout_left[1].table(func.display_pack(df_pack_HP))



        # Plot the power profiles
        placeholder_right_primary.empty()
        placeholder_right_secondary.empty()

        df_loads_primary = pd.DataFrame(dict(t = t_primary,
                                P = P_primary,
                                P_HE = sol.value(P_HP_1),
                                P_HP = sol.value(P_HP_1)))
        
        df_loads_secondary = pd.DataFrame(dict(t = t_secondary,
                                P = P_secondary,
                                P_HE = sol.value(P_HP_2),
                                P_HP = sol.value(P_HP_2)))

        figure = func.plot_powers(df_loads_primary)
        layout_right_primary[0].altair_chart(figure, use_container_width=True)
        figure = func.plot_powers(df_loads_secondary)
        layout_right_secondary[0].altair_chart(figure, use_container_width=True)

        # Plot the SOC
        df_SOC_1 = pd.DataFrame(dict(t = t_SOC_1,
                                SOC_HE = sol.value(SOC_HP_1),
                                SOC_HP = sol.value(SOC_HP_1),))
        
        df_SOC_2 = pd.DataFrame(dict(t = t_SOC_2,
                                SOC_HE = sol.value(SOC_HP_2),
                                SOC_HP = sol.value(SOC_HP_2),))

        figure = func.plot_SOC(df_SOC_1)
        layout_right_primary[1].altair_chart(figure, use_container_width=True)
        figure = func.plot_SOC(df_SOC_2)
        layout_right_secondary[1].altair_chart(figure, use_container_width=True)

        # Plot the current
        df_current_1 = pd.DataFrame(dict(t = t_primary,
                                I_HE = sol.value(I_HP_1),
                                I_HP = sol.value(I_HP_1)))
        
        df_current_2 = pd.DataFrame(dict(t = t_secondary,
                                I_HE = sol.value(I_HP_2),
                                I_HP = sol.value(I_HP_2)))

        figure = func.plot_currents(df_current_1)
        layout_right_primary[1].altair_chart(figure, use_container_width=True)
        figure = func.plot_currents(df_current_2)
        layout_right_secondary[1].altair_chart(figure, use_container_width=True)
        












































    if bool_discrete:
        #################
        sol_series_he = sol.value(SERIES_HE)
        sol_series_hp = sol.value(SERIES_HP)
        sol_parallel_he = sol.value(PARALLEL_HE)
        sol_parallel_hp = sol.value(PARALLEL_HP)

        with st.spinner('Calculating...'):
            # Define the decision variables
            P_HE_1 = opti.variable(N_primary, 1)
            P_HE_2 = opti.variable(N_secondary, 1)
            SERIES_HE = opti.variable(1, 1)
            PARALLEL_HE = opti.variable(1, 1)
            SOC_HE_1 = opti.variable(N_primary+1, 1)
            I_HE_1 = opti.variable(N_primary, 1)
            SOC_HE_2 = opti.variable(N_secondary+1, 1)
            I_HE_2 = opti.variable(N_secondary, 1)

            P_HP_1 = opti.variable(N_primary, 1)
            P_HP_2 = opti.variable(N_secondary, 1)
            SERIES_HP = opti.variable(1, 1)
            PARALLEL_HP = opti.variable(1, 1)
            SOC_HP_1 = opti.variable(N_primary+1, 1)
            I_HP_1 = opti.variable(N_primary, 1)
            SOC_HP_2 = opti.variable(N_secondary+1, 1)
            I_HP_2 = opti.variable(N_secondary, 1)

            # Define the objective function
            objective = C_cell_HE * SERIES_HE * PARALLEL_HE + C_cell_HP * SERIES_HP * PARALLEL_HP   # Total cost of the battery system (eur)

            # Define the constraints
            opti.subject_to(P_HE_1 + P_HP_1 == P_primary)
            opti.subject_to(P_HE_2 + P_HP_2 == P_secondary)

            # if bool_voltage:
            #     opti.subject_to(SERIES_HE == round(V_pack / V_cell_HE))
            #     opti.subject_to(SERIES_HP == round(V_pack / V_cell_HP))

            # opti.subject_to(SERIES_HE >= 0)
            # opti.subject_to(PARALLEL_HE >= 0)
            
            # opti.subject_to(PARALLEL_HP == sol_parallel_hp)
            # opti.subject_to(PARALLEL_HE == sol_parallel_he)
            #opti.subject_to(ca.remainder(SERIES_HE, 1) == 0)
            #opti.subject_to(ca.remainder(PARALLEL_HE, 1) == 0)
            opti.subject_to(opti.bounded(sol_series_he - 3, SERIES_HE, sol_series_he + 3))
            opti.subject_to(opti.bounded(sol_series_hp - 3, SERIES_HP, sol_series_hp + 3))
            opti.subject_to(PARALLEL_HE == round(sol_parallel_he))
            opti.subject_to(PARALLEL_HP == round(sol_parallel_hp))



            if not bool_neg:
                opti.subject_to(P_HP_1 >= 0)
                opti.subject_to(P_HP_2 >= 0)
                opti.subject_to(P_HE_1 >= 0)
                opti.subject_to(P_HE_2 >= 0)

            # opti.subject_to(SERIES_HP >= 0)
            # opti.subject_to(PARALLEL_HP >= 0)
            #opti.subject_to(ca.remainder(SERIES_HP, 1) == 0)
            #opti.subject_to(ca.remainder(PARALLEL_HP, 1) == 0)
            

            # Define the SOC related parameters
            t_SOC_1 = df_load_primary['t'].tolist()
            t_SOC_1.append(t_SOC_1[-1] + (t_SOC_1[-1] - t_SOC_1[-2]))
            SOC_HE_1[0]=ca.DM(0.9)
            SOC_HP_1[0]=ca.DM(0.9)

            for i in range(0, N_primary):
                    E_HE = SERIES_HE * PARALLEL_HE * E_cell_HE
                    E_HP = SERIES_HP * PARALLEL_HP * E_cell_HP
                    opti.subject_to(SOC_HE_1[i+1] == SOC_HE_1[i] - func.get_SOC(P_HE_1[i], E_HE,t_SOC_1[i+1] - t_SOC_1[i]))
                    opti.subject_to(SOC_HP_1[i+1] == SOC_HP_1[i] - func.get_SOC(P_HP_1[i], E_HP,t_SOC_1[i+1] - t_SOC_1[i]))

            opti.subject_to(opti.bounded(0.1, SOC_HE_1, 0.9))
            opti.subject_to(opti.bounded(0.1, SOC_HP_1, 0.9))

            t_SOC_2 = df_load_secondary['t'].tolist()
            t_SOC_2.append(t_SOC_2[-1] + (t_SOC_2[-1] - t_SOC_2[-2]))
            SOC_HE_2[0]=ca.DM(0.9)
            SOC_HP_2[0]=ca.DM(0.9)

            for i in range(0, N_secondary):
                    E_HE = SERIES_HE * PARALLEL_HE * E_cell_HE
                    E_HP = SERIES_HP * PARALLEL_HP * E_cell_HP
                    opti.subject_to(SOC_HE_2[i+1] == SOC_HE_2[i] - func.get_SOC(P_HE_2[i], E_HE,t_SOC_2[i+1] - t_SOC_2[i]))
                    opti.subject_to(SOC_HP_2[i+1] == SOC_HP_2[i] - func.get_SOC(P_HP_2[i], E_HP,t_SOC_2[i+1] - t_SOC_2[i]))

            opti.subject_to(opti.bounded(0.1, SOC_HE_2, 0.9))
            opti.subject_to(opti.bounded(0.1, SOC_HP_2, 0.9))

            # Define the voltage and current related parameters
            SOC_TO_OCV_HE = ca.interpolant('LUT','bspline',[OCV_SOC_HE], OCV_HE)
            SOC_TO_OCV_HP = ca.interpolant('LUT','bspline',[OCV_SOC_HP], OCV_HP)

            for i in range(0, N_primary):
                    if not bool_OCV:
                        V_HE = (SERIES_HE * SOC_TO_OCV_HE(SOC_HE_1[i]))
                        V_HP = (SERIES_HP * SOC_TO_OCV_HP(SOC_HP_1[i]))
                    else:
                        V_HE = SERIES_HE * V_cell_HE
                        V_HP = SERIES_HE * V_cell_HP
                    opti.subject_to(I_HE_1[i] == P_HE_1[i] / V_HE)
                    opti.subject_to(I_HP_1[i] == P_HP_1[i] / V_HP)

            opti.subject_to(I_HE_1 <= (PARALLEL_HE * I_cell_HE))
            opti.subject_to(I_HP_1 <= (PARALLEL_HP * I_cell_HP))

            for i in range(0, N_secondary):
                    if not bool_OCV:
                        V_HE = (SERIES_HE * SOC_TO_OCV_HE(SOC_HE_2[i]))
                        V_HP = (SERIES_HP * SOC_TO_OCV_HP(SOC_HP_2[i]))
                    else:
                        V_HE = SERIES_HE * V_cell_HE
                        V_HP = SERIES_HE * V_cell_HP
                        
                    opti.subject_to(I_HE_2[i] == P_HE_2[i] / V_HE)
                    opti.subject_to(I_HP_2[i] == P_HP_2[i] / V_HP)

            opti.subject_to(I_HE_2 <= (PARALLEL_HE * I_cell_HE))
            opti.subject_to(I_HP_2 <= (PARALLEL_HP * I_cell_HP))

            # Set initial values
            if bool_voltage:
                opti.set_initial(SERIES_HE, round(V_pack / V_cell_HE))  # Set initial value of E_HE
                opti.set_initial(SERIES_HP, round(V_pack / V_cell_HP))  # Set initial value of E_HE
                
            else:
                opti.set_initial(SERIES_HE, 1)  # Set initial value of E_HE
                opti.set_initial(SERIES_HP, 1)  # Set initial value of E_HE
            opti.set_initial(PARALLEL_HE, 16)
            opti.set_initial(PARALLEL_HP, 25)

            # Define the solver and solve the problem
            opti.minimize(objective)
            options = {"ipopt": {"print_level": 5}}
            opti.solver('ipopt', options)
            sol = opti.solve()

            ###########################################

        # layout[0].subheader(f"Optimal total cost: :green[**{'€ {:,.2f}'.format(sol.value(objective))} €**]")
        # layout_left = layout[0].columns(2, gap="large")
        
        # pack_HE = { 'parameter': ['series', 'parallel', 'total energy', 'nominal voltage', 'maximum current', 'rated current', 'total cost'],
        #             'value': [round(sol.value(SERIES_HE), 2), round(sol.value(PARALLEL_HE), 2), f'{round(sol.value(SERIES_HE)*sol.value(PARALLEL_HE)*E_cell_HE, 2)} kWh', f'{round(sol.value(SERIES_HE) * V_cell_HE, 2)} V',
        #             f'{round(max(max(sol.value(I_HE_1)), max(sol.value(I_HE_2))), 2)} A', f'{round(sol.value(PARALLEL_HE) * sol.value(I_cell_HE), 2)} A', f'{round(sol.value(SERIES_HE)*sol.value(PARALLEL_HE)*C_cell_HE, 2)} €']
        # }

        # pack_HP = { 'parameter': ['series', 'parallel', 'total energy', 'nominal voltage', 'maximum current', 'rated current', 'total cost'],
        #             'value': [round(sol.value(SERIES_HP), 2), round(sol.value(PARALLEL_HP), 2), f'{round(sol.value(SERIES_HP)*sol.value(PARALLEL_HP)*E_cell_HP, 2)} kWh', f'{round(sol.value(SERIES_HP) * V_cell_HP, 2)} V',
        #             f'{round(max(max(sol.value(I_HP_1)), max(sol.value(I_HP_2))), 2)} A', f'{round(sol.value(PARALLEL_HP) * sol.value(I_cell_HP), 2)} A', f'{round(sol.value(SERIES_HP)*sol.value(PARALLEL_HP)*C_cell_HP, 2)} €']
        # }

        # df_pack_HE = pd.DataFrame(pack_HE)
        # df_pack_HP = pd.DataFrame(pack_HP)
        # layout_left[0].table(func.display_pack(df_pack_HE))
        # layout_left[1].table(func.display_pack(df_pack_HP))
        


        # Plot the power profiles
        placeholder_right_primary.empty()
        placeholder_right_secondary.empty()

        df_loads_primary = pd.DataFrame(dict(t = t_primary,
                                P = P_primary,
                                P_HE = sol.value(P_HE_1),
                                P_HP = sol.value(P_HP_1)))
        
        df_loads_secondary = pd.DataFrame(dict(t = t_secondary,
                                P = P_secondary,
                                P_HE = sol.value(P_HE_2),
                                P_HP = sol.value(P_HP_2)))

        figure = func.plot_powers(df_loads_primary)
        layout_right_primary[0].altair_chart(figure, use_container_width=True)
        figure = func.plot_powers(df_loads_secondary)
        layout_right_secondary[0].altair_chart(figure, use_container_width=True)

        # Plot the SOC
        df_SOC_1 = pd.DataFrame(dict(t = t_SOC_1,
                                SOC_HE = sol.value(SOC_HE_1),
                                SOC_HP = sol.value(SOC_HP_1),))
        
        df_SOC_2 = pd.DataFrame(dict(t = t_SOC_2,
                                SOC_HE = sol.value(SOC_HE_2),
                                SOC_HP = sol.value(SOC_HP_2),))

        figure = func.plot_SOC(df_SOC_1)
        layout_right_primary[1].altair_chart(figure, use_container_width=True)
        figure = func.plot_SOC(df_SOC_2)
        layout_right_secondary[1].altair_chart(figure, use_container_width=True)

        # Plot the current
        df_current_1 = pd.DataFrame(dict(t = t_primary,
                                I_HE = sol.value(I_HE_1),
                                I_HP = sol.value(I_HP_1)))
        
        df_current_2 = pd.DataFrame(dict(t = t_secondary,
                                I_HE = sol.value(I_HE_2),
                                I_HP = sol.value(I_HP_2)))

        figure = func.plot_currents(df_current_1)
        layout_right_primary[1].altair_chart(figure, use_container_width=True)
        figure = func.plot_currents(df_current_2)
        layout_right_secondary[1].altair_chart(figure, use_container_width=True)

        # Plot the voltage
        SOC_TO_OCV_HE = interp1d(OCV_SOC_HE, OCV_HE, kind='linear', fill_value='extrapolate')
        SOC_TO_OCV_HP = interp1d(OCV_SOC_HP, OCV_HP, kind='linear', fill_value='extrapolate')
        
        df_voltage_1 = df_SOC_1[['t']].copy()

        if not bool_OCV:
            df_voltage_1['V_HE'] = df_SOC_1['SOC_HE'].apply(lambda soc: SOC_TO_OCV_HE(soc))
            df_voltage_1['V_HP'] = df_SOC_1['SOC_HP'].apply(lambda soc: SOC_TO_OCV_HP(soc))
        else:
            df_voltage_1['V_HE'] = V_cell_HE
            df_voltage_1['V_HP'] = V_cell_HP

        df_voltage_1['V_HE'] *= round(sol.value(SERIES_HE))
        df_voltage_1['V_HP'] *= round(sol.value(SERIES_HP))

        df_voltage_2 = df_SOC_2[['t']].copy()

        if not bool_OCV:
            df_voltage_2['V_HE'] = df_SOC_2['SOC_HE'].apply(lambda soc: SOC_TO_OCV_HE(soc))
            df_voltage_2['V_HP'] = df_SOC_2['SOC_HP'].apply(lambda soc: SOC_TO_OCV_HP(soc))
        else:
            df_voltage_2['V_HE'] = V_cell_HE
            df_voltage_2['V_HP'] = V_cell_HP

        df_voltage_2['V_HE'] *= round(sol.value(SERIES_HE))
        df_voltage_2['V_HP'] *= round(sol.value(SERIES_HP))

        figure = func.plot_voltages(df_voltage_1)
        layout_right_primary[0].altair_chart(figure, use_container_width=True)
        figure = func.plot_voltages(df_voltage_2)
        layout_right_secondary[0].altair_chart(figure, use_container_width=True)




        #################
        SERIES_HE = math.ceil(sol.value(SERIES_HE))
        SERIES_HP = math.ceil(sol.value(SERIES_HP))
        PARALLEL_HE = sol.value(PARALLEL_HE)
        PARALLEL_HP = sol.value(PARALLEL_HP)

        TOTALCOST = SERIES_HE * PARALLEL_HE * C_cell_HE + SERIES_HP * PARALLEL_HP * C_cell_HP

        layout[0].subheader(f"Optimal total cost: :green[**{'€ {:,.2f}'.format(TOTALCOST)} €**]")
        layout_left = layout[0].columns(2, gap="large")

        pack_HE = { 'parameter': ['series', 'parallel', 'total energy', 'nominal voltage', 'maximum current', 'rated current', 'total cost'],
                    'value': [int(SERIES_HE), int(PARALLEL_HE), f'{round(SERIES_HE*PARALLEL_HE*E_cell_HE, 2)} kWh', f'{round(SERIES_HE * V_cell_HE, 2)} V',
                    f'{round(max(max(sol.value(I_HE_1)), max(sol.value(I_HE_2))), 2)} A', f'{round(sol.value(PARALLEL_HE) * sol.value(I_cell_HE), 2)} A', f'{round(sol.value(SERIES_HE)*sol.value(PARALLEL_HE)*C_cell_HE, 2)} €']
        }

        pack_HP = { 'parameter': ['series', 'parallel', 'total energy', 'nominal voltage', 'maximum current', 'rated current', 'total cost'],
                    'value': [int(SERIES_HP), int(PARALLEL_HP), f'{round(SERIES_HP*PARALLEL_HP*E_cell_HP, 2)} kWh', f'{round(SERIES_HP * V_cell_HP, 2)} V',
                    f'{round(max(max(sol.value(I_HP_1)), max(sol.value(I_HP_2))), 2)} A', f'{round(sol.value(PARALLEL_HP) * sol.value(I_cell_HP), 2)} A', f'{round(sol.value(SERIES_HP)*sol.value(PARALLEL_HP)*C_cell_HP, 2)} €']
        }

        df_pack_HE = pd.DataFrame(pack_HE)
        df_pack_HP = pd.DataFrame(pack_HP)
        layout_left[0].table(func.display_pack(df_pack_HE))
        layout_left[1].table(func.display_pack(df_pack_HP))
    

