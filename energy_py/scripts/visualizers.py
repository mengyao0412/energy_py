import logging
import os

import matplotlib
#  hack to get matplotlib to play nice with AWS
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from energy_py.scripts.utils import  ensure_dir


plt.style.use('seaborn')
matplotlib.rcParams['agg.path.chunksize'] = 10000
logger = logging.getLogger(__name__)

"""
Functions related to generating outputs from agent and environment info
"""

def single_series_fig(series,
                      fig_path=None,
                      xlabel=None, ylabel=None,
                      xlim='all', ylim=None):
    """
    args
        series (pd.Series)
        fig_path (str)
        xlabel (str) 
        ylabel (str)
        xlim (str) last_week, last_month or all
        ylim (list) 

    returns
        fig (object) a plot of a single time series
    """
    #  create the matplotlib axes and figure objects
    fig, ax = plt.subplots(1, 1, figsize=(15, 10))
    #  plot as a line
    series.astype(float).plot(kind='line', ax=ax)

    if xlabel:
        plt.xlabel(xlabel)

    if ylabel:
        plt.ylabel(ylabel)

    plt.legend()

    if xlim == 'last_week':
        start = series.index[-7 * 24 * 12]
        end = series.index[-1]

    if xlim == 'last_month':
        start = series.index[-30 * 24 * 12]
        end = series.index[-1]

    if xlim == 'all':
        start = series.index[0]
        end = series.index[-1]

    ax.set_xlim([start, end])

    if ylim:
        ax.set_ylim(ylim)

    #  saving to disk
    if fig_path:
        ensure_dir(fig_path)
        fig.savefig(fig_path)

    return fig

def make_panel_fig(df, 
                   panels, 
                   fig_path=None,
                   ylabels=None, 
                   xlabel=None,
                   ylims=None,
                   kinds=None, 
                   errors=None):
    """
    Creates a panel of time series plots.  
    
    args
        df (pd.DataFrame)
        panels (list) names of the columns to include in each panel
                      is always a list of lists [['col1', 'col2']]
        fig_path (str)
        ylabels (list) one per panel
        xlabel (str) shared between all panels
        ylims (str) optional limits on the y axis
        kinds (list) option to change type of plot
        errors (list) column names to use as error bars

    returns
        fig (object) plot of the panels
    """
    num_panels = len(panels)

    fig, axes = plt.subplots(nrows=num_panels,
                             ncols=1,
                             figsize=(15, 10),
                             sharex=True)

    #  catch the case with a single panel
    axes = np.array(axes).flatten()

    for i, (ax, panel) in enumerate(zip(axes, panels)):

        for col in panel:
            data = df.loc[:, col]

            if kinds and kinds[i]:
                kind = kinds[i]
            else:
                kind = 'line'

            data.plot(kind=kind, ax=ax, label=col)

            if errors and errors[i]:
                x = df.index.values
                y = data.values
                error = df.loc[:, errors[i]].values.flatten()
                ax.fill_between(x, y - error, y + error,
                                alpha=0.5)

            if ylims and ylims[i]:
                ax.set_ylim(ylims[i])

            if xlabel:
                ax.set_xlabel(xlabel)

            if ylabels and ylabels[i]: 
                ax.set_ylabel(ylabels[i])

            ax.legend()

    if fig_path:
        ensure_dir(fig_path)
        fig.savefig(fig_path)

    return fig


class EternityVisualizer(object):
    """
    A class to join together data generated by the agent and environment

    args
        agent (object) energy_py Agent 
        env (object) energy_py Environment 
        results_path (str)
    """
    def __init__(self,
                 agent=None,
                 env=None,
                 results_path='./results/'):

        self.agent = agent
        self.env = env
        self.results_path = os.path.join(results_path)

        #  create two dictionaries to hold data and figures
        self.data_dict, self.figs_dict = {}, {}

    def output_results(self, save_data=False):
        """
        The master function in this class.

        Use conditionals for agent & env to give user the flexibility to
        process an agent or environment on it's own

        args
            save_data (bool) option to save csvs to disk
        """
        if self.agent:
            self.agent_outputs = self.load_agent_data()
            self.info_to_plots(self.agent_outputs['info'])
            self.make_reward_panel()

        if self.env:
            self.env_outputs = self.load_env_data()
            self.info_to_plots(self.env_outputs['info'])
            self.make_env_fig()

        if save_data:
            self.save_data_to_disk()

        return self.agent_outputs, self.env_outputs

    def load_agent_data(self):
        """
        Pull data from the agent. 
        """
        return self.agent.output_results()

    def load_env_data(self):
        """
        Pull data from the environment.
        """
        logger.debug('Pulling data out of the environment')
        env_outputs = self.env.output_results()

        #  use the observation datetime index to index the env info df 
        index = env_outputs['observation_ts'].index
        len =  env_outputs['df_env_info'].shape[0]
        env_outputs['df_env_info'].index = index[:len]
        return env_outputs

    def info_to_plots(self, info_dict):
        """
        Takes an info_dict (supplied either by the agent or environment) and
        extracts the data.  

        The entries in the info dict are either lists of numpy arrays or 
        lists of floats/ints.  

        args
            info_dict (dict) either env.info or agent.memory.info
        """
        for var, data in info_dict.items():

            #  don't use next_state or next_observation
            if var != 'next_state' and var != 'next_observation':

                if isinstance(data[0], np.ndarray):
                    #  list of numpy arrays
                    logger.debug('making df for {} from info dict'.format(var))
                    names = ['{}_{}'.format(var,i) for i in range(len(data))]
                    data = np.array(data).reshape(-1, len(data))
                    data = pd.DataFrame(data)
                    data.columns = names
                    self.data_dict[var] = data 
                else:
                    #  list of data 
                    logger.debug('making series for {} from info dict'.format(var))
                    data = pd.Series(data, name=var)
                    fig_name = os.path.join('figs', var)
                    fig = single_series_fig(data, fig_name, self.results_path)

                    #  save the data and Uigure in the data & fig dictionaries
                    self.data_dict[var] = data 
                    self.figs_dict[var] = fig

    def make_reward_panel(self):
        #  reward panel is shared between all environments
        #  it uses only reinforcement learning data (reward)

        fig_path = os.path.join(self.results_path, 'reward_panel.png')
        reward_panel = {'name': 'reward_panel',
                        'panels': [['reward', 'cum max reward'],
                                   ['rolling mean']],
                        'errors': [[], ['rolling std']],
                        'xlabel': 'Episode',
                        'ylabels': ['Total undiscounted reward per episode',
                                    'Rolling last 10% of episodes'],
                        'fig_path': fig_path}

        #  add the dataframe with the data for this plot
        reward_panel['df'] = self.agent_outputs['df_ep']

        #  create the figure and save in the figs dict
        rew_fig = make_panel_fig(**reward_panel)
        self.figs_dict['reward_panel'] = rew_fig

    def make_env_fig(self):
        #  grab the dictionary that specifies the env panel fig
        env_panel_fig = self.env_outputs['env_panel_fig']

        #  add in the env info dataframe, results path and name 
        env_panel_fig['df'] = self.env_outputs['df_env_info']
         
        fig_path = os.path.join(self.results_path, 
                                env_panel_fig['name']+'.png')

        env_panel_fig['fig_path'] = fig_path

        #  create the figure and save in the figs dict
        env_fig = make_panel_fig(**env_panel_fig)
        self.figs_dict['env_panel_fig'] = env_fig    

    def save_data_to_disk(self):
        disk_data = {'df_stp.csv': self.agent_outputs['df_stp'],
                     'df_ep.csv': self.agent_outputs['df_ep'],
                     'env_info.csv': self.env_outputs['df_env_info']}

        for path, data in disk_data.items():
            path = os.path.join(self.results_path, 'csvs', path)
            ensure_dir(path)
            data.to_csv(path)
