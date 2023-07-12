import matplotlib.pyplot as plt # Plotting library

def get_figure(x, y, xlabel, ylabel, title):
    fig, ax = plt.subplots(figsize=(10, 5))
    #ax.plot(df_load_primary['time (s)'], df_load_primary['power (W)'])
    ax.plot(x, y)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True)

    ax.set_xlim([x.min(), x.max()])
    ax.set_ylim([y.min(), y.max()])
    ax.autoscale(False)

    return fig


def get_bars(a, b, c, d):
    # Create a list of labels for the bars
    labels = ['HE String Length', 'HE Strings', 'HP String Length', 'HP Strings']

    # Create a list of values for the bars
    values = [a, b, c, d]

    # Create a figure and axis object
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot the bars
    bars = ax.bar(labels, values, color=['blue', 'blue', 'red', 'red'])

    # Set labels and title
    ax.set_xlabel('Category')
    ax.set_ylabel('Value')
    ax.set_title('Bar Graph')
    ax.grid(True)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height, str(height),
                ha='center', va='bottom')

    return fig

def plot_power(df_power_primary):
    # Extract the data from the DataFrame
    t = df_power_primary['t']/3600
    P = df_power_primary['P']/1000
    P_HE = df_power_primary['P_HE']/1000
    P_HP = df_power_primary['P_HP']/1000

    # Create a figure and axis object
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot the data
    ax.plot(t, P, label='Power Demand')
    ax.plot(t, P_HE, label='High Energy')
    ax.plot(t, P_HP, label='High Power')

    # Set labels and title
    ax.set_xlabel('Time (h)')
    ax.set_ylabel('Power (kW)')
    ax.set_title('Power vs. Time')
    ax.grid(True)

    ax.set_xlim([t.min(), t.max()])
    ax.set_ylim([P.min(), P.max()])
    ax.autoscale(False)

    # Add legend
    ax.legend()

    return fig


