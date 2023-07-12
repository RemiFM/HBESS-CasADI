import casadi as ca     # Optimization toolbox
import streamlit as st  # Visual app framework
import pandas as pd     # DataFrame manipulation
import matplotlib.pyplot as plt # Plotting library
import numpy as np      # List manipulation
from scipy.integrate import cumtrapz
import func
import math

def battery_dynamics(P, E, dt):

    dSOC = (P*(dt))/(E *1000 * 3600)
    return dSOC

opti = ca.Opti() # CasADi helper classes

st.set_page_config(layout="wide")
st.header('Discrete HBESS Sizing using CasADi optimization:zap:')
layout = st.columns([3, 5], gap="large")
cols1 = layout[0].columns(2, gap="large")
cols2 = layout[1].columns(2, gap="large")

cols1[0].write('**High Energy Cell**')
cols1[1].write('**High Power Cell**')
cols2[0].write('**Primary Load Profile**')
cols2[1].write('**Secondary Load Profile**')

# CELL PARAMETERS
Q_cell_HE = cols1[0].number_input('Rated capacity (Ah)', value=94)      # Ah
V_cell_HE = cols1[0].number_input('Nominal voltage (V)', value=3.67)    # V
I_cell_HE = cols1[0].number_input('Maximum current (A)', value=150)     # A
C_cell_HE = cols1[0].number_input('Cost (€)', value=62)                 # €
E_cell_HE = (Q_cell_HE/1000) * V_cell_HE                                # kWh
bV = cols1[0].checkbox('Manually set Pack Voltage')
bEQ = cols1[0].checkbox('Force similar Pack Voltages', disabled=bV)
run = cols1[0].button('Run CasADi optimization')

Q_cell_HP = cols1[1].number_input('Rated capacity (Ah)', value=23)      # Ah
V_cell_HP = cols1[1].number_input('Nominal voltage (V)', value=2.3)     # V
I_cell_HP = cols1[1].number_input('Maximum current (A)', value=92)      # A
C_cell_HP = cols1[1].number_input('Cost (€)', value=38)                 # €
E_cell_HP = (Q_cell_HP/1000) * V_cell_HP                                # kWh
V_pack = cols1[1].number_input('Nominal Pack Voltage (V)', value=120, disabled= not bV)
V_pack = V_pack if bV else 0;
layout[0].divider()

print(V_pack)

# LOAD PROFILE PARAMETERS
df_load_primary = pd.read_csv('tug_boat_1.csv')
df_load_secondary = pd.read_csv('tug_boat_2.csv')

E_cum_primary   = cumtrapz(df_load_primary['power (W)'], df_load_primary['time (s)'], initial=0)        # Ws
E_cum_secondary = cumtrapz(df_load_secondary['power (W)'], df_load_secondary['time (s)'], initial=0)    # Ws

E_req_primary = E_cum_primary.max() / 3600 / 1000     # kWh
E_req_secondary = E_cum_secondary.max() / 3600 / 1000 # kWh

fig1 = func.get_figure(df_load_primary['time (s)']/3600, df_load_primary['power (W)']/1000, 'Time (h)', 'Power (kW)', f'Primary load profile = {round(E_req_primary, 2)} kWh')
fig2 = func.get_figure(df_load_secondary['time (s)']/3600, df_load_secondary['power (W)']/1000, 'Time (h)', 'Power (kW)', f'Secondary load profile = {round(E_req_secondary, 2)} kWh')
cols2[0].pyplot(fig1)
cols2[1].pyplot(fig2)

t_primary       = df_load_primary['time (s)'].values
P_primary       = df_load_primary['power (W)'].values
t_secondary     = df_load_secondary['time (s)'].values
P_secondary     = df_load_secondary['power (W)'].values
N_primary       = t_primary.shape[0]
N_secondary     = t_secondary.shape[0]

#################################################################################################################################
#################################################################################################################################
if run:
        with st.spinner('Calculating, please wait...'):
                t_SOC_primary   = np.hstack([t_primary, t_primary[-1] + np.diff(t_primary)[-1]])
                t_SOC_secondary = np.hstack([t_secondary, t_secondary[-1] + np.diff(t_secondary)[-1]])

                # DECISION VARIABLES
                series_HE = opti.variable(1, 1)
                series_HP = opti.variable(1, 1)

                parallel_HE = opti.variable(1, 1)
                parallel_HP = opti.variable(1, 1)

                SOC_HE_primary          = opti.variable(N_primary+1, 1)
                SOC_HP_primary          = opti.variable(N_primary+1, 1)
                SOC_HE_secondary        = opti.variable(N_secondary+1, 1)
                SOC_HP_secondary        = opti.variable(N_secondary+1, 1)

                P_HE_primary            = opti.variable(N_primary, 1)
                P_HP_primary            = opti.variable(N_primary, 1)
                P_HE_secondary          = opti.variable(N_secondary, 1)
                P_HP_secondary          = opti.variable(N_secondary, 1)


                SOC_HE_primary[0]       = ca.DM(1)
                SOC_HP_primary[0]       = ca.DM(1)
                SOC_HE_secondary[0]     = ca.DM(1)
                SOC_HP_secondary[0]     = ca.DM(1)

                # OBJECTIVE FUNCTION
                obj = ((C_cell_HE * series_HE * parallel_HE) + (C_cell_HP * series_HP * parallel_HP))

                # CONSTRAINTS
                opti.subject_to(P_HE_primary + P_HP_primary == P_primary)
                opti.subject_to(P_HE_secondary + P_HP_secondary == P_secondary)

                opti.subject_to(P_HE_primary >= 0)
                opti.subject_to(P_HP_primary >= 0)
                opti.subject_to(P_HE_secondary >= 0)
                opti.subject_to(P_HP_secondary >= 0)

                opti.subject_to(P_HE_primary <= parallel_HE * I_cell_HE * series_HE * V_cell_HE)
                opti.subject_to(P_HP_primary <= parallel_HP * I_cell_HP * series_HP * V_cell_HP)
                opti.subject_to(P_HE_secondary <= parallel_HE * I_cell_HE * series_HE * V_cell_HE)
                opti.subject_to(P_HP_secondary <= parallel_HP * I_cell_HP * series_HP * V_cell_HP)

                opti.subject_to(ca.remainder(series_HE, 1) < 0)
                opti.subject_to(ca.remainder(series_HP, 1) < 0)
                opti.subject_to(series_HE >= 0)
                opti.subject_to(series_HP >= 0)

                opti.subject_to(ca.remainder(parallel_HE, 1) == 0)
                opti.subject_to(ca.remainder(parallel_HP, 1) == 0)
                opti.subject_to(parallel_HE >= 0)
                opti.subject_to(parallel_HP >= 0)

                opti.subject_to(series_HE*parallel_HE*E_cell_HE + series_HP*parallel_HP*E_cell_HP >= max(E_req_primary, E_req_secondary)) # NOG AANPASSEN !! E_prim & DOD


                if bV:
                        opti.subject_to(series_HE == round(V_pack / V_cell_HE))
                        opti.subject_to(series_HP == round(V_pack / V_cell_HP))

                if bEQ and not bV:
                        opti.subject_to(ca.fabs((series_HE * V_cell_HE) - (series_HP * V_cell_HP)) <= 20)
        
                # opti.subject_to(SOC_HE_primary >= 0)
                # opti.subject_to(SOC_HE_primary <= 1)
                # opti.subject_to(SOC_HP_primary >= 0)
                # opti.subject_to(SOC_HP_primary <= 1)

                # opti.subject_to(SOC_HE_secondary >= 0)
                # opti.subject_to(SOC_HE_secondary <= 1)
                # opti.subject_to(SOC_HP_secondary >= 0)
                # opti.subject_to(SOC_HP_secondary <= 1)

                # for i in range(0, N_primary):
                #     opti.subject_to(SOC_HE_primary[i+1] == SOC_HE_primary[i] - battery_dynamics(P_HE_primary[i], series_HE * parallel_HE * E_cell_HE, (t_SOC_primary[i+1] - t_SOC_primary[i])))
                #     opti.subject_to(SOC_HP_primary[i+1] == SOC_HP_primary[i] - battery_dynamics(P_HP_primary[i], series_HP * parallel_HP * E_cell_HP, (t_SOC_primary[i+1] - t_SOC_primary[i])))

                # for i in range(0, N_secondary):
                #     opti.subject_to(SOC_HE_secondary[i+1] == SOC_HE_secondary[i] - func.battery_dynamics(P_HE_secondary[i]/1000, series_HE * parallel_HE * E_cell_HE, (t_SOC_secondary[i+1] - t_SOC_secondary[i])/3600))
                #     opti.subject_to(SOC_HP_secondary[i+1] == SOC_HP_secondary[i] - func.battery_dynamics(P_HP_secondary[i]/1000, series_HP * parallel_HP * E_cell_HP, (t_SOC_secondary[i+1] - t_SOC_secondary[i])/3600))

                if bEQ and not bV:
                        opti.set_initial(series_HE, 100)
                        opti.set_initial(series_HP, 100)
                        opti.set_initial(parallel_HE, 100)
                        opti.set_initial(parallel_HP, 100)





                # Add the constraints and objective to the optimization problem
                opti.minimize(obj)

                # Define the solver options and solve the problem
                options = {"ipopt": {"print_level": 5, "max_iter": 3000}}
                opti.solver('ipopt', options)
                sol = opti.solve()


                # Print the solution
                #st.write(f"Optimal objective: {sol.value(obj)}")
                #st.write(f"Optimal config of HE battery: **{sol.value(series_HE)}** series, **{sol.value(parallel_HE)}** parallel")
                #st.write(f"Optimal config of HP battery: **{sol.value(series_HP)}** series, **{sol.value(parallel_HP)}** parallel")

                parallel_HE     = math.ceil(sol.value(parallel_HE))
                parallel_HP     = math.ceil(sol.value(parallel_HP))
                series_HE       = math.ceil(sol.value(series_HE)) 
                series_HP       = math.ceil(sol.value(series_HP))

                if series_HE == 0:
                        parallel_HE = 0

                if series_HP == 0:
                        parallel_HP = 0

                if parallel_HE == 0:
                        series_HE = 0

                if parallel_HP == 0:
                        series_HP = 0

                layout[0].write(f"HE Pack: **{series_HE}** series, **{parallel_HE}** parallel, pack voltage **{round(series_HE * V_cell_HE, 1)} V**.")
                layout[0].write(f"HP Pack: **{series_HP}** series, **{parallel_HP}** parallel, pack voltage **{round(series_HP * V_cell_HP, 1)} V**.")
                layout[0].write(f":arrow_right: Total cost: :blue[**€ {series_HE*parallel_HE*C_cell_HE + series_HP*parallel_HP*C_cell_HP}**]")

                #fig = func.get_bars(series_HE, parallel_HE, series_HP, parallel_HP)
                #cols2[0].pyplot(fig)



                # Shared power plots
                df_power_primary = pd.DataFrame(dict(t = t_primary, P = P_primary, P_HE = sol.value(P_HE_primary), P_HP = sol.value(P_HP_primary)))
                df_power_secondary = pd.DataFrame(dict(t = t_secondary, P = P_secondary, P_HE = sol.value(P_HE_secondary), P_HP = sol.value(P_HP_secondary)))

                fig = func.plot_power(df_power_primary)
                cols2[0].pyplot(fig)

                fig = func.plot_power(df_power_secondary)
                cols2[1].pyplot(fig)









