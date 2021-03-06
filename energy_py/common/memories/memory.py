from collections import namedtuple

import numpy as np


#  use a namedtuple to store a single sample of experience
Experience = namedtuple('Experience', ['observation',
                                       'action',
                                       'reward',
                                       'next_observation',
                                       'done'])


def calculate_returns(rewards, discount):
    """
    Calculates the Monte Carlo discounted return.

    args
        rewards (np.array) rewards we want to calculate the return for

    returns
        returns (np.array) the return for each state
    """
    R = 0  # return after state s
    returns = []  # return after next state s'

    #  reverse the list so that we can do a backup
    for r in rewards[::-1]:
        R = r + discount * R  # the Bellman equation
        returns.insert(0, R)

    return np.array(returns).reshape(-1, 1)


class BaseMemory(object):
    """
    Base class for agent memories

    args
        size (int)
        obs_shape (tuple)
        action_shape (tuple)

    The shapes dictionary is used to reshape experience dimensions
    """
    def __init__(self,
                 size,
                 obs_shape,
                 action_shape):

        self.size = int(size)
        self.shapes = {
            'observation': obs_shape,
            'action': action_shape,
            'reward': (1,),
            'next_observation': obs_shape,
            'done': (1,),
            'importance_weight': (1,),
            'indexes': (1,) #  does this do anything ? TODO
        }

    def make_batch_dict(self, batch):
        """
        Takes a list of experiences and converts into a dictionary

        args
            batch (list)

        returns
            batch_dict (dict)

        Batch converted into batch_dict:
            {'observation': np.array(batch_size, *obs_shape,
             'action': np.array(batch_size, *act_shape),
             'reward': np.array(batch_size),
             'next_observation': np.array(batch_size, *obs_shape),
             'done': np.array(batch_size)}
        """
        batch_dict = {}

        for field in Experience._fields:
            arr = np.array([getattr(e, field) for e in batch])
            batch_dict[field] = arr.reshape(len(batch), *self.shapes[field])

        return batch_dict
